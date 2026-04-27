from datetime import datetime

from sqlalchemy.orm import Session

from backend.models.assignment import (
    Assignment,
    AssignmentQuestion,
    AssignmentQuestionKnowledgeNode,
    AssignmentSubmission,
)
from backend.models.knowledge import KnowledgeNode
from backend.models.knowledge_state import UserConceptMastery
from backend.models.user import User
from backend.schemas.teacher import (
    PortraitConceptResponse,
    PortraitSummaryResponse,
    PortraitTrendResponse,
)

_MAX_EVIDENCE = 12


def generate_student_portrait(db: Session, student_id: int) -> PortraitSummaryResponse:
    student = db.query(User).filter(User.id == student_id, User.role == "student").first()
    if not student:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    masteries = (
        db.query(UserConceptMastery, KnowledgeNode)
        .join(KnowledgeNode, UserConceptMastery.knowledge_node_id == KnowledgeNode.id)
        .filter(UserConceptMastery.student_id == student_id)
        .order_by(UserConceptMastery.mastery_score.asc())
        .all()
    )

    all_submissions = (
        db.query(AssignmentSubmission)
        .filter(AssignmentSubmission.student_id == student_id)
        .order_by(AssignmentSubmission.submitted_at.asc())
        .all()
    )

    concepts: list[PortraitConceptResponse] = []
    total_weak = 0
    total_gap = 0
    total_slip = 0
    improving_count = 0
    stable_count = 0
    declining_count = 0

    for mastery, node in masteries:
        node_submissions = [
            s for s in all_submissions
            if _submission_touches_node(s, node.id, node.node_name)
        ]
        trend = _compute_concept_trend(mastery, node_submissions)
        error_type = _classify_error_type(mastery, node_submissions)

        if mastery.status == "weak":
            total_weak += 1
            if error_type == "gap":
                total_gap += 1
            elif error_type == "slip":
                total_slip += 1

        if trend == "improving":
            improving_count += 1
        elif trend == "declining":
            declining_count += 1
        else:
            stable_count += 1

        concepts.append(
            PortraitConceptResponse(
                knowledge_node_id=node.id,
                node_name=node.node_name,
                mastery_score=int(mastery.mastery_score or 50),
                status=mastery.status,
                positive_evidence_count=int(mastery.positive_evidence_count or 0),
                negative_evidence_count=int(mastery.negative_evidence_count or 0),
                last_evaluated_at=mastery.last_evaluated_at,
                trend=trend,
                error_type=error_type,
                recent_scores=_recent_score_timeline(node_submissions),
            )
        )

    concepts.sort(key=lambda c: (c.mastery_score, -(c.positive_evidence_count + c.negative_evidence_count)))

    if concepts:
        weakest = concepts[0]
        strongest = concepts[-1]
        recommendation = _generate_recommendation(weakest, concepts)
    else:
        weakest = None
        strongest = None
        recommendation = "该学生尚无足够的作业数据，建议先完成已发布的作业。"
        concepts = []
        total_weak = 0
        total_gap = 0
        total_slip = 0
        improving_count = 0
        stable_count = 0
        declining_count = 0

    return PortraitSummaryResponse(
        student_id=student_id,
        student_name=student.username,
        total_concepts=len(concepts),
        weak_count=total_weak,
        gap_count=total_gap,
        slip_count=total_slip,
        improving_count=improving_count,
        stable_count=stable_count,
        declining_count=declining_count,
        strongest_concept=strongest.node_name if strongest else None,
        weakest_concept=weakest.node_name if weakest else None,
        recommendation=recommendation,
        concepts=concepts,
    )


def _submission_touches_node(submission: AssignmentSubmission, node_id: int, node_name: str) -> bool:
    question = submission.question
    if question and any(
        rel.knowledge_node_id == node_id
        for rel in (question.knowledge_nodes or [])
    ):
        return True
    ai_review = submission.ai_review_json if isinstance(submission.ai_review_json, dict) else {}
    diagnoses = ai_review.get("diagnoses")
    if not isinstance(diagnoses, list):
        return False
    return any(
        _diagnosis_matches(d, node_id, node_name)
        for d in diagnoses
    )


def _diagnosis_matches(diagnosis: dict, node_id: int, node_name: str) -> bool:
    resolution = diagnosis.get("graph_resolution") if isinstance(diagnosis.get("graph_resolution"), dict) else {}
    if int(resolution.get("node_id") or 0) == node_id:
        return True
    if str(resolution.get("node_name") or "").strip() == node_name:
        return True
    return str(diagnosis.get("knowledge_node") or "").strip() == node_name


def _compute_concept_trend(mastery: UserConceptMastery, submissions: list[AssignmentSubmission]) -> str:
    if not submissions or len(submissions) < 2:
        return "stable"
    recent = submissions[-min(5, len(submissions)):]
    scores = [_submission_effective_score(s) for s in recent]
    if len(scores) < 2:
        return "stable"
    first_half = sum(scores[:len(scores)//2]) / (len(scores)//2)
    second_half = sum(scores[len(scores)//2:]) / (len(scores) - len(scores)//2)
    if second_half - first_half > 10:
        return "improving"
    if first_half - second_half > 10:
        return "declining"
    return "stable"


def _submission_effective_score(submission: AssignmentSubmission) -> float:
    if submission.status == "accepted":
        ai_review = submission.ai_review_json if isinstance(submission.ai_review_json, dict) else {}
        score = ai_review.get("score", 80) if isinstance(ai_review, dict) else 80
        return float(score or 80)
    return 30.0


def _classify_error_type(mastery: UserConceptMastery, submissions: list[AssignmentSubmission]) -> str:
    failed = [s for s in submissions if s.status != "accepted"]
    passed = [s for s in submissions if s.status == "accepted"]
    if not failed:
        return "none"
    if len(failed) == 1 and len(passed) >= 2 and submissions[-1].status == "accepted":
        return "slip"
    if len(failed) >= 3 or (len(failed) >= 2 and submissions[-1].status != "accepted" and submissions[-2].status != "accepted"):
        return "gap"
    pass_rate = len(passed) / len(submissions) if submissions else 0
    if pass_rate < 0.5 and len(submissions) >= 3:
        return "gap"
    if pass_rate >= 0.5:
        return "slip"
    return "gap"


def _recent_score_timeline(submissions: list[AssignmentSubmission]) -> list[PortraitTrendResponse]:
    recent = submissions[-min(_MAX_EVIDENCE, len(submissions)):]
    return [
        PortraitTrendResponse(
            submission_id=s.id,
            status=s.status,
            score=_submission_effective_score(s),
            submitted_at=s.submitted_at,
        )
        for s in recent
    ]


def _generate_recommendation(weakest: PortraitConceptResponse, concepts: list[PortraitConceptResponse]) -> str:
    weak_concepts = [c for c in concepts if c.status == "weak"]
    gap_concepts = [c for c in weak_concepts if c.error_type == "gap"]
    parts: list[str] = []
    if gap_concepts:
        names = "、".join(c.node_name for c in gap_concepts[:3])
        parts.append(f"建议重点强化以下根本性薄弱知识点：{names}")
    elif weak_concepts:
        names = "、".join(c.node_name for c in weak_concepts[:3])
        parts.append(f"以下知识点掌握较弱，建议针对性练习：{names}")
    improving = [c for c in concepts if c.trend == "improving" and c.status != "good"]
    if improving:
        parts.append(f"以下知识点呈上升趋势，继续保持：{'、'.join(c.node_name for c in improving[:2])}")
    declining = [c for c in concepts if c.trend == "declining"]
    if declining:
        parts.append(f"以下知识点有退步迹象，需要关注：{'、'.join(c.node_name for c in declining[:2])}")
    if not parts:
        parts.append("当前学习状态良好，建议按教师发布的作业持续练习。")
    return "。".join(parts) + "。"


def generate_student_portrait_summary(db: Session, student_id: int) -> dict:
    portrait = generate_student_portrait(db, student_id)
    return {
        "student_id": portrait.student_id,
        "student_name": portrait.student_name,
        "total_concepts": portrait.total_concepts,
        "weak_count": portrait.weak_count,
        "gap_count": portrait.gap_count,
        "slip_count": portrait.slip_count,
        "trend_summary": {
            "improving": portrait.improving_count,
            "stable": portrait.stable_count,
            "declining": portrait.declining_count,
        },
        "weakest_concept": portrait.weakest_concept,
        "recommendation": portrait.recommendation,
    }
