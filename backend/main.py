from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import assignment, auth, chat as chat_routes, quiz, teacher, weak_points
from backend.core.config import settings
from backend.db import base  # noqa: F401
from backend.db.bootstrap import ensure_schema_and_seed
from backend.db.session import Base, engine
from backend.services.chat_service import close_cached_clients


Base.metadata.create_all(bind=engine)
ensure_schema_and_seed(engine)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat_routes.router)
app.include_router(quiz.router)
app.include_router(teacher.router)
app.include_router(assignment.teacher_router)
app.include_router(assignment.student_router)
app.include_router(weak_points.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.on_event("shutdown")
def shutdown_clients():
    close_cached_clients()
