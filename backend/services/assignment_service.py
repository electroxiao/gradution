import json
import re
import hashlib
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from backend.core.config import settings
from backend.db.session import SessionLocal
from backend.models.assignment import (
    Assignment,
    AssignmentAssignee,
    AssignmentQuestion,
    AssignmentQuestionKnowledgeNode,
    AssignmentSubmission,
    AssignmentTestCase,
    QuestionBankItem,
)
from backend.models.knowledge import KnowledgeNode
from backend.models.user import User
from backend.schemas.assignment import (
    AssignmentAiHelpRequest,
    AssignmentBulkSubmitRequest,
    AssignmentCreateRequest,
    AssignmentDetailResponse,
    AssignmentGeneratedFocusResponse,
    AssignmentGeneratedQuestionResponse,
    AssignmentGenerateFocusRequest,
    AssignmentGenerateQuestionRequest,
    AssignmentGenerateTestCasesRequest,
    AssignmentProgressCellResponse,
    AssignmentProgressQuestionResponse,
    AssignmentProgressResponse,
    AssignmentProgressStudentResponse,
    AssignmentQuestionInput,
    AssignmentQuestionsUpdateRequest,
    AssignmentReviewRequest,
    AssignmentStudentRef,
    AssignmentSubmissionDetailResponse,
    AssignmentSubmissionHistoryResponse,
    AssignmentSubmissionResponse,
    AssignmentSummaryResponse,
    AssignmentTestCaseInput,
    AssignmentUpdateRequest,
    QuestionBankItemResponse,
)
from backend.services import rag_engine
from backend.services.chat_service import get_openai_client
from backend.services.knowledge_progress_service import mark_node_weak
from backend.services.neo4j_service import get_neo4j_driver
from backend.services.sandbox_service import run_java_submission


VALID_ASSIGNMENT_STATUSES = {"draft", "published", "closed"}
VALID_GRADING_MODES = {"testcase", "ai_review", "hybrid", "observed_ai"}
VALID_AI_REVIEW_LEVELS = {"light", "deep"}
VALID_REVIEW_STATUSES = {"accepted", "teacher_rejected"}
VALID_QUESTION_TYPES = {"programming", "multiple_choice", "fill_blank"}
FAST_PASS_THRESHOLD_SECONDS = 60


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
        starts_at=payload.starts_at,
        due_at=payload.due_at,
    )
    db.add(assignment)
    db.flush()
    _replace_assignees(db, assignment, _resolve_assignee_student_ids(db, payload.student_ids, payload.class_names))
    _sync_questions(db, assignment, payload.questions)
    _sync_assignment_questions_to_bank(db, teacher, assignment)
    db.commit()
    return get_teacher_assignment_detail(db, teacher, assignment.id)


def get_teacher_assignment_detail(db: Session, teacher: User, assignment_id: int) -> AssignmentDetailResponse:
    assignment = _get_teacher_assignment(db, teacher, assignment_id)
    return _assignment_detail(db, assignment, teacher_view=True, student=None)


def delete_assignment(db: Session, teacher: User, assignment_id: int) -> None:
    assignment = _get_teacher_assignment(db, teacher, assignment_id)
    db.delete(assignment)
    db.commit()


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
    if "starts_at" in payload.model_fields_set:
        assignment.starts_at = payload.starts_at
    if "due_at" in payload.model_fields_set:
        assignment.due_at = payload.due_at
    if payload.student_ids is not None or payload.class_names is not None:
        _replace_assignees(
            db,
            assignment,
            _resolve_assignee_student_ids(db, payload.student_ids or [], payload.class_names or []),
        )
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
    _sync_assignment_questions_to_bank(db, teacher, assignment)
    db.commit()
    return get_teacher_assignment_detail(db, teacher, assignment_id)


def generate_assignment_questions(db: Session, payload: AssignmentGenerateQuestionRequest) -> AssignmentGeneratedQuestionResponse:
    requested_total = payload.programming_count + payload.multiple_choice_count + payload.fill_blank_count
    if requested_total <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="至少需要生成一道题目。")
    prompt = f"""
你是一名 Java 课程作业设计助手。请根据教师要求一次生成多道作业题，支持编程题、选择题和填空题。

知识点：{payload.knowledge_point or "未指定"}
教师要求：{payload.requirement}

数量：
- 编程题：{payload.programming_count}
- 选择题：{payload.multiple_choice_count}
- 填空题：{payload.fill_blank_count}

要求：
1. 只返回 JSON，不要解释。
2. question_type 只能是 programming、multiple_choice、fill_blank。
3. 编程题面向 Java 初学者，主类固定 Main，给出 2 到 4 个测试用例。
4. 选择题 options 使用 key/text，answer 填正确 key，可单选。
5. 填空题 answer 填参考答案字符串或字符串数组，explanation 给简短解析。

JSON 格式：
{{
  "questions": [
    {{
      "title": "题目标题",
      "prompt": "题目描述",
      "question_type": "multiple_choice",
      "options": [{{"key": "A", "text": "选项"}}],
      "answer": "A",
      "explanation": "解析",
      "language": "java",
      "test_cases": []
    }}
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
        data = _parse_json_object(response.choices[0].message.content or "")
        raw_questions = data.get("questions") if isinstance(data.get("questions"), list) else []
        questions = []
        for index, raw in enumerate(raw_questions):
            if not isinstance(raw, dict):
                continue
            question_type = _normalize_question_type(raw.get("question_type"))
            title = str(raw.get("title") or f"题目 {index + 1}").strip()
            prompt_text = str(raw.get("prompt") or payload.requirement).strip()
            knowledge_nodes = _recommend_assignment_knowledge_nodes(db, title, prompt_text, payload)
            questions.append(
                {
                    "title": title,
                    "prompt": prompt_text,
                    "question_type": question_type,
                    "options": _normalize_options(raw.get("options")),
                    "answer": _normalize_answer(raw.get("answer")),
                    "explanation": str(raw.get("explanation") or "").strip(),
                    "language": "java",
                    "test_cases": _normalize_generated_test_cases(raw.get("test_cases"), question_type),
                    "knowledge_node_ids": [item["id"] for item in knowledge_nodes],
                    "knowledge_nodes": knowledge_nodes,
                }
            )
        if not questions:
            raise ValueError("大模型未返回有效题目。")
        first = questions[0]
        return AssignmentGeneratedQuestionResponse(
            title=first["title"],
            prompt=first["prompt"],
            question_type=first["question_type"],
            options=first["options"],
            answer=first["answer"],
            explanation=first["explanation"],
            language="java",
            test_cases=first["test_cases"],
            knowledge_node_ids=first["knowledge_node_ids"],
            knowledge_nodes=first["knowledge_nodes"],
            questions=questions,
        )
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"生成题目失败：{error}") from error


def _recommend_assignment_knowledge_nodes(
    db: Session,
    title: str,
    prompt: str,
    payload: AssignmentGenerateQuestionRequest,
    limit: int = 5,
) -> list[dict]:
    query_text = "\n".join(
        item
        for item in [
            f"知识点：{payload.knowledge_point}" if payload.knowledge_point else "",
            f"教师要求：{payload.requirement}",
            f"题目标题：{title}",
            f"题目描述：{prompt}",
        ]
        if item
    )
    keywords = []
    try:
        client = get_openai_client()
        driver = get_neo4j_driver()
        keywords = rag_engine.extract_keywords_with_llm(client, query_text)
        facts = rag_engine.query_graph_with_reasoning(
            driver,
            client,
            query_text,
            keywords=keywords,
            max_depth=2,
            width=4,
            entity_top_k=6,
        )
    except Exception:
        facts = []

    candidates: list[str] = []
    for keyword in [payload.knowledge_point, *keywords]:
        if keyword:
            candidates.append(str(keyword))
    for fact in facts:
        if not isinstance(fact, dict):
            continue
        for key in ["node_name", "seed", "target", "source"]:
            if fact.get(key):
                candidates.append(str(fact[key]))

    seen: set[str] = set()
    node_names = []
    for name in candidates:
        value = name.strip()
        if value and value not in seen:
            seen.add(value)
            node_names.append(value)
        if len(node_names) >= limit:
            break

    graph_node_names = _filter_existing_graph_node_names(node_names)
    return _ensure_assignment_knowledge_node_refs(db, graph_node_names)


def _filter_existing_graph_node_names(node_names: list[str]) -> list[str]:
    if not node_names:
        return []
    try:
        driver = get_neo4j_driver()
        with driver.session(database=settings.neo4j_db_name) as session:
            records = session.run(
                """
                UNWIND $names AS candidate
                MATCH (n:Knowledge {name: candidate})
                RETURN DISTINCT n.name AS node_name
                """,
                names=node_names,
            )
            existing = {record["node_name"] for record in records if record["node_name"]}
    except Exception:
        return []
    return [name for name in node_names if name in existing]


def _ensure_assignment_knowledge_node_refs(db: Session, node_names: list[str]) -> list[dict]:
    if not node_names:
        return []
    existing = {
        row.node_name: row
        for row in db.query(KnowledgeNode).filter(KnowledgeNode.node_name.in_(node_names)).all()
    }
    result = []
    for node_name in node_names:
        row = existing.get(node_name)
        if not row:
            row = KnowledgeNode(node_name=node_name)
            db.add(row)
            db.flush()
            existing[node_name] = row
        result.append({"id": row.id, "node_name": row.node_name})
    db.commit()
    return result


def generate_assignment_test_cases(payload: AssignmentGenerateTestCasesRequest) -> list[AssignmentTestCaseInput]:
    prompt = f"""
你是一名 Java 编程作业测试用例设计助手。请根据题目内容生成 2 到 4 个测试用例。

知识点：{payload.knowledge_point or "未指定"}
题目标题：{payload.title or "未命名题目"}
题目描述：
{payload.prompt}

要求：
1. 只返回 JSON 数组，不要解释。
2. 每项包含 input_data、expected_output、is_sample、sort_order。
3. 至少 1 个示例测试，至少 1 个隐藏测试。
4. 默认主类为 Main，从标准输入读取，从标准输出打印。
"""
    client = get_openai_client()
    try:
        response = client.chat.completions.create(
            model=settings.llm_model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
        )
        content = response.choices[0].message.content or ""
        data = _parse_json_array(content)
        test_cases = [
            AssignmentTestCaseInput(
                input_data=item.get("input_data", ""),
                expected_output=item.get("expected_output", ""),
                is_sample=bool(item.get("is_sample", index == 0)),
                sort_order=int(item.get("sort_order", index)),
            )
            for index, item in enumerate(data)
            if isinstance(item, dict)
        ]
        return test_cases or [AssignmentTestCaseInput(input_data="", expected_output="", is_sample=True, sort_order=0)]
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"生成测试用例失败：{error}",
        ) from error


def generate_assignment_focus(payload: AssignmentGenerateFocusRequest) -> AssignmentGeneratedFocusResponse:
    review_level = _normalize_ai_review_level(payload.ai_review_level)
    prompt = f"""
你是一名编程作业代码审查助手。请根据题目内容和教师评分标准，给出 AI 评审应该重点关注的方面。

题目标题：{payload.title or "未命名题目"}
题目描述：
{payload.prompt}

教师评分标准：
{payload.ai_grading_rubric or "未填写"}

审查强度：{review_level}

要求：
1. 只返回 JSON，不要解释。
2. ai_grading_focus 为字符串数组。
3. summary 用 1 到 2 句话说明建议原因。

JSON 格式：
{{
  "ai_grading_focus": ["边界条件", "异常处理"],
  "summary": "建议重点检查这些方面。"
}}
"""
    client = get_openai_client()
    try:
        response = client.chat.completions.create(
            model=settings.llm_model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        content = response.choices[0].message.content or ""
        data = _parse_json_object(content)
        return AssignmentGeneratedFocusResponse(
            ai_grading_focus=_normalize_ai_focus(data.get("ai_grading_focus")),
            summary=str(data.get("summary") or "").strip(),
        )
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"生成 AI 关注点失败：{error}",
        ) from error


def list_question_bank_items(
    db: Session,
    teacher: User,
    keyword: str = "",
    question_type: str = "",
    chapter: str = "",
    limit: int = 50,
) -> list[QuestionBankItemResponse]:
    query = db.query(QuestionBankItem).filter(QuestionBankItem.teacher_id == teacher.id)
    if keyword.strip():
        like = f"%{keyword.strip()}%"
        query = query.filter((QuestionBankItem.title.like(like)) | (QuestionBankItem.prompt.like(like)))
    if question_type.strip():
        query = query.filter(QuestionBankItem.question_type == _normalize_question_type(question_type))
    ordered_query = query.order_by(QuestionBankItem.updated_at.desc(), QuestionBankItem.id.desc())
    chapter_filter = chapter.strip()
    if chapter_filter:
        rows = ordered_query.all()
        rows = [row for row in rows if chapter_filter in _question_bank_item_chapters(db, row)]
        rows = rows[:limit]
    else:
        rows = ordered_query.limit(limit).all()
    return [_question_bank_item_response(row, db) for row in rows]


def create_question_bank_item(db: Session, teacher: User, payload: AssignmentQuestionInput) -> QuestionBankItemResponse:
    row = _upsert_question_bank_item(db, teacher, payload, increment_reuse=False)
    db.commit()
    db.refresh(row)
    return _question_bank_item_response(row, db)


def reuse_question_bank_item(db: Session, teacher: User, item_id: int) -> QuestionBankItemResponse:
    row = db.query(QuestionBankItem).filter(QuestionBankItem.id == item_id, QuestionBankItem.teacher_id == teacher.id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题库题目不存在。")
    row.reuse_count = int(row.reuse_count or 0) + 1
    db.commit()
    db.refresh(row)
    return _question_bank_item_response(row, db)


def delete_question_bank_item(db: Session, teacher: User, item_id: int) -> None:
    row = db.query(QuestionBankItem).filter(QuestionBankItem.id == item_id, QuestionBankItem.teacher_id == teacher.id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题库题目不存在。")
    db.delete(row)
    db.commit()


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


def submit_assignment(
    db: Session,
    student: User,
    assignment_id: int,
    payload: AssignmentBulkSubmitRequest,
) -> dict:
    assignment = _get_student_assignment(db, student, assignment_id)
    questions = sorted(assignment.questions, key=lambda item: (item.sort_order, item.id))
    question_by_id = {question.id: question for question in questions}
    answer_by_question_id = {item.question_id: item for item in payload.answers}
    unknown_ids = [question_id for question_id in answer_by_question_id if question_id not in question_by_id]
    if unknown_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="提交内容包含不属于当前作业的题目。")
    missing_ids = [question.id for question in questions if question.id not in answer_by_question_id]
    if missing_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请完成所有题目后再提交作业。")

    submitted_at = datetime.now()
    submissions: list[AssignmentSubmission] = []
    for question in questions:
        item = answer_by_question_id.get(question.id)
        if not item:
            continue
        question_type = _normalize_question_type(question.question_type)
        if question_type == "programming":
            code = (item.code or "").strip()
            if not code:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"请完成题目“{question.title or question.id}”。")
            answer = None
        else:
            code = ""
            answer = _normalize_answer(item.answer)
            if _answer_is_empty(answer):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"请完成题目“{question.title or question.id}”。")

        previous_submission = _get_previous_submission(db, student.id, assignment.id, question.id)
        started_at = _resolve_submission_started_at(item.started_at, previous_submission)
        submission = AssignmentSubmission(
            assignment_id=assignment.id,
            question_id=question.id,
            student_id=student.id,
            code=code,
            answer_json=answer,
            status="submitted",
            results_json=[
                {
                    "case_index": 1,
                    "status": "submitted",
                    "check_mode": "background",
                    "summary": "已提交，系统正在后台判题。",
                }
            ],
            ai_review_json=None,
            final_decision_source="background_pending",
            started_at=started_at,
            duration_seconds=_duration_seconds(started_at, submitted_at),
            submitted_at=submitted_at,
        )
        db.add(submission)
        db.flush()
        submissions.append(submission)

    db.commit()
    return {
        "detail": "提交成功，系统将在后台完成判题。",
        "submission_ids": [submission.id for submission in submissions],
        "submitted_count": len(submissions),
    }


def grade_assignment_submissions_in_background(submission_ids: list[int]) -> None:
    if not submission_ids:
        return
    db = SessionLocal()
    try:
        for submission_id in submission_ids:
            _grade_pending_assignment_submission(db, submission_id)
    finally:
        db.close()


def _grade_pending_assignment_submission(db: Session, submission_id: int) -> None:
    submission = db.query(AssignmentSubmission).filter(AssignmentSubmission.id == submission_id).first()
    if not submission or submission.status != "submitted":
        return
    assignment = submission.assignment
    question = submission.question
    student = submission.student
    try:
        question_type = _normalize_question_type(question.question_type)
        if question_type == "programming":
            status_value, results, ai_review, decision_source = _grade_submission(assignment, question, submission.code or "")
            previous_submission = _get_previous_submission_before(db, submission)
            previous_code = (previous_submission.code or "") if previous_submission else ""
            trust_label, trust_score = _resolve_submission_trust(
                status_value,
                submission.duration_seconds,
                submission.code or "",
                previous_code,
            )
            submission.trust_label = trust_label
            submission.trust_score = trust_score
        elif question_type == "multiple_choice":
            status_value, results, ai_review, decision_source = _grade_multiple_choice_locally(question, submission.answer_json)
        else:
            normalized_answer = _normalize_answer(submission.answer_json)
            ai_review = _run_ai_objective_review(assignment, question, normalized_answer)
            status_value = _resolve_ai_only_status(question, ai_review)
            results = [
                {
                    "case_index": 1,
                    "status": status_value,
                    "check_mode": "ai_objective_review",
                    "summary": ai_review.get("summary") if isinstance(ai_review, dict) else "",
                }
            ]
            decision_source = "ai_objective_review"

        submission.status = status_value
        submission.results_json = results
        submission.ai_review_json = ai_review
        submission.final_decision_source = decision_source
        _mark_wrong_submission_bound_nodes_weak(db, student, question, submission)
        db.commit()
    except Exception as error:
        db.rollback()
        submission = db.query(AssignmentSubmission).filter(AssignmentSubmission.id == submission_id).first()
        if not submission:
            return
        submission.status = "sandbox_error"
        submission.results_json = [
            {
                "case_index": 1,
                "status": "sandbox_error",
                "check_mode": "background",
                "summary": f"后台判题失败：{error}",
            }
        ]
        submission.final_decision_source = "background_error"
        db.commit()


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
    return [_submission_to_response(item, student_visible=True) for item in submissions]


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
            AssignmentProgressQuestionResponse(
                id=question.id,
                title=question.title or f"第 {index + 1} 题",
                question_type=_normalize_question_type(question.question_type),
                sort_order=question.sort_order,
                knowledge_nodes=[
                    {"id": relation.knowledge_node.id, "node_name": relation.knowledge_node.node_name}
                    for relation in sorted(question.knowledge_nodes, key=lambda item: (item.sort_order, item.id))
                    if relation.knowledge_node
                ],
            )
            for index, question in enumerate(questions)
        ],
        students=[
            AssignmentProgressStudentResponse(id=assignee.student_id, username=assignee.student.username, class_name=assignee.student.class_name)
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
            selectinload(AssignmentSubmission.reviewer),
        )
        .filter(
            AssignmentSubmission.id == submission_id,
            AssignmentSubmission.assignment_id == assignment.id,
        )
        .first()
    )
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提交记录不存在。")

    return _teacher_submission_detail_response(submission)


def list_teacher_question_submissions(
    db: Session,
    teacher: User,
    assignment_id: int,
    student_id: int,
    question_id: int,
) -> AssignmentSubmissionHistoryResponse:
    assignment = _get_teacher_assignment(db, teacher, assignment_id)
    assigned_student_ids = {assignee.student_id for assignee in assignment.assignees}
    question_ids = {question.id for question in assignment.questions}
    if student_id not in assigned_student_ids or question_id not in question_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学生或题目不属于该作业。")

    submissions = (
        db.query(AssignmentSubmission)
        .options(
            selectinload(AssignmentSubmission.question),
            selectinload(AssignmentSubmission.student),
            selectinload(AssignmentSubmission.reviewer),
        )
        .filter(
            AssignmentSubmission.assignment_id == assignment.id,
            AssignmentSubmission.student_id == student_id,
            AssignmentSubmission.question_id == question_id,
        )
        .order_by(AssignmentSubmission.submitted_at.desc(), AssignmentSubmission.id.desc())
        .all()
    )
    return AssignmentSubmissionHistoryResponse(
        submissions=[_teacher_submission_detail_response(submission) for submission in submissions]
    )


def _teacher_submission_detail_response(submission: AssignmentSubmission) -> AssignmentSubmissionDetailResponse:
    return AssignmentSubmissionDetailResponse(
        id=submission.id,
        assignment_id=submission.assignment_id,
        question_id=submission.question_id,
        question_title=submission.question.title if submission.question else "",
        student_id=submission.student_id,
        student_username=submission.student.username if submission.student else "",
        code=submission.code,
        answer=submission.answer_json,
        status=submission.status,
        results_json=submission.results_json,
        ai_review_json=submission.ai_review_json,
        decision_source=submission.final_decision_source,
        teacher_review_note=submission.teacher_review_note,
        trust_label=submission.trust_label,
        trust_score=submission.trust_score,
        reviewed_at=submission.reviewed_at,
        reviewed_by=submission.reviewed_by,
        reviewed_by_username=submission.reviewer.username if submission.reviewer else None,
        run_time_ms=_sum_run_time_ms(submission.results_json),
        started_at=submission.started_at,
        duration_seconds=submission.duration_seconds,
        submitted_at=submission.submitted_at,
    )


def review_assignment_submission(
    db: Session,
    teacher: User,
    assignment_id: int,
    submission_id: int,
    payload: AssignmentReviewRequest,
) -> AssignmentSubmissionDetailResponse:
    assignment = _get_teacher_assignment(db, teacher, assignment_id)
    submission = (
        db.query(AssignmentSubmission)
        .options(
            selectinload(AssignmentSubmission.question),
            selectinload(AssignmentSubmission.student),
            selectinload(AssignmentSubmission.reviewer),
        )
        .filter(
            AssignmentSubmission.id == submission_id,
            AssignmentSubmission.assignment_id == assignment.id,
        )
        .first()
    )
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="提交记录不存在。")
    if payload.status not in VALID_REVIEW_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="教师改判状态非法。")

    submission.status = payload.status
    submission.final_decision_source = "teacher_override"
    submission.teacher_review_note = payload.note.strip() or None
    submission.reviewed_at = datetime.now()
    submission.reviewed_by = teacher.id
    db.commit()
    db.refresh(submission)
    return get_teacher_submission_detail(db, teacher, assignment_id, submission_id)


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
        print(f"[assignment_ai_help_stream] 图谱检索失败: {error}")
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
            selectinload(Assignment.questions)
            .selectinload(AssignmentQuestion.knowledge_nodes)
            .selectinload(AssignmentQuestionKnowledgeNode.knowledge_node),
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
            selectinload(Assignment.questions)
            .selectinload(AssignmentQuestion.knowledge_nodes)
            .selectinload(AssignmentQuestionKnowledgeNode.knowledge_node),
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


def _resolve_assignee_student_ids(db: Session, student_ids: list[int], class_names: list[str]) -> list[int]:
    resolved = set(int(item) for item in student_ids if str(item).strip())
    normalized_classes = [item.strip() for item in class_names if str(item).strip()]
    if normalized_classes:
        class_student_ids = db.query(User.id).filter(User.role == "student", User.class_name.in_(normalized_classes)).all()
        resolved.update(int(row.id) for row in class_student_ids)
    return sorted(resolved)


def _sync_questions(db: Session, assignment: Assignment, payload_questions: list[AssignmentQuestionInput]) -> None:
    existing = {question.id: question for question in assignment.questions}
    keep_ids: set[int] = set()

    for index, item in enumerate(payload_questions):
        question_type = _normalize_question_type(item.question_type)
        if question_type == "programming" and item.language != "java":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前仅支持 Java 题目。")
        ai_review_level = _normalize_ai_review_level(item.ai_review_level)
        grading_mode = _resolve_grading_mode(item) if question_type == "programming" else "ai_review"
        sort_order = item.sort_order if item.sort_order is not None else index
        if item.id and item.id in existing:
            question = existing[item.id]
            keep_ids.add(question.id)
            question.title = item.title
            question.prompt = item.prompt
            question.question_type = question_type
            question.options_json = [option.model_dump() for option in item.options]
            question.answer_json = _normalize_answer(item.answer)
            question.explanation = item.explanation or ""
            question.starter_code = item.starter_code or ""
            question.language = "java"
            question.grading_mode = grading_mode
            question.ai_grading_rubric = (item.ai_grading_rubric or "").strip()
            question.ai_grading_focus_json = _normalize_ai_focus(item.ai_grading_focus)
            question.sort_order = sort_order
        else:
            question = AssignmentQuestion(
                assignment=assignment,
                title=item.title,
                prompt=item.prompt,
                question_type=question_type,
                options_json=[option.model_dump() for option in item.options],
                answer_json=_normalize_answer(item.answer),
                explanation=item.explanation or "",
                starter_code=item.starter_code or "",
                language="java",
                grading_mode=grading_mode,
                ai_grading_rubric=(item.ai_grading_rubric or "").strip(),
                ai_grading_focus_json=_normalize_ai_focus(item.ai_grading_focus),
                sort_order=sort_order,
            )
            db.add(question)
            db.flush()
            keep_ids.add(question.id)
        _sync_test_cases(db, question, item.test_cases if question_type == "programming" else [])
        _sync_question_knowledge_nodes(db, question, item.knowledge_node_ids)

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
            test_case.input_data = item.input_data or ""
            test_case.expected_output = item.expected_output or ""
            test_case.is_sample = item.is_sample
            test_case.sort_order = sort_order
        else:
            test_case = AssignmentTestCase(
                question=question,
                input_data=item.input_data or "",
                expected_output=item.expected_output or "",
                is_sample=item.is_sample,
                sort_order=sort_order,
            )
            db.add(test_case)
            db.flush()
            keep_ids.add(test_case.id)

    for test_case in list(question.test_cases):
        if test_case.id not in keep_ids:
            db.delete(test_case)


def _sync_question_knowledge_nodes(db: Session, question: AssignmentQuestion, knowledge_node_ids: list[int]) -> None:
    normalized_ids = list(dict.fromkeys(int(item) for item in knowledge_node_ids if str(item).strip()))
    if normalized_ids:
        count = db.query(func.count(KnowledgeNode.id)).filter(KnowledgeNode.id.in_(normalized_ids)).scalar()
        if count != len(normalized_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="题目绑定的知识点包含无效节点。")

    existing = {item.knowledge_node_id: item for item in question.knowledge_nodes}
    keep_ids: set[int] = set()
    for index, node_id in enumerate(normalized_ids):
        relation = existing.get(node_id)
        if relation:
            relation.sort_order = index
            keep_ids.add(relation.id)
            continue
        relation = AssignmentQuestionKnowledgeNode(
            question=question,
            knowledge_node_id=node_id,
            sort_order=index,
        )
        db.add(relation)
        db.flush()
        keep_ids.add(relation.id)

    for relation in list(question.knowledge_nodes):
        if relation.id not in keep_ids:
            db.delete(relation)


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
        starts_at=assignment.starts_at,
        due_at=assignment.due_at,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
        question_count=len(assignment.questions),
        assignee_count=len(assignment.assignees),
        submitted_count=submitted_count,
        accepted_count=accepted_count,
        class_names=sorted({item.student.class_name for item in assignment.assignees if item.student and item.student.class_name}),
        question_type_counts=_question_type_counts(assignment),
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
        knowledge_nodes = [
            {
                "id": relation.knowledge_node.id,
                "node_name": relation.knowledge_node.node_name,
            }
            for relation in sorted(question.knowledge_nodes, key=lambda item: (item.sort_order, item.id))
            if relation.knowledge_node
        ]
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
                    "question_type": _normalize_question_type(question.question_type),
                    "options": _normalize_options(question.options_json),
                    "answer": question.answer_json if teacher_view else None,
                    "explanation": question.explanation or "",
                    "starter_code": question.starter_code or "",
                    "knowledge_node_ids": [item["id"] for item in knowledge_nodes],
                    "knowledge_nodes": knowledge_nodes,
                    "language": question.language,
                    "grading_mode": _normalize_grading_mode(question.grading_mode),
                    "enable_testcases": _question_enable_testcases(question),
                    "ai_review_level": _question_ai_review_level(question),
                    "ai_grading_rubric": question.ai_grading_rubric or "",
                    "ai_grading_focus": _normalize_ai_focus(question.ai_grading_focus_json),
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
        starts_at=assignment.starts_at,
        due_at=assignment.due_at,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
        questions=questions,
        assigned_students=[
            AssignmentStudentRef.model_validate(item.student)
            for item in assignment.assignees
            if teacher_view and item.student
        ],
        class_names=sorted({
            item.student.class_name
            for item in assignment.assignees
            if item.student and item.student.class_name
        }),
        submissions=[_submission_to_response(item, student_visible=not teacher_view) for item in submissions],
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
    started_at = _to_naive_local(started_at)
    submitted_at = _to_naive_local(submitted_at) or submitted_at
    return max(0, int((submitted_at - started_at).total_seconds()))


def _to_naive_local(value: datetime | None) -> datetime | None:
    if value and value.tzinfo is not None:
        return value.astimezone().replace(tzinfo=None)
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


def _student_visible_results(results_json):
    if not isinstance(results_json, list):
        return results_json
    visible_results = []
    for item in results_json:
        if not isinstance(item, dict):
            visible_results.append(item)
            continue
        visible = dict(item)
        if not visible.get("is_sample", True):
            visible["input"] = ""
            visible["expected_output"] = ""
            visible["actual_output"] = ""
            if visible.get("status") == "accepted":
                visible["stderr"] = ""
            visible.setdefault("summary", "隐藏测试用例")
        visible_results.append(visible)
    return visible_results


def _normalize_grading_mode(value: str | None) -> str:
    value = (value or "testcase").strip().lower()
    if value not in VALID_GRADING_MODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="判题模式必须是 testcase、observed_ai、ai_review 或 hybrid。",
        )
    return value


def _normalize_question_type(value: str | None) -> str:
    normalized = (value or "programming").strip().lower()
    if normalized not in VALID_QUESTION_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="题型必须是 programming、multiple_choice 或 fill_blank。")
    return normalized


def _normalize_options(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    options = []
    for index, item in enumerate(value):
        if isinstance(item, dict):
            key = str(item.get("key") or chr(65 + index)).strip()
            text = str(item.get("text") or "").strip()
        else:
            key = chr(65 + index)
            text = str(item).strip()
        if text:
            options.append({"key": key, "text": text})
    return options


def _normalize_answer(value):
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return value
    return str(value).strip()


def _normalize_generated_test_cases(value, question_type: str) -> list[AssignmentTestCaseInput]:
    if question_type != "programming" or not isinstance(value, list):
        return []
    return [
        AssignmentTestCaseInput(
            input_data=str(item.get("input_data") or ""),
            expected_output=str(item.get("expected_output") or ""),
            is_sample=bool(item.get("is_sample", index == 0)),
            sort_order=int(item.get("sort_order", index) or index),
        )
        for index, item in enumerate(value)
        if isinstance(item, dict)
    ]


def _question_type_counts(assignment: Assignment) -> dict[str, int]:
    counts = {"programming": 0, "multiple_choice": 0, "fill_blank": 0}
    for question in assignment.questions:
        question_type = _normalize_question_type(question.question_type)
        counts[question_type] = counts.get(question_type, 0) + 1
    return counts


def _sync_assignment_questions_to_bank(db: Session, teacher: User, assignment: Assignment) -> None:
    for question in assignment.questions:
        payload = AssignmentQuestionInput(
            title=question.title or "",
            prompt=question.prompt,
            question_type=_normalize_question_type(question.question_type),
            options=_normalize_options(question.options_json),
            answer=question.answer_json,
            explanation=question.explanation or "",
            starter_code=question.starter_code or "",
            knowledge_node_ids=[
                relation.knowledge_node_id
                for relation in sorted(question.knowledge_nodes, key=lambda item: (item.sort_order, item.id))
            ],
            language=question.language or "java",
            grading_mode=_normalize_grading_mode(question.grading_mode),
            ai_grading_rubric=question.ai_grading_rubric or "",
            ai_grading_focus=_normalize_ai_focus(question.ai_grading_focus_json),
            test_cases=[
                AssignmentTestCaseInput(
                    input_data=test_case.input_data or "",
                    expected_output=test_case.expected_output or "",
                    is_sample=test_case.is_sample,
                    sort_order=test_case.sort_order,
                )
                for test_case in sorted(question.test_cases, key=lambda item: (item.sort_order, item.id))
            ],
        )
        _upsert_question_bank_item(db, teacher, payload, increment_reuse=False)


def _upsert_question_bank_item(
    db: Session,
    teacher: User,
    payload: AssignmentQuestionInput,
    increment_reuse: bool = False,
) -> QuestionBankItem:
    question_type = _normalize_question_type(payload.question_type)
    content_hash = _question_bank_content_hash(teacher.id, question_type, payload.title, payload.prompt)
    row = (
        db.query(QuestionBankItem)
        .filter(QuestionBankItem.teacher_id == teacher.id, QuestionBankItem.content_hash == content_hash)
        .first()
    )
    values = {
        "title": payload.title.strip() or "未命名题目",
        "prompt": payload.prompt.strip(),
        "question_type": question_type,
        "options_json": [option.model_dump() if hasattr(option, "model_dump") else option for option in payload.options],
        "answer_json": _normalize_answer(payload.answer),
        "explanation": payload.explanation or "",
        "starter_code": payload.starter_code or "",
        "language": "java",
        "grading_mode": _resolve_grading_mode(payload) if question_type == "programming" else "ai_review",
        "ai_grading_rubric": (payload.ai_grading_rubric or "").strip(),
        "ai_grading_focus_json": _normalize_ai_focus(payload.ai_grading_focus),
        "test_cases_json": [item.model_dump() if hasattr(item, "model_dump") else item for item in payload.test_cases],
        "knowledge_node_ids_json": [int(item) for item in payload.knowledge_node_ids if str(item).strip()],
    }
    if row:
        for key, value in values.items():
            setattr(row, key, value)
        if increment_reuse:
            row.reuse_count = int(row.reuse_count or 0) + 1
        return row
    row = QuestionBankItem(teacher_id=teacher.id, content_hash=content_hash, reuse_count=1 if increment_reuse else 0, **values)
    db.add(row)
    db.flush()
    return row


def _question_bank_content_hash(teacher_id: int, question_type: str, title: str, prompt: str) -> str:
    raw = json.dumps(
        {
            "teacher_id": teacher_id,
            "question_type": question_type,
            "title": (title or "").strip(),
            "prompt": (prompt or "").strip(),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _question_bank_item_knowledge_node_ids(row: QuestionBankItem) -> list[int]:
    return [
        int(item)
        for item in (row.knowledge_node_ids_json if isinstance(row.knowledge_node_ids_json, list) else [])
        if str(item).strip()
    ]


def _question_bank_item_knowledge_nodes(db: Session | None, row: QuestionBankItem) -> list[dict]:
    node_ids = _question_bank_item_knowledge_node_ids(row)
    if not db or not node_ids:
        return []
    rows = db.query(KnowledgeNode).filter(KnowledgeNode.id.in_(node_ids)).all()
    by_id = {node.id: node for node in rows}
    return [
        {
            "id": node.id,
            "node_name": node.node_name,
            "chapter": node.chapter or "",
        }
        for node_id in node_ids
        if (node := by_id.get(node_id))
    ]


def _question_bank_item_chapters(db: Session, row: QuestionBankItem) -> set[str]:
    return {
        str(item.get("chapter") or "").strip()
        for item in _question_bank_item_knowledge_nodes(db, row)
        if str(item.get("chapter") or "").strip()
    }


def _question_bank_item_response(row: QuestionBankItem, db: Session | None = None) -> QuestionBankItemResponse:
    knowledge_node_ids = _question_bank_item_knowledge_node_ids(row)
    return QuestionBankItemResponse(
        id=row.id,
        title=row.title,
        prompt=row.prompt,
        question_type=_normalize_question_type(row.question_type),
        options=_normalize_options(row.options_json),
        answer=row.answer_json,
        explanation=row.explanation or "",
        starter_code=row.starter_code or "",
        language=row.language or "java",
        grading_mode=_normalize_grading_mode(row.grading_mode),
        ai_grading_rubric=row.ai_grading_rubric or "",
        ai_grading_focus=_normalize_ai_focus(row.ai_grading_focus_json),
        test_cases=[
            AssignmentTestCaseInput(**item)
            for item in (row.test_cases_json if isinstance(row.test_cases_json, list) else [])
            if isinstance(item, dict)
        ],
        knowledge_node_ids=knowledge_node_ids,
        knowledge_nodes=_question_bank_item_knowledge_nodes(db, row),
        reuse_count=int(row.reuse_count or 0),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _normalize_ai_review_level(value: str | None) -> str:
    value = (value or "light").strip().lower()
    if value not in VALID_AI_REVIEW_LEVELS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="AI 审查强度必须是 light 或 deep。")
    return value


def _grading_mode_from_new_fields(enable_testcases: bool, ai_review_level: str) -> str:
    ai_review_level = _normalize_ai_review_level(ai_review_level)
    if enable_testcases and ai_review_level == "light":
        return "testcase"
    if enable_testcases and ai_review_level == "deep":
        return "hybrid"
    return "ai_review"


def _resolve_grading_mode(item: AssignmentQuestionInput) -> str:
    if item.grading_mode:
        return _normalize_grading_mode(item.grading_mode)
    return _grading_mode_from_new_fields(bool(item.enable_testcases), item.ai_review_level)


def _question_enable_testcases(question: AssignmentQuestion) -> bool:
    return _normalize_grading_mode(question.grading_mode) != "ai_review"


def _question_ai_review_level(question: AssignmentQuestion) -> str:
    return "light" if _normalize_grading_mode(question.grading_mode) == "testcase" else "deep"


def _normalize_ai_focus(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        items = value.split(",")
    elif isinstance(value, list):
        items = value
    else:
        return []
    return [str(item).strip() for item in items if str(item).strip()]


def _submission_to_response(
    submission: AssignmentSubmission,
    student_visible: bool = False,
) -> AssignmentSubmissionResponse:
    return AssignmentSubmissionResponse(
        id=submission.id,
        assignment_id=submission.assignment_id,
        question_id=submission.question_id,
        student_id=submission.student_id,
        code=submission.code,
        answer=submission.answer_json,
        status=submission.status,
        results_json=_student_visible_results(submission.results_json) if student_visible else submission.results_json,
        ai_review_json=submission.ai_review_json,
        decision_source=submission.final_decision_source,
        teacher_review_note=submission.teacher_review_note,
        trust_label=submission.trust_label,
        trust_score=submission.trust_score,
        started_at=submission.started_at,
        duration_seconds=submission.duration_seconds,
        submitted_at=submission.submitted_at,
    )


def _get_previous_submission(
    db: Session,
    student_id: int,
    assignment_id: int,
    question_id: int,
) -> AssignmentSubmission | None:
    return (
        db.query(AssignmentSubmission)
        .filter(
            AssignmentSubmission.student_id == student_id,
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.question_id == question_id,
        )
        .order_by(AssignmentSubmission.submitted_at.desc(), AssignmentSubmission.id.desc())
        .first()
    )


def _get_previous_submission_before(db: Session, submission: AssignmentSubmission) -> AssignmentSubmission | None:
    return (
        db.query(AssignmentSubmission)
        .filter(
            AssignmentSubmission.student_id == submission.student_id,
            AssignmentSubmission.assignment_id == submission.assignment_id,
            AssignmentSubmission.question_id == submission.question_id,
            AssignmentSubmission.id != submission.id,
            AssignmentSubmission.submitted_at <= submission.submitted_at,
        )
        .order_by(AssignmentSubmission.submitted_at.desc(), AssignmentSubmission.id.desc())
        .first()
    )


def _resolve_submission_started_at(
    client_started_at: datetime | None,
    previous_submission: AssignmentSubmission | None,
) -> datetime | None:
    if previous_submission:
        return _to_naive_local(previous_submission.submitted_at)
    return _to_naive_local(client_started_at)


def _resolve_submission_trust(status_value: str, duration_seconds: int | None, code: str = "", previous_code: str = "") -> tuple[str, float]:
    if status_value != "accepted":
        return "normal", 1.0
    flags: list[str] = []
    trust = 1.0

    if duration_seconds is not None and duration_seconds <= FAST_PASS_THRESHOLD_SECONDS:
        flags.append("fast_submit")
        trust -= 0.4

    if previous_code and code == previous_code:
        flags.append("identical_code")
        trust -= 0.6

    if code and len(code.strip().splitlines()) < 3:
        flags.append("minimal_code")
        trust -= 0.3

    if flags:
        label = "suspicious_" + "_".join(flags)
        return label, max(0.0, trust)
    return "normal", 1.0


def _mark_wrong_submission_bound_nodes_weak(
    db: Session,
    student: User,
    question: AssignmentQuestion,
    submission: AssignmentSubmission,
) -> None:
    if submission.status == "accepted":
        return
    relations = sorted(question.knowledge_nodes, key=lambda item: (item.sort_order, item.id))
    seen_node_ids: set[int] = set()
    for relation in relations:
        node = relation.knowledge_node or db.query(KnowledgeNode).filter(KnowledgeNode.id == relation.knowledge_node_id).first()
        if not node:
            continue
        if node.id in seen_node_ids:
            continue
        seen_node_ids.add(node.id)
        mark_node_weak(db, student, node.node_name)


def _grade_submission(assignment: Assignment, question: AssignmentQuestion, code: str) -> tuple[str, list[dict], dict | None, str]:
    grading_mode = _normalize_grading_mode(question.grading_mode)
    if grading_mode == "observed_ai":
        observe_status, observe_results = run_java_submission(code, list(question.test_cases), observe_only=True)
        if observe_status != "accepted":
            ai_review = _run_ai_code_review(
                assignment,
                question,
                code,
                observe_results,
                "deep",
                True,
                True,
            )
            return observe_status, observe_results, ai_review, "observed_ai"
        ai_review = _run_ai_code_review(
            assignment,
            question,
            code,
            observe_results,
            "deep",
            True,
            True,
        )
        return _resolve_ai_only_status(question, ai_review), observe_results, ai_review, "observed_ai"

    if _question_enable_testcases(question):
        testcase_status, testcase_results = run_java_submission(code, list(question.test_cases))
        if testcase_status != "accepted":
            ai_review = _run_ai_code_review(
                assignment,
                question,
                code,
                testcase_results,
                _effective_ai_review_level(question),
                True,
                False,
            )
            return testcase_status, testcase_results, ai_review, "ai_with_testcases"
        ai_review = _run_ai_code_review(
            assignment,
            question,
            code,
            testcase_results,
            _effective_ai_review_level(question),
            True,
            False,
        )
        return _resolve_ai_with_testcases_status(question, ai_review), testcase_results, ai_review, "ai_with_testcases"

    compile_status, compile_results = run_java_submission(code, [])
    if compile_status != "accepted":
        ai_review = _run_ai_code_review(
            assignment,
            question,
            code,
            compile_results,
            _effective_ai_review_level(question),
            False,
            False,
        )
        return compile_status, compile_results, ai_review, "ai_only"
    ai_review = _run_ai_code_review(
        assignment,
        question,
        code,
        compile_results,
        _effective_ai_review_level(question),
        False,
        False,
    )
    return _resolve_ai_only_status(question, ai_review), compile_results, ai_review, "ai_only"


def _effective_ai_review_level(question: AssignmentQuestion) -> str:
    if not _question_enable_testcases(question):
        return "deep"
    return _question_ai_review_level(question)


def _run_ai_code_review(
    assignment: Assignment,
    question: AssignmentQuestion,
    code: str,
    execution_results: list[dict],
    review_level: str,
    enable_testcases: bool,
    observe_only: bool = False,
) -> dict:
    client = get_openai_client()
    prompt = _build_ai_review_prompt(
        assignment,
        question,
        code,
        execution_results,
        review_level,
        enable_testcases,
        observe_only,
    )
    fallback = {
        "decision": "ai_rejected",
        "summary": "AI 判题失败，按未通过处理。",
        "issues": ["AI 判题调用失败或返回格式异常。"],
        "strengths": [],
        "diagnoses": [],
    }
    try:
        response = client.chat.completions.create(
            model=settings.llm_model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        content = response.choices[0].message.content or ""
        parsed = _parse_json_object(content)
        return _normalize_ai_review_payload(parsed)
    except Exception:
        return fallback


def _run_ai_objective_review(assignment: Assignment, question: AssignmentQuestion, answer) -> dict:
    client = get_openai_client()
    prompt = f"""
你是一名 Java 课程客观题判分助手。请根据题目、标准答案和学生答案进行语义判分。

要求：
1. 只返回 JSON，不要解释。
2. decision 只能是 accepted 或 ai_rejected。
3. accepted 表示通过，ai_rejected 表示不通过。
4. 不确定时也返回 ai_rejected。
5. 输出 summary、issues、strengths、diagnoses 作为解释信息。

作业：{assignment.title}
题型：{_normalize_question_type(question.question_type)}
题目：{question.title}
题干：
{question.prompt}
选项：
{json.dumps(_normalize_options(question.options_json), ensure_ascii=False)}
标准答案：
{json.dumps(question.answer_json, ensure_ascii=False)}
解析：
{question.explanation or ""}
学生答案：
{json.dumps(answer, ensure_ascii=False)}

返回 JSON 格式：
{{
  "decision": "accepted",
  "summary": "简要说明",
  "issues": [],
  "strengths": [],
  "diagnoses": []
}}
"""
    fallback = _local_objective_review(question, answer)
    try:
        response = client.chat.completions.create(
            model=settings.llm_model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.15,
        )
        return _normalize_ai_review_payload(_parse_json_object(response.choices[0].message.content or ""))
    except Exception:
        return fallback


def _local_objective_review(question: AssignmentQuestion, answer) -> dict:
    expected = question.answer_json
    answer_text = json.dumps(answer, ensure_ascii=False, sort_keys=True) if isinstance(answer, (list, dict)) else str(answer or "").strip()
    expected_text = json.dumps(expected, ensure_ascii=False, sort_keys=True) if isinstance(expected, (list, dict)) else str(expected or "").strip()
    is_match = answer_text.lower().replace(" ", "") == expected_text.lower().replace(" ", "")
    return {
        "decision": "accepted" if is_match else "ai_rejected",
        "summary": "答案与标准答案一致。" if is_match else "答案与标准答案不一致。",
        "issues": [] if is_match else ["答案不匹配。"],
        "strengths": ["答案匹配。"] if is_match else [],
        "diagnoses": [],
    }


def _grade_multiple_choice_locally(question: AssignmentQuestion, answer) -> tuple[str, list[dict], dict, str]:
    expected = _normalize_answer(question.answer_json)
    normalized_answer = _normalize_answer(answer)
    accepted = _normalized_answer_text(normalized_answer) == _normalized_answer_text(expected)
    status_value = "accepted" if accepted else "wrong_answer"
    review = {
        "decision": "accepted" if accepted else "ai_rejected",
        "summary": "选择与标准答案一致。" if accepted else "选择与标准答案不一致。",
        "issues": [] if accepted else ["选择题答案错误。"],
        "strengths": ["答案匹配。"] if accepted else [],
        "diagnoses": [],
    }
    results = [
        {
            "case_index": 1,
            "status": status_value,
            "check_mode": "local_multiple_choice",
            "summary": review["summary"],
        }
    ]
    return status_value, results, review, "local_multiple_choice"


def _normalized_answer_text(value) -> str:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True).strip().lower().replace(" ", "")
    return str(value or "").strip().lower().replace(" ", "")


def _answer_is_empty(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return not value or all(_answer_is_empty(item) for item in value)
    if isinstance(value, dict):
        return not value or all(_answer_is_empty(item) for item in value.values())
    return False


def _build_ai_review_prompt(
    assignment: Assignment,
    question: AssignmentQuestion,
    code: str,
    execution_results: list[dict],
    review_level: str,
    enable_testcases: bool,
    observe_only: bool = False,
) -> str:
    review_level = _normalize_ai_review_level(review_level)
    rubric = question.ai_grading_rubric or "请重点判断实现是否满足题意、是否存在明显正确性风险、资源管理问题或教学目标偏差。"
    teacher_focus = _normalize_ai_focus(question.ai_grading_focus_json)
    inferred_focus = _infer_focus_from_prompt(question.prompt)
    merged_focus = _merge_focus(inferred_focus, teacher_focus)
    bound_knowledge_nodes = [
        relation.knowledge_node.node_name
        for relation in sorted(question.knowledge_nodes, key=lambda item: (item.sort_order, item.id))
        if relation.knowledge_node
    ]
    strategy_text = (
        "轻审查：不要主动苛责命名、架构或微优化，只检查题意满足、明显逻辑错误、危险实现与较大风险。"
        if review_level == "light"
        else "深审查：重点检查事务、线程安全、资源释放、边界处理、设计偏差、异常处理与明显性能风险。"
    )
    grading_mode_text = "观察运行 + AI 判题" if observe_only else "标准输出 + AI 复核" if enable_testcases else "仅 AI 判题"

    return f"""
你是一名严格但克制的 Java 编程作业评审助手。请根据教师给出的评分标准，对学生代码进行保守评审。

要求：
1. 只返回 JSON，不要输出任何解释性文字。
2. decision 只能是 accepted 或 ai_rejected。
3. accepted 表示通过，ai_rejected 表示不通过。
4. 未启用测试用例时，请主动从题意、边界、资源管理和潜在风险角度深入检查。
5. 观察运行模式下，运行输出不是固定答案，请结合代码、输出证据和评分标准判断是否满足题意。
6. 启用标准输出测试且当前为轻审查时，只指出明显问题，不要为了工程洁癖过度挑刺。
7. 不确定时返回 ai_rejected。
8. 必须输出 summary、issues、strengths、diagnoses，作为给教师和学生查看的解释信息。
9. diagnoses 用于描述学生可能薄弱的知识点，不参与系统薄弱点写入。
10. diagnoses 每项包含 knowledge_node、stage、category、evidence、reason、student_feedback。

作业标题：{assignment.title}
题目标题：{question.title or "未命名题目"}
题目描述：
{question.prompt}

是否启用测试用例：{"是" if enable_testcases else "否"}
判题方式：{grading_mode_text}
审查强度：{review_level}
审查策略：
{strategy_text}

教师评分标准：
{rubric}

综合关注点（系统推断 + 教师指定）：
{json.dumps(merged_focus, ensure_ascii=False)}

题目绑定知识点：
{json.dumps(bound_knowledge_nodes, ensure_ascii=False)}
测试/编译结果摘要：
{json.dumps(execution_results or [], ensure_ascii=False)}

学生代码：
```java
{code}
```

返回 JSON 格式：
{{
  "decision": "accepted",
  "summary": "简要总结",
  "issues": ["问题1"],
  "strengths": ["优点1"],
  "diagnoses": [
    {{
      "knowledge_node": "Runnable接口",
      "stage": "compile",
      "category": "api_misuse",
      "evidence": "cannot find symbol: method start()",
      "reason": "学生把 Runnable 当作 Thread 使用。",
      "student_feedback": "Runnable 表示任务，不能直接 start，需要交给 Thread 执行。"
    }}
  ]
}}
"""


def _normalize_ai_review_payload(data: dict) -> dict:
    decision = str(data.get("decision") or "ai_rejected").strip()
    if decision not in {"accepted", "ai_rejected"}:
        decision = "ai_rejected"
    issues = data.get("issues")
    strengths = data.get("strengths")
    diagnoses = data.get("diagnoses")
    summary = str(data.get("summary") or ("AI 判定通过。" if decision == "accepted" else "AI 判定未通过。")).strip()
    return {
        "decision": decision,
        "summary": summary,
        "issues": [str(item).strip() for item in (issues if isinstance(issues, list) else []) if str(item).strip()],
        "strengths": [str(item).strip() for item in (strengths if isinstance(strengths, list) else []) if str(item).strip()],
        "diagnoses": _normalize_ai_diagnoses(diagnoses),
    }


def _normalize_ai_diagnoses(diagnoses) -> list[dict]:
    if not isinstance(diagnoses, list):
        return []
    normalized = []
    for item in diagnoses:
        if not isinstance(item, dict):
            continue
        diagnosis = {
            "knowledge_node": str(item.get("knowledge_node") or "unknown").strip() or "unknown",
            "stage": str(item.get("stage") or "").strip(),
            "category": str(item.get("category") or "").strip(),
            "evidence": str(item.get("evidence") or "").strip(),
            "reason": str(item.get("reason") or "").strip(),
            "student_feedback": str(item.get("student_feedback") or "").strip(),
        }
        if diagnosis["knowledge_node"] or diagnosis["reason"] or diagnosis["student_feedback"]:
            normalized.append(diagnosis)
    return normalized


def _infer_focus_from_prompt(prompt: str) -> list[str]:
    text = (prompt or "").lower()
    inferred: list[str] = []
    keyword_groups = [
        (["sql", "数据库", "jdbc", "事务", "隔离级别"], ["SQL 正确性", "事务边界", "资源释放"]),
        (["线程", "并发", "锁", "synchronized", "thread"], ["线程安全", "竞态条件", "锁使用"]),
        (["文件", "io", "输入输出流", "stream"], ["资源关闭", "异常处理"]),
        (["边界", "异常", "非法输入"], ["边界条件", "异常处理"]),
    ]
    for keywords, focuses in keyword_groups:
        if any(keyword in text for keyword in keywords):
            inferred.extend(focuses)
    if not inferred:
        inferred.extend(["题意满足", "边界条件", "明显逻辑错误"])
    return _merge_focus(inferred, [])


def _merge_focus(auto_focus: list[str], teacher_focus: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for item in [*auto_focus, *teacher_focus]:
        value = str(item).strip()
        if value and value not in seen:
            seen.add(value)
            merged.append(value)
    return merged


def _resolve_ai_only_status(question: AssignmentQuestion, ai_review: dict) -> str:
    if not isinstance(ai_review, dict):
        return "ai_rejected"
    return "accepted" if ai_review.get("decision") == "accepted" else "ai_rejected"


def _resolve_ai_with_testcases_status(question: AssignmentQuestion, ai_review: dict) -> str:
    if not isinstance(ai_review, dict):
        return "accepted"
    return "accepted" if ai_review.get("decision") == "accepted" else "ai_rejected"


def _parse_json_array(content: str) -> list:
    start = content.find("[")
    end = content.rfind("]") + 1
    if start == -1 or end <= start:
        raise ValueError("大模型未返回 JSON 数组。")
    data = json.loads(content[start:end])
    if not isinstance(data, list):
        raise ValueError("返回结果不是 JSON 数组。")
    return data
