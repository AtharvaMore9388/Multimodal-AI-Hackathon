from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional

from app.services import ingest as ingest_svc

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    subject: Optional[str] = Form(None),
    user_email: Optional[str] = Form(None),
):
    try:
        raw = await file.read()
    except Exception as e:
        raise HTTPException(400, f"Could not read upload: {e}")
    if not file.filename:
        raise HTTPException(400, "Missing filename")
    result = ingest_svc.ingest_file(file.filename, raw, subject=subject, user_email=user_email)
    return result


@router.get("/documents")
def list_documents():
    from app.core import storage
    conn = storage._connect()
    try:
        cur = conn.execute("""
            SELECT d.*, COUNT(c.chunk_id) as chunk_count
            FROM documents d
            LEFT JOIN doc_chunks c ON c.doc_id = d.doc_id
            GROUP BY d.doc_id
            ORDER BY d.uploaded_at DESC
        """)
        return {"documents": [dict(r) for r in cur.fetchall()]}
    finally:
        conn.close()


@router.get("/documents/{doc_id}/chunks")
def get_document_chunks(doc_id: str):
    from app.core import storage
    conn = storage._connect()
    try:
        cur = conn.execute("SELECT * FROM doc_chunks WHERE doc_id=? ORDER BY chunk_index ASC", (doc_id,))
        return {"doc_id": doc_id, "chunks": [dict(r) for r in cur.fetchall()]}
    finally:
        conn.close()

