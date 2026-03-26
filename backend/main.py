from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import auth, chat as chat_routes, weak_points
from backend.core.config import settings
from backend.db import base  # noqa: F401
from backend.db.session import Base, engine


Base.metadata.create_all(bind=engine)

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
app.include_router(weak_points.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
