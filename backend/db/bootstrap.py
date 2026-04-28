from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.security import get_password_hash
from backend.models.user import User


def ensure_schema_and_seed(engine: Engine) -> None:
    _ensure_user_role_column(engine)
    _ensure_user_class_column(engine)
    _ensure_knowledge_node_columns(engine)
    _ensure_assignment_submission_timing_columns(engine)
    _ensure_assignment_grading_columns(engine)
    _ensure_assignment_type_and_bank_columns(engine)
    _ensure_assignment_graph_linkage(engine)
    _ensure_teacher_seed(engine)
    _ensure_student_class_seed(engine)


def _ensure_user_role_column(engine: Engine) -> None:
    inspector = inspect(engine)
    try:
        columns = {column["name"] for column in inspector.get_columns("users")}
    except Exception:
        return

    if "role" in columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(32) NOT NULL DEFAULT 'student'"))
        connection.execute(text("CREATE INDEX ix_users_role ON users (role)"))


def _ensure_user_class_column(engine: Engine) -> None:
    inspector = inspect(engine)
    try:
        columns = {column["name"] for column in inspector.get_columns("users")}
    except Exception:
        return
    with engine.begin() as connection:
        if "class_name" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN class_name VARCHAR(64) NULL"))
            connection.execute(text("CREATE INDEX ix_users_class_name ON users (class_name)"))
        connection.execute(text("UPDATE users SET class_name = '软件1班' WHERE role = 'student' AND (class_name IS NULL OR class_name = '')"))


def _ensure_knowledge_node_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    try:
        table_names = set(inspector.get_table_names())
        if "knowledge_nodes" not in table_names:
            return
        columns = {column["name"] for column in inspector.get_columns("knowledge_nodes")}
    except Exception:
        return

    with engine.begin() as connection:
        if "chapter" not in columns:
            connection.execute(text("ALTER TABLE knowledge_nodes ADD COLUMN chapter VARCHAR(64) NULL"))


def _ensure_assignment_submission_timing_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    try:
        table_names = set(inspector.get_table_names())
        if "assignment_submissions" not in table_names:
            return
        columns = {column["name"] for column in inspector.get_columns("assignment_submissions")}
    except Exception:
        return

    with engine.begin() as connection:
        if "started_at" not in columns:
            connection.execute(text("ALTER TABLE assignment_submissions ADD COLUMN started_at DATETIME NULL"))
        if "duration_seconds" not in columns:
            connection.execute(text("ALTER TABLE assignment_submissions ADD COLUMN duration_seconds INT NULL"))


def _ensure_assignment_grading_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    try:
        table_names = set(inspector.get_table_names())
        question_columns = {column["name"] for column in inspector.get_columns("assignment_questions")} if "assignment_questions" in table_names else set()
        submission_columns = {column["name"] for column in inspector.get_columns("assignment_submissions")} if "assignment_submissions" in table_names else set()
    except Exception:
        return

    with engine.begin() as connection:
        if "assignment_questions" in table_names:
            if "starter_code" not in question_columns:
                connection.execute(text("ALTER TABLE assignment_questions ADD COLUMN starter_code TEXT NULL"))
            if "grading_mode" not in question_columns:
                connection.execute(text("ALTER TABLE assignment_questions ADD COLUMN grading_mode VARCHAR(32) NOT NULL DEFAULT 'testcase'"))
            if "ai_grading_rubric" not in question_columns:
                connection.execute(text("ALTER TABLE assignment_questions ADD COLUMN ai_grading_rubric TEXT NULL"))
            if "ai_grading_focus_json" not in question_columns:
                connection.execute(text("ALTER TABLE assignment_questions ADD COLUMN ai_grading_focus_json JSON NULL"))
            if "ai_grading_pass_threshold" not in question_columns:
                connection.execute(text("ALTER TABLE assignment_questions ADD COLUMN ai_grading_pass_threshold INT NOT NULL DEFAULT 85"))
            if "ai_grading_confidence_threshold" not in question_columns:
                connection.execute(text("ALTER TABLE assignment_questions ADD COLUMN ai_grading_confidence_threshold FLOAT NOT NULL DEFAULT 0.85"))

        if "assignment_submissions" in table_names:
            if "ai_review_json" not in submission_columns:
                connection.execute(text("ALTER TABLE assignment_submissions ADD COLUMN ai_review_json JSON NULL"))
            if "final_decision_source" not in submission_columns:
                connection.execute(text("ALTER TABLE assignment_submissions ADD COLUMN final_decision_source VARCHAR(32) NULL"))
            if "teacher_review_status" not in submission_columns:
                connection.execute(text("ALTER TABLE assignment_submissions ADD COLUMN teacher_review_status VARCHAR(32) NULL"))
            if "teacher_review_note" not in submission_columns:
                connection.execute(text("ALTER TABLE assignment_submissions ADD COLUMN teacher_review_note TEXT NULL"))
            if "reviewed_at" not in submission_columns:
                connection.execute(text("ALTER TABLE assignment_submissions ADD COLUMN reviewed_at DATETIME NULL"))
            if "reviewed_by" not in submission_columns:
                connection.execute(text("ALTER TABLE assignment_submissions ADD COLUMN reviewed_by INT NULL"))


def _ensure_assignment_type_and_bank_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    try:
        table_names = set(inspector.get_table_names())
        assignment_columns = {column["name"] for column in inspector.get_columns("assignments")} if "assignments" in table_names else set()
        question_columns = {column["name"] for column in inspector.get_columns("assignment_questions")} if "assignment_questions" in table_names else set()
        submission_columns = {column["name"] for column in inspector.get_columns("assignment_submissions")} if "assignment_submissions" in table_names else set()
    except Exception:
        return

    with engine.begin() as connection:
        if "assignments" in table_names and "starts_at" not in assignment_columns:
            connection.execute(text("ALTER TABLE assignments ADD COLUMN starts_at DATETIME NULL"))
        if "assignment_questions" in table_names:
            if "question_type" not in question_columns:
                connection.execute(text("ALTER TABLE assignment_questions ADD COLUMN question_type VARCHAR(32) NOT NULL DEFAULT 'programming'"))
                connection.execute(text("CREATE INDEX ix_assignment_questions_question_type ON assignment_questions (question_type)"))
            if "options_json" not in question_columns:
                connection.execute(text("ALTER TABLE assignment_questions ADD COLUMN options_json JSON NULL"))
            if "answer_json" not in question_columns:
                connection.execute(text("ALTER TABLE assignment_questions ADD COLUMN answer_json JSON NULL"))
            if "explanation" not in question_columns:
                connection.execute(text("ALTER TABLE assignment_questions ADD COLUMN explanation TEXT NULL"))
        if "assignment_submissions" in table_names and "answer_json" not in submission_columns:
            connection.execute(text("ALTER TABLE assignment_submissions ADD COLUMN answer_json JSON NULL"))
        if "question_bank_items" not in table_names:
            connection.execute(
                text(
                    """
                    CREATE TABLE question_bank_items (
                        id INTEGER PRIMARY KEY,
                        teacher_id INTEGER NOT NULL,
                        title VARCHAR(255) NOT NULL DEFAULT '',
                        prompt TEXT NOT NULL,
                        question_type VARCHAR(32) NOT NULL DEFAULT 'programming',
                        options_json JSON NULL,
                        answer_json JSON NULL,
                        explanation TEXT NULL,
                        starter_code TEXT NULL,
                        language VARCHAR(32) NOT NULL DEFAULT 'java',
                        grading_mode VARCHAR(32) NOT NULL DEFAULT 'testcase',
                        ai_grading_rubric TEXT NULL,
                        ai_grading_focus_json JSON NULL,
                        ai_grading_pass_threshold INT NOT NULL DEFAULT 85,
                        ai_grading_confidence_threshold FLOAT NOT NULL DEFAULT 0.85,
                        test_cases_json JSON NULL,
                        knowledge_node_ids_json JSON NULL,
                        difficulty VARCHAR(32) NOT NULL DEFAULT 'medium',
                        source VARCHAR(32) NOT NULL DEFAULT 'assignment',
                        content_hash VARCHAR(64) NOT NULL,
                        reuse_count INT NOT NULL DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT uq_question_bank_teacher_content UNIQUE (teacher_id, content_hash)
                    )
                    """
                )
            )
            connection.execute(text("CREATE INDEX ix_question_bank_items_teacher_id ON question_bank_items (teacher_id)"))
            connection.execute(text("CREATE INDEX ix_question_bank_items_question_type ON question_bank_items (question_type)"))
            connection.execute(text("CREATE INDEX ix_question_bank_items_difficulty ON question_bank_items (difficulty)"))
            connection.execute(text("CREATE INDEX ix_question_bank_items_source ON question_bank_items (source)"))
            connection.execute(text("CREATE INDEX ix_question_bank_items_content_hash ON question_bank_items (content_hash)"))


def _ensure_assignment_graph_linkage(engine: Engine) -> None:
    inspector = inspect(engine)
    try:
        table_names = set(inspector.get_table_names())
        submission_columns = {column["name"] for column in inspector.get_columns("assignment_submissions")} if "assignment_submissions" in table_names else set()
    except Exception:
        return

    with engine.begin() as connection:
        if "assignment_question_knowledge_nodes" not in table_names:
            connection.execute(
                text(
                    """
                    CREATE TABLE assignment_question_knowledge_nodes (
                        id INTEGER PRIMARY KEY,
                        question_id INTEGER NOT NULL,
                        knowledge_node_id INTEGER NOT NULL,
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        CONSTRAINT uq_assignment_question_knowledge_node UNIQUE (question_id, knowledge_node_id)
                    )
                    """
                )
            )
            connection.execute(text("CREATE INDEX ix_assignment_question_knowledge_nodes_question_id ON assignment_question_knowledge_nodes (question_id)"))
            connection.execute(text("CREATE INDEX ix_assignment_question_knowledge_nodes_knowledge_node_id ON assignment_question_knowledge_nodes (knowledge_node_id)"))

        if "user_concept_mastery" not in table_names:
            connection.execute(
                text(
                    """
                    CREATE TABLE user_concept_mastery (
                        id INTEGER PRIMARY KEY,
                        student_id INTEGER NOT NULL,
                        knowledge_node_id INTEGER NOT NULL,
                        mastery_score INTEGER NOT NULL DEFAULT 50,
                        positive_evidence_count INTEGER NOT NULL DEFAULT 0,
                        negative_evidence_count INTEGER NOT NULL DEFAULT 0,
                        status VARCHAR(32) NOT NULL DEFAULT 'partial',
                        last_source_submission_id INTEGER NULL,
                        last_evaluated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT uq_student_knowledge_mastery UNIQUE (student_id, knowledge_node_id)
                    )
                    """
                )
            )
            connection.execute(text("CREATE INDEX ix_user_concept_mastery_student_id ON user_concept_mastery (student_id)"))
            connection.execute(text("CREATE INDEX ix_user_concept_mastery_knowledge_node_id ON user_concept_mastery (knowledge_node_id)"))

        if "assignment_submissions" in table_names:
            if "trust_label" not in submission_columns:
                connection.execute(text("ALTER TABLE assignment_submissions ADD COLUMN trust_label VARCHAR(64) NULL"))
            if "trust_score" not in submission_columns:
                connection.execute(text("ALTER TABLE assignment_submissions ADD COLUMN trust_score FLOAT NULL"))
            if "excluded_from_mastery_update" not in submission_columns:
                connection.execute(text("ALTER TABLE assignment_submissions ADD COLUMN excluded_from_mastery_update BOOLEAN NOT NULL DEFAULT 0"))


def _ensure_teacher_seed(engine: Engine) -> None:
    with Session(engine) as session:
        user = session.query(User).filter(User.username == settings.teacher_seed_username).first()
        if user:
            if user.role != "teacher":
                user.role = "teacher"
                session.commit()
            return

        teacher = User(
            username=settings.teacher_seed_username,
            password_hash=get_password_hash(settings.teacher_seed_password),
            role="teacher",
        )
        session.add(teacher)
        session.commit()


def _ensure_student_class_seed(engine: Engine) -> None:
    students = [
        *[(f"student{index:02d}", "软件1班") for index in range(1, 5)],
        *[(f"student{index:02d}", "软件2班") for index in range(5, 11)],
    ]
    with Session(engine) as session:
        for username, class_name in students:
            user = session.query(User).filter(User.username == username).first()
            if user:
                user.role = "student"
                user.class_name = class_name
                continue
            session.add(
                User(
                    username=username,
                    password_hash=get_password_hash("123456"),
                    role="student",
                    class_name=class_name,
                )
            )
        session.query(User).filter(
            User.role == "student",
            (User.class_name.is_(None)) | (User.class_name == ""),
        ).update({"class_name": "软件1班"}, synchronize_session=False)
        session.commit()
