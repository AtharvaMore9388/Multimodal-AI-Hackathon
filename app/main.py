import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import storage

ENV_PATH = Path(__file__).resolve().parent / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    example = Path(__file__).resolve().parent / ".env.example"
    if example.exists():
        load_dotenv(example)

storage.DB_PATH = Path(os.environ.get("DATABASE_URL", "").replace("sqlite:///", "").lstrip("/")) if os.environ.get("DATABASE_URL", "").startswith("sqlite") else (Path(__file__).resolve().parent / "study_buddy.db")
storage.init_db()

app = FastAPI(
    title="StudyBuddy — Multimodal AI Study Companion",
    description="FastAPI backend for the Multimodal AI Hackathon Track D: Personalized Tutoring & Adaptive Learning.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import ingest, chat, quiz, learner, topics, evaluation, audio  # noqa: E402

app.include_router(ingest.router)
app.include_router(chat.router)
app.include_router(quiz.router)
app.include_router(learner.router)
app.include_router(topics.router)
app.include_router(evaluation.router)
app.include_router(audio.router)


from fastapi.responses import HTMLResponse


@app.get("/health", tags=["meta"])
def health():
    return {
        "status": "ok",
        "service": "study_buddy_backend",
        "version": "1.0.0",
        "db": str(storage.DB_PATH),
        "offline_mode": not bool(os.environ.get("OPENAI_API_KEY", "").startswith("sk-")),
    }


@app.get("/api/info", tags=["meta"])
def api_info():
    return {
        "name": "StudyBuddy API",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "routers": ["ingest", "chat", "quiz", "learner", "topics", "evaluation", "audio"],
    }


@app.get("/", response_class=HTMLResponse, tags=["web"])
@app.get("/app", response_class=HTMLResponse, tags=["web"])
def root():
    static_file = Path(__file__).resolve().parent / "static" / "index.html"
    if static_file.exists():
        return HTMLResponse(content=static_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>StudyBuddy Web App</h1><p>Starting up...</p>")

