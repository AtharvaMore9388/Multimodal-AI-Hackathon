import hashlib
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Optional

from app.services import quiz as quiz_svc, learner as learner_svc

router = APIRouter(prefix="/quiz", tags=["quiz"])


class GenerateIn(BaseModel):
    subject: str = "Operating Systems"
    topic: Optional[str] = None
    count: int = 5
    difficulty: str = "medium"
    qtypes: Optional[list[str]] = None
    user_email: Optional[str] = None
    mode: str = "standard"
    source_doc_id: Optional[str] = None


class DiagnosticIn(BaseModel):
    user_email: str
    subject: str = "Operating Systems"


class AnswerItem(BaseModel):
    qid: str
    user_answer: str


class GradeIn(BaseModel):
    user_email: str
    quiz_run_id: Optional[str] = None
    subject: Optional[str] = None
    answers: list[AnswerItem]


@router.post("/generate")
def generate(data: GenerateIn):
    qs = quiz_svc.generate_questions(
        subject=data.subject, topic=data.topic, count=data.count,
        difficulty=data.difficulty, qtypes=data.qtypes,
        user_email=data.user_email, mode=data.mode,
        source_doc_id=data.source_doc_id,
    )
    return {
        "subject": data.subject,
        "topic": data.topic,
        "difficulty": data.difficulty,
        "questions": qs,
    }


@router.post("/diagnostic")
def diagnostic(data: DiagnosticIn):
    return learner_svc.diagnostic_quiz_spec(user_email=data.user_email, subject=data.subject)


@router.post("/grade")
def grade(data: GradeIn):
    run_id = data.quiz_run_id or hashlib.sha1(f"{data.user_email}:{datetime.utcnow().isoformat()}".encode()).hexdigest()[:16]
    answers = [{"qid": a.qid, "user_answer": a.user_answer} for a in data.answers]
    return quiz_svc.grade_response(data.user_email, run_id, answers, subject=data.subject)
