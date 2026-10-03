import json
import random
import re
from datetime import datetime
from typing import Any

from app.core import storage
from app.services import rag as rag_svc


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z0-9_]+", (text or "").lower()))


def context_precision(retrieved_contexts: list[str], gold_contexts: list[str]) -> float:
    if not retrieved_contexts:
        return 0.0
    hits = 0
    gold_set = {g.strip().lower() for g in gold_contexts if g.strip()}
    for rc in retrieved_contexts:
        rc_norm = (rc or "").strip().lower()
        if any(gs and (gs in rc_norm or rc_norm in gs) for gs in gold_set):
            hits += 1
            continue
        rc_toks = _tokens(rc)
        if any(len(_tokens(g) & rc_toks) >= max(3, len(_tokens(g)) // 2) for g in gold_contexts):
            hits += 1
    return hits / len(retrieved_contexts)


def context_recall(retrieved_contexts: list[str], gold_contexts: list[str]) -> float:
    if not gold_contexts:
        return 1.0
    covered = 0
    rc_blob = " ".join(retrieved_contexts).lower()
    for g in gold_contexts:
        g = (g or "").strip()
        if not g:
            covered += 1
            continue
        g_norm = g.lower()
        if g_norm in rc_blob:
            covered += 1
            continue
        g_toks = _tokens(g)
        rc_toks = _tokens(rc_blob)
        if g_toks and rc_toks and (len(g_toks & rc_toks) / max(1, len(g_toks))) >= 0.6:
            covered += 1
    return covered / len(gold_contexts)


def answer_relevance(answer: str, question: str) -> float:
    q_toks = _tokens(question)
    a_toks = _tokens(answer)
    if not q_toks:
        return 1.0 if a_toks else 0.0
    wh_q = {w for w in q_toks if w in {"what", "why", "how", "when", "where", "who", "which", "define", "explain", "compare"}}
    overlap = len(q_toks & a_toks) / max(1, len(q_toks))
    length_factor = min(1.0, len(a_toks) / max(4, len(q_toks) * 2))
    bonus = 0.1 if wh_q and len(a_toks) >= 5 else 0.0
    return max(0.0, min(1.0, 0.6 * overlap + 0.3 * length_factor + bonus))


def faithfulness(answer: str, contexts: list[str]) -> float:
    answer_sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", (answer or "").strip()) if s.strip()]
    if not answer_sents:
        return 0.0
    ctx_blob = " ".join(contexts).lower()
    supported = 0
    for s in answer_sents:
        s_toks = _tokens(s)
        if not s_toks:
            continue
        ctx_toks = _tokens(ctx_blob)
        frac = len(s_toks & ctx_toks) / max(1, len(s_toks))
        if frac >= 0.4 or s.lower() in ctx_blob:
            supported += 1
    return supported / max(1, len(answer_sents))


def scope_accuracy(in_scope_flag: bool, gold_should_be_in_scope: bool) -> float:
    return 1.0 if bool(in_scope_flag) == bool(gold_should_be_in_scope) else 0.0


def keyword_hit_rate(answer: str, gold_keywords: list[str]) -> float:
    if not gold_keywords:
        return 1.0
    a_toks = _tokens(answer)
    hits = sum(1 for kw in gold_keywords if kw.lower() in a_toks or kw.lower() in (answer or "").lower())
    return hits / len(gold_keywords)


def run_rag_eval(eval_name: str, questions: list[dict[str, Any]],
                 subject: str, user_email: str | None = None) -> dict[str, Any]:
    run_id = storage.create_eval_run(eval_name, subject, user_email)
    per_row: list[dict[str, Any]] = []
    metric_runs: dict[str, list[float]] = {
        "context_precision": [], "context_recall": [], "answer_relevance": [],
        "faithfulness": [], "scope_accuracy": [], "keyword_hit_rate": [],
    }
    for q in questions:
        question_text = q["question"]
        gold_contexts = q.get("gold_contexts", []) or []
        gold_answer = q.get("gold_answer", "") or ""
        gold_keywords = q.get("gold_keywords", []) or []
        gold_in_scope = q.get("in_scope", True)
        resp = rag_svc.ask(question_text, subject=subject, user_email=None, top_k=5)
        contexts = [s.get("excerpt", s.get("text", "")) for s in resp.get("sources", [])]
        system_answer = resp.get("answer_text", "")
        in_scope_flag = resp.get("in_scope", False)
        m_cp = context_precision(contexts, gold_contexts)
        m_cr = context_recall(contexts, gold_contexts)
        m_ar = answer_relevance(system_answer, question_text)
        m_fa = faithfulness(system_answer, contexts)
        m_sa = scope_accuracy(in_scope_flag, gold_in_scope)
        m_kh = keyword_hit_rate(system_answer, gold_keywords)
        metrics = {
            "context_precision": round(m_cp, 4),
            "context_recall": round(m_cr, 4),
            "answer_relevance": round(m_ar, 4),
            "faithfulness": round(m_fa, 4),
            "scope_accuracy": round(m_sa, 4),
            "keyword_hit_rate": round(m_kh, 4),
        }
        for k, v in metrics.items():
            metric_runs[k].append(v)
        storage.add_eval_row(run_id, question_text, gold_contexts, gold_answer,
                           system_answer, contexts, bool(in_scope_flag), metrics)
        per_row.append({
            "question": question_text,
            "in_scope_gold": gold_in_scope,
            "in_scope_system": bool(in_scope_flag),
            "metrics": metrics,
        })
    summary = {k: round(sum(v) / max(1, len(v)), 4) for k, v in metric_runs.items()}
    summary["questions_evaluated"] = len(per_row)
    storage.finalize_eval_run(run_id, summary)
    return {
        "run_id": run_id,
        "eval_name": eval_name,
        "subject": subject,
        "started_at": datetime.utcnow().isoformat(),
        "summary": summary,
        "rows": per_row,
    }


STUDENT_PROFILES = [
    {"name": "beginner", "p_correct": 0.35, "sessions": 5, "questions_per_session": 4},
    {"name": "average", "p_correct": 0.60, "sessions": 6, "questions_per_session": 4},
    {"name": "advanced", "p_correct": 0.85, "sessions": 4, "questions_per_session": 4},
]


def simulate_student(profile: dict[str, Any], subject: str = "Operating Systems") -> dict[str, Any]:
    email = f"sim_{profile['name']}_{abs(hash(profile['name'])) % 100000}@study.dev"
    rng = random.Random(hash(email) & 0xFFFFFFFF)
    topics = storage.list_topics(subject)
    initial_mastery: dict[str, float] = {}
    for t in topics:
        initial_mastery[t["topic_id"]] = 0.1
        storage.update_mastery(email, t["topic_id"], 0, skip_bkt=True)
    from app.services import quiz as quiz_svc
    qids_used: set[str] = set()
    for session_idx in range(profile["sessions"]):
        qs = quiz_svc.generate_questions(subject, None, count=profile["questions_per_session"],
                                       difficulty="medium", user_email=email, mode="standard")
        answers_batch = []
        for q in qs:
            qid = q.get("qid")
            if not qid:
                continue
            qids_used.add(qid)
            correct = rng.random() < profile["p_correct"]
            correct_answer = q.get("correct_answer", "") if correct else "wrong_answer_placeholder"
            answers_batch.append({"qid": qid, "user_answer": correct_answer})
        if answers_batch:
            run_id = f"sim_{email}_{session_idx}_{rng.randint(0, 9999)}"
            quiz_svc.grade_response(email, run_id, answers_batch, subject=subject)
    final = {r["topic_id"]: r["mastery"] for r in storage.get_mastery(email, subject)}
    gains = []
    for t in topics:
        tid = t["topic_id"]
        before = initial_mastery.get(tid, 0.1)
        after = final.get(tid, before)
        gains.append(after - before)
    return {
        "profile": profile["name"],
        "user_email": email,
        "questions_answered": len(qids_used),
        "unique_questions": len(qids_used),
        "avg_mastery_gain": round(sum(gains) / max(1, len(gains)), 4),
        "final_mastery_per_topic": {
            t["name"]: round(final.get(t["topic_id"], initial_mastery.get(t["topic_id"], 0.1)), 4)
            for t in topics
        },
    }


def run_simulated_study(subject: str = "Operating Systems") -> dict[str, Any]:
    results = [simulate_student(p, subject) for p in STUDENT_PROFILES]
    total_q_answered = sum(r["questions_answered"] for r in results)
    all_unique_qids: set[str] = set()
    for r in results:
        sim_email = r["user_email"]
        used = storage.used_qids_for(sim_email)
        all_unique_qids.update(used)
    unique_across_all = len(all_unique_qids)
    overall_gain = sum(r["avg_mastery_gain"] for r in results) / max(1, len(results))
    repetition_rate = 0.0
    if total_q_answered:
        repetition_rate = round(max(0.0, 1.0 - (unique_across_all / max(1, total_q_answered))), 4)
    return {
        "subject": subject,
        "num_profiles": len(STUDENT_PROFILES),
        "profiles": STUDENT_PROFILES,
        "avg_mastery_gain": round(overall_gain, 4),
        "question_repetition_rate": repetition_rate,
        "per_profile_results": results,
    }
