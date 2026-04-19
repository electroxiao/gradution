import json

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from backend.core.config import settings
from backend.models.assignment import (
    Assignment,
    AssignmentAssignee,
    AssignmentQuestion,
    AssignmentSubmission,
    AssignmentTestCase,
)
from backend.models.user import User
from backend.schemas.assignment import (
    AssignmentAiHelpRequest,
    AssignmentAiHelpResponse,
    AssignmentCreateRequest,
    AssignmentDetailResponse,
    AssignmentGeneratedQuestionResponse,
    AssignmentGenerateQuestionRequest,
    AssignmentQuestionInput,
    AssignmentQuestionsUpdateRequest,
    AssignmentRunResultResponse,
    AssignmentStudentRef,
    AssignmentSubmissionResponse,
    AssignmentSummaryResponse,
    AssignmentTestCaseInput,
    AssignmentUpdateRequest,
)
from backend.services.chat_service import get_openai_client
from backend.services.sandbox_service import run_java_submission


VALID_ASSIGNMENT_STATUSES = {"draft", "published", "closed"}


def list_teacher_assignments(db: Session, teacher: User) -> list[AssignmentSummaryResponse]:
    assignments = (
        db.query(Assignment)
        .options(selectinload(Assignment.questions), selectinload(Assignment.assignees))
        .filter(Assignment.teacher_id == teacher.id)
        .order_by(Assignment.updated_at.desc(), Assignment.id.desc())
        .all()
    )
    return [_assignment_summary(db, item) for item in assignments]


def create_assignment(db: Session, teacher: User, payload: AssignmentCreateRequest) -> AssignmentDetailResponse:
    _validate_status(payload.status)
    assignment = Assignment(
        title=payload.title.strip(),
        description=payload.description,
        teacher_id=teacher.id,
        status=payload.status,
        due_at=payload.due_at,
    )
    db.add(assignment)
    db.flush()
    _replace_assignees(db, assignment, payload.student_ids)
    _sync_questions(db, assignment, payload.questions)
    db.commit()
    return get_teacher_assignment_detail(db, teacher, assignment.id)


def get_teacher_assignment_detail(db: Session, teacher: User, assignment_id: int) -> AssignmentDetailResponse:
    assignment = _get_teacher_assignment(db, teacher, assignment_id)
    return _assignment_detail(db, assignment, teacher_view=True, student=None)


def update_assignment(
    db: Session,
    teacher: User,
    assignment_id: int,
    payload: AssignmentUpdateRequest,
) -> AssignmentDetailResponse:
    assignment = _get_teacher_assignment(db, teacher, assignment_id)
    if payload.title is not None:
        assignment.title = payload.title.strip()
    if payload.description is not None:
        assignment.description = payload.description
    if payload.status is not None:
        _validate_status(payload.status)
        assignment.status = payload.status
    if "due_at" in payload.model_fields_set:
        assignment.due_at = payload.due_at
    if payload.student_ids is not None:
        _replace_assignees(db, assignment, payload.student_ids)
    db.commit()
    return get_teacher_assignment_detail(db, teacher, assignment_id)


def update_assignment_questions(
    db: Session,
    teacher: User,
    assignment_id: int,
    payload: AssignmentQuestionsUpdateRequest,
) -> AssignmentDetailResponse:
    assignment = _get_teacher_assignment(db, teacher, assignment_id)
    _sync_questions(db, assignment, payload.questions)
    db.commit()
    return get_teacher_assignment_detail(db, teacher, assignment_id)


def generate_assignment_question(payload: AssignmentGenerateQuestionRequest) -> AssignmentGeneratedQuestionResponse:
    prompt = f"""
你是一名 Java 编程作业设计助手。请根据教师要求生成一道 Java 编程题草稿和 2 到 4 个测试用例。

知识点：{payload.knowledge_point or "未指定"}
教师要求：{payload.requirement}

要求：
1. 题目面向 Java 初学者，主类固定为 Main，从标准输入读取，从标准输出打印。
2. 测试用例包含 input_data、expected_output、is_sample、sort_order。
3. 至少 1 个示例测试，至少 1 个隐藏测试。
4. 只返回 JSON，不要解释。

JSON 格式：
{{
  "title": "题目标题",
  "prompt": "题目描述，包含输入输出要求",
  "language": "java",
  "test_cases": [
    {{"input_data": "输入", "expected_output": "输出", "is_sample": true, "sort_order": 0}}
  ]
}}
"""
    client = get_openai_client()
    try:
        response = client.chat.completions.create(
            model=settings.llm_model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        content = response.choices[0].message.content or ""
        data = _parse_json_object(content)
        test_cases = [
            AssignmentTestCaseInput(
                input_data=item.get("input_data", ""),
                expected_output=item.get("expected_output", ""),
                is_sample=bool(item.get("is_sample", False)),
                sort_order=int(item.get("sort_order", index)),
            )
            for index, item in enumerate(data.get("test_cases", []))
        ]
        if not test_cases:
            test_cases = [AssignmentTestCaseInput(input_data="", expected_output="", is_sample=True, sort_order=0)]
        return AssignmentGeneratedQuestionResponse(
            title=data.get("title") or "Java 编程题",
            prompt=data.get("prompt") or payload.requirement,
            language="java",
            test_cases=test_cases,
        )
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"生成题目失败：{error}",
        ) from error


def list_student_assignments(db: Session, student: User) -> list[AssignmentSummaryResponse]:
    assignments = (
        db.query(Assignment)
        .join(AssignmentAssignee, AssignmentAssignee.assignment_id == Assignment.id)
        .options(selectinload(Assignment.questions), selectinload(Assignment.assignees))
        .filter(AssignmentAssignee.student_id == student.id)
        .filter(Assignment.status != "draft")
        .order_by(Assignment.updated_at.desc(), Assignment.id.desc())
        .all()
    )
    return [_assignment_summary(db, item, student=student) for item in assignments]


def get_student_assignment_detail(db: Session, student: User, assignment_id: int) -> AssignmentDetailResponse:
    assignment = _get_student_assignment(db, student, assignment_id)
    return _assignment_detail(db, assignment, teacher_view=False, student=student)


def submit_assignment_question(
    db: Session,
    student: User,
    assignment_id: int,
    question_id: int,
    code: str,
) -> AssignmentRunResultResponse:
    assignment = _get_student_assignment(db, student, assignment_id)
    question = _get_assignment_question(assignment, question_id)
    if question.language != "java":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前仅支持 Java 作业。")
    if not question.test_cases:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该题目尚未配置测试用例。")

    status_value, results = run_java_submission(code, list(question.test_cases))
    submission = AssignmentSubmission(
        assignment_id=assignment.id,
        question_id=question.id,
        student_id=student.id,
        code=code,
        status=status_value,
        results_json=results,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return AssignmentRunResultResponse(
        submission=AssignmentSubmissionResponse.model_validate(submission),
        status=status_value,
        results=results,
    )


def list_student_submissions(db: Session, student: User, assignment_id: int) -> list[AssignmentSubmissionResponse]:
    _get_student_assignment(db, student, assignment_id)
    submissions = (
        db.query(AssignmentSubmission)
        .filter(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.student_id == student.id,
        )
        .order_by(AssignmentSubmission.submitted_at.desc(), AssignmentSubmission.id.desc())
        .all()
    )
    return [AssignmentSubmissionResponse.model_validate(item) for item in submissions]


def assignment_ai_help(
    db: Session,
    student: User,
    assignment_id: int,
    question_id: int,
    payload: AssignmentAiHelpRequest,
) -> AssignmentAiHelpResponse:
    assignment = _get_student_assignment(db, student, assignment_id)
    question = _get_assignment_question(assignment, question_id)
    prompt = f"""
你是一名 Java 编程作业助教。学生可以随时提问，请根据题目、学生代码和最近运行结果给出循序渐进的帮助。

要求：
1. 优先指出思路、错误位置和调试方法。
2. 不要直接给完整可复制的标准答案。
3. 如果代码有明显语法或运行错误，先解释原因，再给最小修改建议。
4. 回答使用中文，简洁具体。

作业：{assignment.title}
题目：{question.title or "编程题"}
题目描述：
{question.prompt}

学生代码：
```java
{payload.code or "学生暂未提供代码"}
```

最近运行结果：
{json.dumps(payload.last_result or {}, ensure_ascii=False)}

学生问题：
{payload.message}
"""
    client = get_openai_client()
    try:
        response = client.chat.completions.create(
            model=settings.llm_model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        return AssignmentAiHelpResponse(answer=(response.choices[0].message.content or "").strip())
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AI 帮助失败：{error}") from error


def _validate_status(status_value: str) -> None:
    if status_value not in VALID_ASSIGNMENT_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="作业状态必须是 draft、published 或 closed。")


def _get_teacher_assignment(db: Session, teacher: User, assignment_id: int) -> Assignment:
    assignment = (
        db.query(Assignment)
        .options(
            selectinload(Assignment.questions).selectinload(AssignmentQuestion.test_cases),
            selectinload(Assignment.assignees).selectinload(AssignmentAssignee.student),
        )
        .filter(Assignment.id == assignment_id, Assignment.teacher_id == teacher.id)
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="作业不存在。")
    return assignment


def _get_student_assignment(db: Session, student: User, assignment_id: int) -> Assignment:
    assignment = (
        db.query(Assignment)
        .join(AssignmentAssignee, AssignmentAssignee.assignment_id == Assignment.id)
        .options(
            selectinload(Assignment.questions).selectinload(AssignmentQuestion.test_cases),
            selectinload(Assignment.assignees).selectinload(AssignmentAssignee.student),
        )
        .filter(
            Assignment.id == assignment_id,
            AssignmentAssignee.student_id == student.id,
            Assignment.status != "draft",
        )
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="作业不存在或未分配给你。")
    return assignment


def _get_assignment_question(assignment: Assignment, question_id: int) -> AssignmentQuestion:
    question = next((item for item in assignment.questions if item.id == question_id), None)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在。")
    return question


def _replace_assignees(db: Session, assignment: Assignment, student_ids: list[int]) -> None:
    student_ids = sorted(set(student_ids))
    if student_ids:
        count = (
            db.query(func.count(User.id))
            .filter(User.id.in_(student_ids), User.role == "student")
            .scalar()
        )
        if count != len(student_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="学生列表包含无效用户。")

    db.query(AssignmentAssignee).filter(AssignmentAssignee.assignment_id == assignment.id).delete(
        synchronize_session=False
    )
    db.flush()
    for student_id in student_ids:
        db.add(AssignmentAssignee(assignment_id=assignment.id, student_id=student_id))


def _sync_questions(db: Session, assignment: Assignment, payload_questions: list[AssignmentQuestionInput]) -> None:
    existing = {question.id: question for question in assignment.questions}
    keep_ids: set[int] = set()

    for index, item in enumerate(payload_questions):
        if item.language != "java":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前仅支持 Java 题目。")
        sort_order = item.sort_order if item.sort_order is not None else index
        if item.id and item.id in existing:
            question = existing[item.id]
            keep_ids.add(question.id)
            question.title = item.title
            question.prompt = item.prompt
            question.language = "java"
            question.sort_order = sort_order
        else:
            question = AssignmentQuestion(
                assignment=assignment,
                title=item.title,
                prompt=item.prompt,
                language="java",
                sort_order=sort_order,
            )
            db.add(question)
            db.flush()
            keep_ids.add(question.id)
        _sync_test_cases(db, question, item.test_cases)

    for question in list(assignment.questions):
        if question.id not in keep_ids:
            db.delete(question)


def _sync_test_cases(db: Session, question: AssignmentQuestion, payload_cases: list[AssignmentTestCaseInput]) -> None:
    existing = {test_case.id: test_case for test_case in question.test_cases}
    keep_ids: set[int] = set()
    for index, item in enumerate(payload_cases):
        sort_order = item.sort_order if item.sort_order is not None else index
        if item.id and item.id in existing:
            test_case = existing[item.id]
            keep_ids.add(test_case.id)
            test_case.input_data = item.input_data
            test_case.expected_output = item.expected_output
            test_case.is_sample = item.is_sample
            test_case.sort_order = sort_order
        else:
            test_case = AssignmentTestCase(
                question=question,
                input_data=item.input_data,
                expected_output=item.expected_output,
                is_sample=item.is_sample,
                sort_order=sort_order,
            )
            db.add(test_case)
            db.flush()
            keep_ids.add(test_case.id)

    for test_case in list(question.test_cases):
        if test_case.id not in keep_ids:
            db.delete(test_case)


def _assignment_summary(db: Session, assignment: Assignment, student: User | None = None) -> AssignmentSummaryResponse:
    query = db.query(AssignmentSubmission).filter(AssignmentSubmission.assignment_id == assignment.id)
    if student:
        query = query.filter(AssignmentSubmission.student_id == student.id)
    submitted_count = query.with_entities(func.count(AssignmentSubmission.id)).scalar() or 0
    accepted_count = query.filter(AssignmentSubmission.status == "accepted").with_entities(func.count(AssignmentSubmission.id)).scalar() or 0
    return AssignmentSummaryResponse(
        id=assignment.id,
        title=assignment.title,
        description=assignment.description,
        status=assignment.status,
        due_at=assignment.due_at,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
        question_count=len(assignment.questions),
        assignee_count=len(assignment.assignees),
        submitted_count=submitted_count,
        accepted_count=accepted_count,
    )


def _assignment_detail(
    db: Session,
    assignment: Assignment,
    teacher_view: bool,
    student: User | None,
) -> AssignmentDetailResponse:
    questions = []
    for question in sorted(assignment.questions, key=lambda item: (item.sort_order, item.id)):
        test_cases = []
        for test_case in sorted(question.test_cases, key=lambda item: (item.sort_order, item.id)):
            expected_output = test_case.expected_output if teacher_view or test_case.is_sample else None
            test_cases.append(
                {
                    "id": test_case.id,
                    "input_data": test_case.input_data if teacher_view or test_case.is_sample else "",
                    "expected_output": expected_output,
                    "is_sample": test_case.is_sample,
                    "sort_order": test_case.sort_order,
                }
            )
        questions.append(
            {
                "id": question.id,
                "title": question.title,
                "prompt": question.prompt,
                "language": question.language,
                "sort_order": question.sort_order,
                "test_cases": test_cases,
            }
        )

    submission_query = db.query(AssignmentSubmission).filter(AssignmentSubmission.assignment_id == assignment.id)
    if student:
        submission_query = submission_query.filter(AssignmentSubmission.student_id == student.id)
    submissions = submission_query.order_by(AssignmentSubmission.submitted_at.desc(), AssignmentSubmission.id.desc()).all()

    return AssignmentDetailResponse(
        id=assignment.id,
        title=assignment.title,
        description=assignment.description,
        status=assignment.status,
        due_at=assignment.due_at,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
        questions=questions,
        assigned_students=[
            AssignmentStudentRef.model_validate(item.student)
            for item in assignment.assignees
            if teacher_view and item.student
        ],
        submissions=[AssignmentSubmissionResponse.model_validate(item) for item in submissions],
    )


def _parse_json_object(content: str) -> dict:
    start = content.find("{")
    end = content.rfind("}") + 1
    if start == -1 or end <= start:
        raise ValueError("大模型未返回 JSON。")
    return json.loads(content[start:end])
