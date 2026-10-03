import hashlib
import json
import math
import random
import re
from datetime import datetime
from typing import Any, Optional

from app.core import llm, storage
from app.services import ingest as ingest_svc


def _citation_for_topic(topic_id: str) -> str:
    conn = storage._connect()
    try:
        cur = conn.execute("SELECT name FROM topics WHERE topic_id=?", (topic_id,))
        row = cur.fetchone()
        topic_name = row["name"] if row else topic_id
        cur2 = conn.execute(
            "SELECT c.page, c.slide, c.video_start_s, d.filename "
            "FROM doc_chunk_topic_links l "
            "LEFT JOIN doc_chunks c ON c.chunk_id=l.chunk_id "
            "LEFT JOIN documents d ON d.doc_id=c.doc_id "
            "WHERE l.topic_id=? LIMIT 1",
            (topic_id,),
        )
        r = cur2.fetchone()
        loc = ""
        if r:
            if r["page"]:
                loc = f"{r['filename']} p.{r['page']}"
            elif r["slide"]:
                loc = f"{r['filename']} slide {r['slide']}"
            elif r["video_start_s"] is not None:
                m, s = divmod(int(r["video_start_s"]), 60)
                loc = f"{r['filename']} @ {m}:{s:02d}"
            else:
                loc = r["filename"] or "course material"
        return f"Topic: {topic_name} — {loc or 'sourced from course material'}"
    finally:
        conn.close()


def generate_questions(subject: str, topic: Optional[str] = None, count: int = 5,
                     difficulty: str = "medium", qtypes: Optional[list[str]] = None,
                     user_email: Optional[str] = None, mode: str = "standard",
                     source_doc_id: Optional[str] = None) -> list[dict[str, Any]]:
    qtypes = qtypes or ["mcq", "short", "numerical"]
    topic_rows = storage.list_topics(subject)
    if topic:
        topic_rows = [t for t in topic_rows if t["topic_id"] == topic or t["name"].lower() == topic.lower() or topic.lower() in t["name"].lower()]
    if not topic_rows:
        topic_rows = storage.list_topics("Operating Systems")
    def _is_clean(s: str) -> bool:
        if not s or len(s) < 2:
            return False
        if "\ufffd" in s or "\x00" in s:
            return False
        printable = sum(1 for ch in s if 32 <= ord(ch) <= 126 or ord(ch) in (10, 13, 9))
        return (printable / len(s)) >= 0.85

    topic_pool: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for t in topic_rows:
        if not _is_clean(t.get("name", "")):
            continue
        for c in t.get("concepts", []):
            if _is_clean(c.get("name", "")) and _is_clean(c.get("definition", "")):
                topic_pool.append((t, c))
    if not topic_pool:
        topic_pool = [(topic_rows[0], {"name": "Paging", "definition": "Paging maps logical addresses to physical frames via a page table."}) for _ in range(count)]
    used = storage.used_qids_for(user_email) if user_email else set()
    seed_salt = datetime.utcnow().isoformat()
    rng = random.Random(f"{subject}:{topic or 'any'}:{count}:{mode}:{user_email or 'anon'}:{seed_salt}")
    out: list[dict[str, Any]] = []
    attempts = 0
    seen_fps_this_call: set[str] = set()
    while len(out) < count and attempts < count * 10 and topic_pool:
        attempts += 1
        if mode == "diagnostic":
            spread = ["mcq", "mcq", "short", "short", "numerical"]
            qtype = spread[len(out) % len(spread)]
        else:
            qtype = qtypes[len(out) % len(qtypes)]
        t, c = rng.choice(topic_pool)
        variant = attempts // 2 if attempts > 2 else 0
        base = llm.synthetic_quiz_question(
            t["name"], c["name"], c["definition"],
            qtype=qtype, difficulty=difficulty,
            variant=variant, rng=rng,
        )
        if not _is_clean(base.get("question_text", "")):
            continue
        src_summary = _citation_for_topic(t["topic_id"])
        q_payload = {
            "qtype": base["qtype"],
            "difficulty": difficulty,
            "subject": subject,
            "topic_id": t["topic_id"],
            "question_text": base["question_text"],
            "options_json": base.get("options_json"),
            "correct_answer": base["correct_answer"],
            "ideal_answer": base.get("ideal_answer", ""),
            "source_doc_id": source_doc_id,
            "source_page": None,
            "source_slide": None,
            "source_video_ts": None,
            "citation_summary": src_summary,
            "created_at": datetime.utcnow().isoformat(),
        }
        qid = storage.add_question(q_payload)
        q_payload["qid"] = qid
        q_payload["topic_name"] = t["name"]
        q_payload["source_page"] = None
        if q_payload["qid"] in seen_fps_this_call:
            continue
        seen_fps_this_call.add(q_payload["qid"])
        if q_payload["qid"] not in used or attempts > count * 3:
            out.append(q_payload)
    return out


def _grade_mcq(user_answer: str, correct: str, options_json: Optional[str]) -> tuple[bool, float, str]:
    options: list[str] = []
    if options_json:
        try:
            options = json.loads(options_json)
        except Exception:
            options = []
    ua = (user_answer or "").strip().upper()
    ca = (correct or "").strip().upper()
    if ua == ca:
        return True, 1.0, f"Option {ua} is correct."
    letter_pat = re.compile(r"\b([A-D])\b")
    um = letter_pat.search(ua)
    cm = letter_pat.search(ca)
    if um and cm and um.group(1) == cm.group(1):
        return True, 1.0, f"Option {um.group(1)} is correct."
    if options:
        try:
            u_idx = ord(ua[0]) - ord("A") if ua and "A" <= ua[0] <= "Z" else -1
            c_idx = ord(ca[0]) - ord("A") if ca and "A" <= ca[0] <= "Z" else -1
            if 0 <= u_idx < len(options) and 0 <= c_idx < len(options):
                u_text = options[u_idx][3:].strip().lower()
                c_text = options[c_idx][3:].strip().lower()
                if u_text and c_text and (u_text in c_text or c_text in u_text):
                    return True, 1.0, "Answer text matches the correct option."
        except Exception:
            pass
    return False, 0.0, f"Correct answer is {ca}."


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _grade_short(user_answer: str, correct: str, ideal: Optional[str]) -> tuple[bool, float, str]:
    if not user_answer and not correct:
        return True, 1.0, "Correct."
    if user_answer and correct and user_answer.strip().lower() == correct.strip().lower():
        return True, 1.0, "Exact match with correct answer."
    if user_answer and ideal and user_answer.strip().lower() == ideal.strip().lower():
        return True, 1.0, "Exact match with ideal answer."
    u_toks = set(re.findall(r"[A-Za-z0-9_]+", (user_answer or "").lower()))
    c_toks = set(re.findall(r"[A-Za-z0-9_]+", (correct or "").lower()))
    i_toks = set(re.findall(r"[A-Za-z0-9_]+", (ideal or correct or "").lower()))
    kw_sim = _jaccard(u_toks, c_toks)
    overlap_ideal = _jaccard(u_toks, i_toks)
    score = 0.6 * kw_sim + 0.4 * overlap_ideal
    is_correct = score >= 0.5
    feedback = f"Keyword Jaccard={kw_sim:.2f}; Ideal overlap={overlap_ideal:.2f}; Score={score:.2f}."
    if is_correct:
        feedback += " Answer accepted (>= 0.5)."
    else:
        feedback += f" Expected: {ideal or correct}"
    return is_correct, round(score, 4), feedback


def _grade_numerical(user_answer: str, correct: str, tol: float = 1e-2) -> tuple[bool, float, str]:
    try:
        uv = float(re.search(r"-?\d+(?:\.\d+)?", (user_answer or "").strip()).group(0))
    except Exception:
        uv = None
    try:
        cv = float(re.search(r"-?\d+(?:\.\d+)?", (correct or "").strip()).group(0))
    except Exception:
        cv = None
    if uv is None or cv is None:
        return False, 0.0, f"Could not compare numerically. Expected {correct!r}."
    ok = math.isclose(uv, cv, abs_tol=max(tol, abs(cv) * 0.01))
    diff = abs(uv - cv)
    if ok:
        return True, 1.0, f"Values match (|{uv}-{cv}|={diff:.4f} <= tol)."
    return False, 0.0, f"Off by {diff:.4f}. Expected {cv}."


def grade_response(user_email: str, quiz_run_id: Optional[str],
                   answers: list[dict[str, Any]], subject: Optional[str] = None) -> dict[str, Any]:
    detail: list[dict[str, Any]] = []
    total_score = 0.0
    per_topic: dict[str, list[float]] = {}
    missed_concept_by_topic: dict[str, list[str]] = {}
    correct_count = 0
    q_ids_graded = 0
    pending_updates: list[tuple[str, int]] = []
    conn = storage._connect()
    try:
        for a in answers:
            qid = a.get("qid")
            if not qid:
                continue
            cur = conn.execute("SELECT * FROM question_bank WHERE qid=?", (qid,))
            q = cur.fetchone()
            if not q:
                continue
            q_ids_graded += 1
            q_type = q["qtype"]
            user_ans = a.get("user_answer", "")
            if q_type == "mcq":
                ok, score, fb = _grade_mcq(user_ans, q["correct_answer"], q["options_json"])
            elif q_type == "numerical":
                ok, score, fb = _grade_numerical(user_ans, q["correct_answer"])
            else:
                ok, score, fb = _grade_short(user_ans, q["correct_answer"], q["ideal_answer"])
            correct_count += int(ok)
            total_score += score
            tid = q["topic_id"]
            if tid:
                per_topic.setdefault(tid, []).append(score)
                if not ok:
                    missed = missed_concept_by_topic.setdefault(tid, [])
                    for kw in re.findall(r"[A-Z][a-z]+", q["question_text"])[:3]:
                        if kw not in missed:
                            missed.append(kw)
                aid = hashlib.sha1(f"{user_email}:{qid}:{datetime.utcnow().isoformat()}".encode()).hexdigest()[:20]
                conn.execute(
                    """INSERT INTO user_quiz_answers(answer_id, user_email, qid, quiz_run_id, user_answer, is_correct, score, answered_at)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (aid, user_email, qid, quiz_run_id, user_ans, 1 if ok else 0,
                     float(score), datetime.utcnow().isoformat()),
                )
                pending_updates.append((tid, 1 if ok else 0))
            detail.append({
                "qid": qid,
                "qtype": q_type,
                "question": q["question_text"],
                "user_answer": user_ans,
                "correct_answer": q["correct_answer"],
                "is_correct": ok,
                "score": score,
                "feedback": {
                    "text": fb,
                    "citation_summary": q["citation_summary"],
                    "explanation": q["ideal_answer"] or "",
                },
            })
        conn.commit()
    finally:
        conn.close()
    for tid, correct_0_1 in pending_updates:
        storage.update_mastery(user_email, tid, correct_0_1)
    per_topic_average = {tid: round(sum(s) / max(1, len(s)), 4) for tid, s in per_topic.items()}
    weak = storage._weak_topics(user_email, subject)
    likely_misconceptions = []
    conn = storage._connect()
    try:
        for tid, kws in missed_concept_by_topic.items():
            cur = conn.execute("SELECT name FROM topics WHERE topic_id=?", (tid,))
            row = cur.fetchone()
            name = row["name"] if row else tid
            if per_topic_average.get(tid, 1.0) < 0.5:
                likely_misconceptions.append({
                    "topic_id": tid,
                    "topic_name": name,
                    "missed_keywords": kws,
                    "hint": f"Review {name}: focus on {', '.join(kws) or 'core concepts'}.",
                })
    finally:
        conn.close()
    return {
        "quiz_run_id": quiz_run_id,
        "user_email": user_email,
        "total_questions": q_ids_graded,
        "correct_count": correct_count,
        "score": correct_count,
        "total": max(1, q_ids_graded),
        "percent": round(100.0 * correct_count / max(1, q_ids_graded), 1),
        "average_score": round(total_score / max(1, q_ids_graded), 4),
        "per_topic_average": per_topic_average,
        "weak_topics_to_review": [{"topic_id": w["topic_id"], "topic_name": w["topic_name"], "mastery": w["mastery"]} for w in weak[:5]],
        "likely_misconceptions": likely_misconceptions,
        "detail": detail,
    }
