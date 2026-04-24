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
    AssignmentQuestionKnowledgeNode,
    AssignmentSubmission,
    AssignmentTestCase,
)
from backend.models.knowledge import KnowledgeNode
from backend.models.knowledge_state import UserConceptMastery
from backend.models.user import User
from backend.schemas.assignment import (
    AssignmentAiHelpRequest,
    AssignmentAiHelpResponse,
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
from backend.services.knowledge_progress_service import get_or_create_knowledge_node, mark_node_mastered, mark_node_weak
from backend.services.sandbox_service import run_java_submission


VALID_ASSIGNMENT_STATUSES = {"draft", "published", "closed"}
VALID_GRADING_MODES = {"testcase", "ai_review", "hybrid", "observed_ai"}
VALID_AI_REVIEW_LEVELS = {"light", "deep"}
VALID_REVIEW_STATUSES = {"accepted", "ai_rejected", "needs_manual_review"}
DEFAULT_AI_GRADING_PASS_THRESHOLD = 85
DEFAULT_AI_GRADING_CONFIDENCE_THRESHOLD = 0.85
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


def generate_assignment_question(db: Session, payload: AssignmentGenerateQuestionRequest) -> AssignmentGeneratedQuestionResponse:
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
        title = data.get("title") or "Java 编程题"
        prompt_text = data.get("prompt") or payload.requirement
        knowledge_nodes = _recommend_assignment_knowledge_nodes(db, title, prompt_text, payload)
        return AssignmentGeneratedQuestionResponse(
            title=title,
            prompt=prompt_text,
            language="java",
            test_cases=test_cases,
            knowledge_node_ids=[item["id"] for item in knowledge_nodes],
            knowledge_nodes=knowledge_nodes,
        )
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"生成题目失败：{error}",
        ) from error


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
    if _normalize_grading_mode(question.grading_mode) in {"testcase", "hybrid"} and not question.test_cases:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该题目尚未配置测试用例。")

    started_at = _to_naive_local(started_at)
    submitted_at = datetime.now()
    duration_seconds = _duration_seconds(started_at, submitted_at)
    status_value, results, ai_review, decision_source = _grade_submission(assignment, question, code)
    trust_label, trust_score, excluded_from_mastery_update = _resolve_submission_trust(status_value, duration_seconds)
    submission = AssignmentSubmission(
        assignment_id=assignment.id,
        question_id=question.id,
        student_id=student.id,
        code=code,
        status=status_value,
        results_json=results,
        ai_review_json=ai_review,
        final_decision_source=decision_source,
        teacher_review_status="pending" if status_value == "needs_manual_review" else None,
        trust_label=trust_label,
        trust_score=trust_score,
        excluded_from_mastery_update=excluded_from_mastery_update,
        started_at=started_at,
        duration_seconds=duration_seconds,
        submitted_at=submitted_at,
    )
    db.add(submission)
    db.flush()
    _apply_submission_mastery_evidence(db, student, question, submission)
    db.commit()
    db.refresh(submission)
    return AssignmentRunResultResponse(
        submission=_submission_to_response(submission),
        status=status_value,
        results=results,
        ai_review=ai_review,
        decision_source=decision_source,
        manual_review_required=status_value == "needs_manual_review" or bool((ai_review or {}).get("manual_review_required")),
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
    return [_submission_to_response(item) for item in submissions]


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
        ai_review_json=submission.ai_review_json,
        decision_source=submission.final_decision_source,
        manual_review_required=_submission_requires_manual_review(submission),
        teacher_review_status=submission.teacher_review_status,
        teacher_review_note=submission.teacher_review_note,
        trust_label=submission.trust_label,
        trust_score=submission.trust_score,
        excluded_from_mastery_update=bool(submission.excluded_from_mastery_update),
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="人工复核状态非法。")

    submission.status = payload.status
    submission.final_decision_source = "teacher_override"
    submission.teacher_review_status = "approved" if payload.status == "accepted" else "rejected"
    submission.teacher_review_note = payload.note.strip() or None
    submission.reviewed_at = datetime.now()
    submission.reviewed_by = teacher.id
    db.commit()
    db.refresh(submission)
    return get_teacher_submission_detail(db, teacher, assignment_id, submission_id)


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


def _sync_questions(db: Session, assignment: Assignment, payload_questions: list[AssignmentQuestionInput]) -> None:
    existing = {question.id: question for question in assignment.questions}
    keep_ids: set[int] = set()

    for index, item in enumerate(payload_questions):
        if item.language != "java":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前仅支持 Java 题目。")
        ai_review_level = _normalize_ai_review_level(item.ai_review_level)
        grading_mode = _resolve_grading_mode(item)
        sort_order = item.sort_order if item.sort_order is not None else index
        if item.id and item.id in existing:
            question = existing[item.id]
            keep_ids.add(question.id)
            question.title = item.title
            question.prompt = item.prompt
            question.starter_code = item.starter_code or ""
            question.language = "java"
            question.grading_mode = grading_mode
            question.ai_grading_rubric = (item.ai_grading_rubric or "").strip()
            question.ai_grading_focus_json = _normalize_ai_focus(item.ai_grading_focus)
            question.ai_grading_pass_threshold = item.ai_grading_pass_threshold
            question.ai_grading_confidence_threshold = item.ai_grading_confidence_threshold
            question.sort_order = sort_order
        else:
            question = AssignmentQuestion(
                assignment=assignment,
                title=item.title,
                prompt=item.prompt,
                starter_code=item.starter_code or "",
                language="java",
                grading_mode=grading_mode,
                ai_grading_rubric=(item.ai_grading_rubric or "").strip(),
                ai_grading_focus_json=_normalize_ai_focus(item.ai_grading_focus),
                ai_grading_pass_threshold=item.ai_grading_pass_threshold,
                ai_grading_confidence_threshold=item.ai_grading_confidence_threshold,
                sort_order=sort_order,
            )
            db.add(question)
            db.flush()
            keep_ids.add(question.id)
        _sync_test_cases(db, question, item.test_cases)
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
                    "starter_code": question.starter_code or "",
                    "knowledge_node_ids": [item["id"] for item in knowledge_nodes],
                    "knowledge_nodes": knowledge_nodes,
                    "language": question.language,
                    "grading_mode": _normalize_grading_mode(question.grading_mode),
                    "enable_testcases": _question_enable_testcases(question),
                    "ai_review_level": _question_ai_review_level(question),
                    "ai_grading_rubric": question.ai_grading_rubric or "",
                    "ai_grading_focus": _normalize_ai_focus(question.ai_grading_focus_json),
                    "ai_grading_pass_threshold": (
                        question.ai_grading_pass_threshold
                        if question.ai_grading_pass_threshold is not None
                        else DEFAULT_AI_GRADING_PASS_THRESHOLD
                    ),
                    "ai_grading_confidence_threshold": float(
                        question.ai_grading_confidence_threshold
                        if question.ai_grading_confidence_threshold is not None
                        else DEFAULT_AI_GRADING_CONFIDENCE_THRESHOLD
                    ),
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
        submissions=[_submission_to_response(item) for item in submissions],
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


def _normalize_grading_mode(value: str | None) -> str:
    value = (value or "testcase").strip().lower()
    if value not in VALID_GRADING_MODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="判题模式必须是 testcase、observed_ai、ai_review 或 hybrid。",
        )
    return value


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


def _submission_requires_manual_review(submission: AssignmentSubmission) -> bool:
    if submission.final_decision_source == "teacher_override":
        return submission.status == "needs_manual_review"
    ai_review = submission.ai_review_json if isinstance(submission.ai_review_json, dict) else {}
    return submission.status == "needs_manual_review" or bool(ai_review.get("manual_review_required"))


def _submission_to_response(submission: AssignmentSubmission) -> AssignmentSubmissionResponse:
    return AssignmentSubmissionResponse(
        id=submission.id,
        assignment_id=submission.assignment_id,
        question_id=submission.question_id,
        student_id=submission.student_id,
        code=submission.code,
        status=submission.status,
        results_json=submission.results_json,
        ai_review_json=submission.ai_review_json,
        decision_source=submission.final_decision_source,
        manual_review_required=_submission_requires_manual_review(submission),
        teacher_review_status=submission.teacher_review_status,
        teacher_review_note=submission.teacher_review_note,
        trust_label=submission.trust_label,
        trust_score=submission.trust_score,
        excluded_from_mastery_update=bool(submission.excluded_from_mastery_update),
        started_at=submission.started_at,
        duration_seconds=submission.duration_seconds,
        submitted_at=submission.submitted_at,
    )


def _resolve_submission_trust(status_value: str, duration_seconds: int | None) -> tuple[str, float, bool]:
    if duration_seconds is not None and duration_seconds <= FAST_PASS_THRESHOLD_SECONDS and status_value == "accepted":
        return "suspicious_fast_pass", 0.0, True
    return "normal", 1.0, False


def _apply_submission_mastery_evidence(
    db: Session,
    student: User,
    question: AssignmentQuestion,
    submission: AssignmentSubmission,
) -> None:
    if submission.excluded_from_mastery_update:
        return
    relations = sorted(question.knowledge_nodes, key=lambda item: (item.sort_order, item.id))
    if not relations:
        return

    delta = 5 if submission.status == "accepted" else -3
    positive = 1 if submission.status == "accepted" else 0
    negative = 0 if submission.status == "accepted" else 1
    for relation in relations:
        node = relation.knowledge_node or db.query(KnowledgeNode).filter(KnowledgeNode.id == relation.knowledge_node_id).first()
        if not node:
            continue
        mastery = _get_or_create_user_concept_mastery(db, student.id, node.id)
        mastery.mastery_score = max(0, min(100, int(mastery.mastery_score or 50) + delta))
        mastery.positive_evidence_count = int(mastery.positive_evidence_count or 0) + positive
        mastery.negative_evidence_count = int(mastery.negative_evidence_count or 0) + negative
        mastery.status = _mastery_status_for_score(mastery.mastery_score)
        mastery.last_source_submission_id = submission.id
        _sync_legacy_knowledge_status(db, student, node.node_name, mastery.status)


def _get_or_create_user_concept_mastery(db: Session, student_id: int, knowledge_node_id: int) -> UserConceptMastery:
    mastery = (
        db.query(UserConceptMastery)
        .filter(
            UserConceptMastery.student_id == student_id,
            UserConceptMastery.knowledge_node_id == knowledge_node_id,
        )
        .first()
    )
    if mastery:
        return mastery
    mastery = UserConceptMastery(
        student_id=student_id,
        knowledge_node_id=knowledge_node_id,
        mastery_score=50,
        positive_evidence_count=0,
        negative_evidence_count=0,
        status="partial",
    )
    db.add(mastery)
    db.flush()
    return mastery


def _mastery_status_for_score(score: int) -> str:
    if score <= 39:
        return "weak"
    if score <= 69:
        return "partial"
    return "good"


def _sync_legacy_knowledge_status(db: Session, student: User, node_name: str, mastery_status: str) -> None:
    if mastery_status == "weak":
        mark_node_weak(db, student, node_name)
    elif mastery_status == "good":
        mark_node_mastered(db, student, node_name)
    else:
        get_or_create_knowledge_node(db, node_name)


def _grade_submission(assignment: Assignment, question: AssignmentQuestion, code: str) -> tuple[str, list[dict], dict | None, str]:
    grading_mode = _normalize_grading_mode(question.grading_mode)
    if grading_mode == "observed_ai":
        observe_status, observe_results = run_java_submission(code, list(question.test_cases), observe_only=True)
        if observe_status != "accepted":
            return observe_status, observe_results, None, "observed_ai"
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
            return testcase_status, testcase_results, None, "ai_with_testcases"
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
        return compile_status, compile_results, None, "ai_only"
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
        "decision": "needs_manual_review",
        "score": 0,
        "confidence": 0,
        "summary": "AI 判题暂时不可用，建议教师人工复核。",
        "issues": ["AI 判题调用失败或返回格式异常。"],
        "strengths": [],
        "manual_review_required": True,
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
    except Exception as error:
        fallback["summary"] = f"AI 判题失败：{error}"
        return fallback


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
2. decision 只能是 accepted、ai_rejected、needs_manual_review 三者之一。
3. 只有在你高置信度确认实现合理时，才允许 decision=accepted。
4. 未启用测试用例时，请主动从题意、边界、资源管理和潜在风险角度深入检查。
5. 观察运行模式下，运行输出不是固定答案，请结合代码、输出证据和评分标准判断是否满足题意。
6. 启用标准输出测试且当前为轻审查时，只指出明显问题，不要为了工程洁癖过度挑刺。
7. score 为 0 到 100 的整数；confidence 为 0 到 1 的小数。
8. issues 和 strengths 必须是字符串数组。
9. manual_review_required 为布尔值。

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

测试/编译结果摘要：
{json.dumps(execution_results or [], ensure_ascii=False)}

学生代码：
```java
{code}
```

返回 JSON 格式：
{{
  "decision": "accepted",
  "score": 92,
  "confidence": 0.93,
  "summary": "简要总结",
  "issues": ["问题1"],
  "strengths": ["优点1"],
  "manual_review_required": false
}}
"""


def _normalize_ai_review_payload(data: dict) -> dict:
    decision = str(data.get("decision") or "needs_manual_review").strip()
    if decision not in {"accepted", "ai_rejected", "needs_manual_review"}:
        decision = "needs_manual_review"
    issues = data.get("issues")
    strengths = data.get("strengths")
    score = int(data.get("score", 0) or 0)
    confidence = float(data.get("confidence", 0) or 0)
    summary = str(data.get("summary") or "AI 未返回有效总结。").strip()
    manual_review_required = bool(data.get("manual_review_required", decision != "accepted"))
    score = max(0, min(score, 100))
    confidence = max(0.0, min(confidence, 1.0))
    normalized = {
        "decision": decision,
        "score": score,
        "confidence": confidence,
        "summary": summary,
        "issues": [str(item).strip() for item in (issues if isinstance(issues, list) else []) if str(item).strip()],
        "strengths": [str(item).strip() for item in (strengths if isinstance(strengths, list) else []) if str(item).strip()],
        "manual_review_required": manual_review_required,
    }
    if not normalized["issues"] and decision != "accepted":
        normalized["issues"] = ["AI 无法高置信度确认该实现满足要求。"]
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
        return "needs_manual_review"
    score = int(ai_review.get("score", 0) or 0)
    confidence = float(ai_review.get("confidence", 0) or 0)
    decision = ai_review.get("decision")
    manual_review_required = bool(ai_review.get("manual_review_required"))
    pass_threshold = int(
        question.ai_grading_pass_threshold
        if question.ai_grading_pass_threshold is not None
        else DEFAULT_AI_GRADING_PASS_THRESHOLD
    )
    confidence_threshold = float(
        question.ai_grading_confidence_threshold
        if question.ai_grading_confidence_threshold is not None
        else DEFAULT_AI_GRADING_CONFIDENCE_THRESHOLD
    )
    if (
        decision == "accepted"
        and score >= pass_threshold
        and confidence >= confidence_threshold
        and not manual_review_required
    ):
        return "accepted"
    if decision == "ai_rejected" and not manual_review_required:
        return "ai_rejected"
    return "needs_manual_review"


def _resolve_hybrid_status(question: AssignmentQuestion, ai_review: dict) -> str:
    if not isinstance(ai_review, dict):
        return "needs_manual_review"
    score = int(ai_review.get("score", 0) or 0)
    confidence = float(ai_review.get("confidence", 0) or 0)
    decision = ai_review.get("decision")
    manual_review_required = bool(ai_review.get("manual_review_required"))
    pass_threshold = int(
        question.ai_grading_pass_threshold
        if question.ai_grading_pass_threshold is not None
        else DEFAULT_AI_GRADING_PASS_THRESHOLD
    )
    confidence_threshold = float(
        question.ai_grading_confidence_threshold
        if question.ai_grading_confidence_threshold is not None
        else DEFAULT_AI_GRADING_CONFIDENCE_THRESHOLD
    )
    if (
        decision == "accepted"
        and score >= pass_threshold
        and confidence >= confidence_threshold
        and not manual_review_required
    ):
        return "accepted"
    if decision == "ai_rejected" and not manual_review_required:
        return "ai_rejected"
    return "needs_manual_review"


def _resolve_ai_with_testcases_status(question: AssignmentQuestion, ai_review: dict) -> str:
    if not isinstance(ai_review, dict):
        return "accepted"
    score = int(ai_review.get("score", 0) or 0)
    confidence = float(ai_review.get("confidence", 0) or 0)
    decision = ai_review.get("decision")
    manual_review_required = bool(ai_review.get("manual_review_required"))
    pass_threshold = int(
        question.ai_grading_pass_threshold
        if question.ai_grading_pass_threshold is not None
        else DEFAULT_AI_GRADING_PASS_THRESHOLD
    )
    confidence_threshold = float(
        question.ai_grading_confidence_threshold
        if question.ai_grading_confidence_threshold is not None
        else DEFAULT_AI_GRADING_CONFIDENCE_THRESHOLD
    )
    if decision == "ai_rejected" and not manual_review_required:
        return "ai_rejected"
    if decision == "accepted" and score >= max(60, pass_threshold - 10) and confidence >= max(0.6, confidence_threshold - 0.2):
        return "accepted"
    return "needs_manual_review" if manual_review_required else "accepted"


def _parse_json_array(content: str) -> list:
    start = content.find("[")
    end = content.rfind("]") + 1
    if start == -1 or end <= start:
        raise ValueError("大模型未返回 JSON 数组。")
    data = json.loads(content[start:end])
    if not isinstance(data, list):
        raise ValueError("返回结果不是 JSON 数组。")
    return data
