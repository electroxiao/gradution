import json
from datetime import datetime

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
    AssignmentProgressCellResponse,
    AssignmentProgressQuestionResponse,
    AssignmentProgressResponse,
    AssignmentProgressStudentResponse,
    AssignmentQuestionInput,
    AssignmentQuestionsUpdateRequest,
    AssignmentRunResultResponse,
    AssignmentStudentRef,
    AssignmentSubmissionDetailResponse,
    AssignmentSubmissionResponse,
    AssignmentSummaryResponse,
    AssignmentTestCaseInput,
    AssignmentUpdateRequest,
)
from backend.services import rag_engine
from backend.services.chat_service import get_neo4j_driver, get_openai_client
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
    started_at: datetime | None = None,
) -> AssignmentRunResultResponse:
    assignment = _get_student_assignment(db, student, assignment_id)
    question = _get_assignment_question(assignment, question_id)
    if question.language != "java":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前仅支持 Java 作业。")
    if not question.test_cases:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该题目尚未配置测试用例。")

    status_value, results = run_java_submission(code, list(question.test_cases))
    started_at = _strip_timezone(started_at)
    submitted_at = datetime.now()
    submission = AssignmentSubmission(
        assignment_id=assignment.id,
        question_id=question.id,
        student_id=student.id,
        code=code,
        status=status_value,
        results_json=results,
        started_at=started_at,
        duration_seconds=_duration_seconds(started_at, submitted_at),
        submitted_at=submitted_at,
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


def get_teacher_assignment_progress(db: Session, teacher: User, assignment_id: int) -> AssignmentProgressResponse:
    assignment = _get_teacher_assignment(db, teacher, assignment_id)
    questions = sorted(assignment.questions, key=lambda item: (item.sort_order, item.id))
    assignees = sorted(
        [item for item in assignment.assignees if item.student],
        key=lambda item: (item.student.username, item.student_id),
    )

    submissions = (
        db.query(AssignmentSubmission)
        .filter(AssignmentSubmission.assignment_id == assignment.id)
        .order_by(AssignmentSubmission.submitted_at.asc(), AssignmentSubmission.id.asc())
        .all()
    )

    grouped: dict[tuple[int, int], dict] = {}
    for submission in submissions:
        key = (submission.student_id, submission.question_id)
        item = grouped.setdefault(key, {"count": 0, "latest": None})
        item["count"] += 1
        latest = item["latest"]
        if latest is None or (submission.submitted_at, submission.id) >= (latest.submitted_at, latest.id):
            item["latest"] = submission

    cells = []
    for assignee in assignees:
        for question in questions:
            group = grouped.get((assignee.student_id, question.id), {"count": 0, "latest": None})
            latest = group["latest"]
            if latest:
                cells.append(
                    AssignmentProgressCellResponse(
                        student_id=assignee.student_id,
                        question_id=question.id,
                        status=latest.status,
                        submission_count=group["count"],
                        latest_submission_id=latest.id,
                        submitted_at=latest.submitted_at,
                        run_time_ms=_sum_run_time_ms(latest.results_json),
                        duration_seconds=latest.duration_seconds,
                    )
                )
            else:
                cells.append(
                    AssignmentProgressCellResponse(
                        student_id=assignee.student_id,
                        question_id=question.id,
                        status="not_submitted",
                    )
                )

    return AssignmentProgressResponse(
        assignment_id=assignment.id,
        title=assignment.title,
        questions=[
            AssignmentProgressQuestionResponse(id=question.id, title=question.title or f"第 {index + 1} 题", sort_order=question.sort_order)
            for index, question in enumerate(questions)
        ],
        students=[
            AssignmentProgressStudentResponse(id=assignee.student_id, username=assignee.student.username)
            for assignee in assignees
        ],
        cells=cells,
    )


def get_teacher_submission_detail(
    db: Session,
    teacher: User,
    assignment_id: int,
    submission_id: int,
) -> AssignmentSubmissionDetailResponse:
    assignment = _get_teacher_assignment(db, teacher, assignment_id)
    submission = (
        db.query(AssignmentSubmission)
        .options(
            selectinload(AssignmentSubmission.question),
            selectinload(AssignmentSubmission.student),
        )
        .filter(
            AssignmentSubmission.id == submission_id,
            AssignmentSubmission.assignment_id == assignment.id,
        )
        .first()
    )
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提交记录不存在。")

    return AssignmentSubmissionDetailResponse(
        id=submission.id,
        assignment_id=submission.assignment_id,
        question_id=submission.question_id,
        question_title=submission.question.title if submission.question else "",
        student_id=submission.student_id,
        student_username=submission.student.username if submission.student else "",
        code=submission.code,
        status=submission.status,
        results_json=submission.results_json,
        run_time_ms=_sum_run_time_ms(submission.results_json),
        started_at=submission.started_at,
        duration_seconds=submission.duration_seconds,
        submitted_at=submission.submitted_at,
    )


def assignment_ai_help(
    db: Session,
    student: User,
    assignment_id: int,
    question_id: int,
    payload: AssignmentAiHelpRequest,
) -> AssignmentAiHelpResponse:
    client, help_context, keywords, facts, reasoning_trace, retrieval_trace = _prepare_assignment_rag_help(
        db,
        student,
        assignment_id,
        question_id,
        payload,
    )

    try:
        answer = _generate_assignment_rag_help(client, help_context, facts)
        return AssignmentAiHelpResponse(
            answer=answer,
            keywords=[str(item) for item in keywords],
            facts=facts,
            reasoning_trace=reasoning_trace,
            retrieval_trace=retrieval_trace,
        )
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AI 帮助失败：{error}") from error


def assignment_ai_help_stream(
    db: Session,
    student: User,
    assignment_id: int,
    question_id: int,
    payload: AssignmentAiHelpRequest,
):
    client, help_context, keywords, facts, reasoning_trace, retrieval_trace = _prepare_assignment_rag_help(
        db,
        student,
        assignment_id,
        question_id,
        payload,
    )
    yield _sse_event(
        "metadata",
        {
            "keywords": [str(item) for item in keywords],
            "facts": facts,
            "reasoning_trace": reasoning_trace,
            "retrieval_trace": retrieval_trace,
        },
    )

    chunks: list[str] = []
    try:
        for chunk in _stream_assignment_rag_help(client, help_context, facts):
            chunks.append(chunk)
            yield _sse_event("answer_delta", {"content": chunk})
        yield _sse_event("answer_done", {"answer": "".join(chunks)})
    except Exception as error:
        yield _sse_event("error", {"detail": f"AI 帮助失败：{error}"})


def _prepare_assignment_rag_help(
    db: Session,
    student: User,
    assignment_id: int,
    question_id: int,
    payload: AssignmentAiHelpRequest,
):
    assignment = _get_student_assignment(db, student, assignment_id)
    question = _get_assignment_question(assignment, question_id)
    client = get_openai_client()
    reasoning_trace: list = []
    retrieval_trace: list = []
    help_context = _build_assignment_help_context(assignment, question, payload)

    try:
        driver = get_neo4j_driver()
        keywords = rag_engine.extract_keywords_with_llm(
            client,
            help_context,
            history=[],
            trace=reasoning_trace,
        )
        facts = rag_engine.query_graph_with_reasoning(
            driver,
            client,
            help_context,
            keywords=keywords,
            max_depth=2,
            width=3,
            reasoning_trace=reasoning_trace,
            retrieval_trace=retrieval_trace,
        )
    except Exception as error:
        print(f"[assignment_ai_help] 图谱检索失败: {error}")
        keywords = []
        facts = []
        retrieval_trace.append(
            {
                "type": "retrieval",
                "title": "图谱检索失败",
                "summary": "本次未能完成知识图谱检索，已退回到作业上下文辅导。",
                "details": [str(error)],
                "stage": "assignment_rag",
                "mode": "student",
            }
        )
    return client, help_context, keywords, facts, reasoning_trace, retrieval_trace


def _build_assignment_help_context(assignment: Assignment, question: AssignmentQuestion, payload: AssignmentAiHelpRequest) -> str:
    return f"""
作业：{assignment.title}
作业说明：{assignment.description or "无"}
题目：{question.title or "编程题"}
题目描述：
{question.prompt}

学生问题：
{payload.message}

学生当前代码：
```java
{payload.code or "学生暂未提供代码"}
```

最近运行结果：
{json.dumps(payload.last_result or {}, ensure_ascii=False)}
"""


def _build_assignment_help_prompt(help_context: str, facts: list) -> str:
    knowledge_text = rag_engine.build_knowledge_text(facts) if facts else "本次没有检索到明确的图谱知识点。"
    return f"""
你是一名 Java 编程作业助教。请基于【知识图谱检索结果】和【作业上下文】帮助学生学习。

要求：
1. 优先基于检索到的知识点解释，不要脱离题目空泛讲解。
2. 不要直接给出完整可复制的标准答案。
3. 如果代码有编译或运行错误，先解释错误类型，再给最小修改方向。
4. 如果测试输出不匹配，指出可能相关的概念误区和下一步排查方法。
5. 回答要中文、具体、分步骤，建议控制在 4 到 8 句话。
6. 可以给短小代码片段或伪代码，但不要提供整题完整答案。

【知识图谱检索结果】
{knowledge_text}

【作业上下文】
{help_context}
"""


def _generate_assignment_rag_help(client, help_context: str, facts: list) -> str:
    prompt = _build_assignment_help_prompt(help_context, facts)
    response = client.chat.completions.create(
        model=settings.llm_model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.35,
    )
    return (response.choices[0].message.content or "").strip()


def _stream_assignment_rag_help(client, help_context: str, facts: list):
    prompt = _build_assignment_help_prompt(help_context, facts)
    stream = client.chat.completions.create(
        model=settings.llm_model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.35,
        stream=True,
    )
    for chunk in stream:
        content = chunk.choices[0].delta.content if chunk.choices else None
        if content:
            yield content


def _sse_event(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


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


def _duration_seconds(started_at: datetime | None, submitted_at: datetime) -> int | None:
    if not started_at:
        return None
    started_at = _strip_timezone(started_at)
    submitted_at = _strip_timezone(submitted_at) or submitted_at
    return max(0, int((submitted_at - started_at).total_seconds()))


def _strip_timezone(value: datetime | None) -> datetime | None:
    if value and value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value


def _sum_run_time_ms(results_json) -> int | None:
    if not isinstance(results_json, list):
        return None
    values = [
        int(item.get("elapsed_ms", 0))
        for item in results_json
        if isinstance(item, dict) and item.get("elapsed_ms") is not None
    ]
    if not values:
        return None
    return sum(values)
