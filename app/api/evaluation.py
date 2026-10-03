from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Optional

from app.core import storage
from app.services import evaluation as eval_svc
from app.evaluation import test_set

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


class RagEvalIn(BaseModel):
    eval_name: str = "team-gold-set-v1"
    subject: str = "Operating Systems"
    questions: Optional[list[dict[str, Any]]] = None
    user_email: Optional[str] = None


class SimulatedStudyIn(BaseModel):
    subject: str = "Operating Systems"


@router.post("/run-ragas")
def run_ragas(data: RagEvalIn):
    qs = data.questions
    if not qs:
        qs = test_set.OS_GOLD_SET
    return eval_svc.run_rag_eval(
        eval_name=data.eval_name, questions=qs, subject=data.subject, user_email=data.user_email,
    )


@router.post("/simulated-study")
def simulated_study(data: SimulatedStudyIn):
    return eval_svc.run_simulated_study(subject=data.subject)


@router.get("/runs")
def list_runs():
    return {"runs": storage.list_eval_runs()}


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    return storage.get_eval_run(run_id)


@router.get("/gold-set")
def gold_set(subject: str = "Operating Systems"):
    if subject == "Operating Systems":
        return {"subject": subject, "questions": test_set.OS_GOLD_SET}
    return {"subject": subject, "questions": []}
