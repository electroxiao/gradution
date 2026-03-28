from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.security import get_password_hash
from backend.models.user import User


def ensure_schema_and_seed(engine: Engine) -> None:
    _ensure_user_role_column(engine)
    _ensure_teacher_seed(engine)


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
