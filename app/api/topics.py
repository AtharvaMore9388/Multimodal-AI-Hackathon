from fastapi import APIRouter, Query
from typing import Optional

from app.core import storage

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("/")
def list_topics(subject: Optional[str] = Query(None)):
    return {"subject": subject, "topics": storage.list_topics(subject)}


@router.get("/graph")
def course_flow_map(subject: Optional[str] = Query(None)):
    graph = storage.course_flow_map(subject)
    return {"subject": subject, **graph}
