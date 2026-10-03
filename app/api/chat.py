from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from app.services import rag as rag_svc

router = APIRouter(prefix="/chat", tags=["chat"])


class AskIn(BaseModel):
    question: str
    subject: Optional[str] = None
    user_email: Optional[str] = None
    lang: str = "en"
    top_k: int = 5


@router.post("/ask")
def ask(data: AskIn):
    return rag_svc.ask(
        question=data.question,
        subject=data.subject,
        user_email=data.user_email,
        lang=data.lang,
        top_k=data.top_k,
    )
