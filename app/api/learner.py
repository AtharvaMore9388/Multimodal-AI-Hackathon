from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

from app.services import learner as learner_svc
from app.core import storage

router = APIRouter(prefix="/learner", tags=["learner"])


class OnboardingIn(BaseModel):
    user_email: str
    subjects_of_interest: list[str] = []
    current_level: str = "beginner"
    goal: str = ""


@router.post("/complete-onboarding")
def complete_onboarding(data: OnboardingIn):
    return learner_svc.complete_onboarding(
        user_email=data.user_email,
        subjects_of_interest=data.subjects_of_interest,
        current_level=data.current_level,
        goal=data.goal,
    )


@router.get("/study-schedule")
def study_schedule(
    user_email: str = Query(...),
    days: int = Query(14, ge=1, le=60),
    exam_date: Optional[str] = Query(None),
    subject: Optional[str] = Query(None),
):
    return learner_svc.suggest_study_schedule(
        user_email=user_email, days_until_exam=days, exam_date=exam_date, subject=subject,
    )


@router.get("/flashcards")
def flashcards(
    user_email: str = Query(...),
    subject: Optional[str] = Query(None),
    limit: int = Query(12, ge=1, le=100),
    only_weak: bool = Query(True),
):
    return learner_svc.generate_flashcards(
        user_email=user_email, subject=subject, limit=limit, only_weak=only_weak,
    )


@router.get("/is-new")
def is_new_student(user_email: str = Query(...)):
    return {"user_email": user_email, "is_new": storage.is_new_student(user_email)}
