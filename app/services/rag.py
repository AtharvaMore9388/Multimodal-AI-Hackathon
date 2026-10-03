import re
from datetime import datetime
from typing import Any, Optional

from app.core import llm, storage
from app.services import ingest as ingest_svc


def _cited_source_dict(ctx: dict[str, Any], idx: int, question_tokens: set[str]) -> dict[str, Any]:
    text = (ctx.get("text") or "").strip()
    t_tokens = set(re.findall(r"[A-Za-z0-9_]+", text.lower()))
    overlap = len(question_tokens & t_tokens) / max(1, len(question_tokens))
    relevance = float(ctx.get("relevance", 0.5 + 0.3 * overlap))
    page = ctx.get("page")
    slide = ctx.get("slide")
    v_start = ctx.get("video_start_s")
    v_end = ctx.get("video_end_s")
    clickback = None
    if v_start is not None:
        m, s = divmod(int(v_start), 60)
        clickback = f"#t={m}:{s:02d}"
    return {
        "ref": f"[{idx+1}]",
        "chunk_id": ctx.get("chunk_id"),
        "doc_id": ctx.get("doc_id"),
        "source": ctx.get("source") or ctx.get("filename") or "course material",
        "file_type": ctx.get("file_type"),
        "page": page,
        "slide": slide,
        "video_start_s": v_start,
        "video_end_s": v_end,
        "video_clickback_s": v_start,
        "clickback": clickback,
        "figures_count": ctx.get("figures_count", 0),
        "figure_keywords": ctx.get("figure_keywords"),
        "topic_id": ctx.get("topic_id"),
        "topic": ctx.get("topic_name"),
        "concepts": ctx.get("concepts"),
        "relevance": round(relevance, 4),
        "excerpt": text[:500],
    }


def ask(question: str, subject: Optional[str] = None, user_email: Optional[str] = None,
        lang: str = "en", top_k: int = 5) -> dict[str, Any]:
    contexts = ingest_svc.search_similar(question, top_k=top_k)
    q_tokens = set(re.findall(r"[A-Za-z0-9_]+", question.lower()))
    cited_sources = [_cited_source_dict(c, i, q_tokens) for i, c in enumerate(contexts)]
    prompt = llm.build_rag_prompt(question, contexts, lang=lang)
    synth = llm.synthetic_rag_answer(question, contexts, lang=lang)
    answer_text = llm.try_openai_chat(prompt, synth["answer_text"])
    scope_label = synth["scope_label"]
    scope_reason = synth["scope_reason"]
    m = re.match(r"^\s*\[?(SOURCE-BACKED|UNSOURCED)\]?\s*", answer_text)
    if m:
        scope_label = m.group(1)
        answer_text = answer_text[m.end():]
    sources = cited_sources or synth.get("sources", [])
    if user_email:
        for s in sources:
            if s.get("topic_id") and s.get("relevance", 0) >= 0.6:
                storage.update_mastery(user_email, s["topic_id"], 1, today=datetime.utcnow())
            elif s.get("topic_id"):
                storage.update_mastery(user_email, s["topic_id"], 0, today=datetime.utcnow())
    return {
        "question": question,
        "scope_label": scope_label,
        "scope_reason": scope_reason,
        "in_scope": scope_label == "SOURCE-BACKED",
        "answer_text": answer_text,
        "sources": sources,
        "lang": lang,
    }
