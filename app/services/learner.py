import hashlib
import json
import random
from datetime import datetime, timedelta
from typing import Any, Optional

from app.core import llm, storage


def diagnostic_quiz_spec(user_email: str, subject: str = "Operating Systems") -> dict[str, Any]:
    topics = storage.list_topics(subject)
    rng = random.Random(f"diagnostic:{user_email}:{subject}")
    picked = rng.sample(topics, min(5, len(topics))) if len(topics) >= 5 else topics
    spread = ["mcq", "mcq", "short", "short", "numerical"]
    qs = []
    from app.services import quiz as quiz_svc
    for i, t in enumerate(picked):
        qtype = spread[i % len(spread)]
        qlist = quiz_svc.generate_questions(subject, t["topic_id"], count=1, difficulty="easy", qtypes=[qtype], user_email=user_email, mode="diagnostic")
        if qlist:
            qs.append(qlist[0])
    if not qs:
        qs = quiz_svc.generate_questions(subject, None, count=5, difficulty="easy", qtypes=spread, user_email=user_email, mode="diagnostic")
    return {
        "subject": subject,
        "is_new_student": storage.is_new_student(user_email),
        "topics_covered": [{"topic_id": q.get("topic_id"), "topic_name": q.get("topic_name") or ""} for q in qs],
        "questions": qs,
        "estimated_minutes": 2,
    }


def complete_onboarding(user_email: str, subjects_of_interest: list[str],
                      current_level: str, goal: str) -> dict[str, Any]:
    storage.complete_onboarding(user_email, subjects_of_interest or [], current_level or "beginner", goal or "")
    return {
        "user_email": user_email,
        "onboarded_at": datetime.utcnow().isoformat(),
        "subjects_of_interest": subjects_of_interest or [],
        "current_level": current_level or "beginner",
        "goal": goal or "",
        "next_step": "Take the diagnostic quiz at /quiz/diagnostic to seed initial per-topic mastery.",
    }


def suggest_study_schedule(user_email: str, days_until_exam: int = 14,
                         exam_date: Optional[str] = None,
                         subject: Optional[str] = None) -> dict[str, Any]:
    mastery_rows = storage.get_mastery(user_email, subject)
    topics_all = storage.list_topics(subject)
    mastery_by_tid = {r["topic_id"]: r for r in mastery_rows}
    today = datetime.utcnow()
    days: list[dict[str, Any]] = []
    for day_idx in range(days_until_exam):
        day_date = today + timedelta(days=day_idx)
        iso = day_date.isoformat()
        is_review_lock = exam_date and (datetime.fromisoformat(exam_date) - day_date).days <= 2 if exam_date else False
        weakest_new = []
        spaced = []
        threshold = []
        if not is_review_lock:
            no_mastery = [t for t in topics_all if t["topic_id"] not in mastery_by_tid]
            weak_with_low = sorted(
                [t for t in topics_all if mastery_by_tid.get(t["topic_id"], {}).get("mastery", 0.0) < 0.4],
                key=lambda t: mastery_by_tid.get(t["topic_id"], {}).get("mastery", 0.0),
            )
            weakest_new = [{"topic_id": t["topic_id"], "topic_name": t["name"], "reason": "weak/new"} for t in (no_mastery + weak_with_low)[:2]]
            due = [
                r for r in mastery_rows if r.get("next_review") and r["next_review"] <= iso
            ]
            spaced = [{"topic_id": r["topic_id"], "topic_name": r["topic_name"], "reason": "spaced due"} for r in due[:2]]
            near = [
                t for t in topics_all if 0.45 <= mastery_by_tid.get(t["topic_id"], {}).get("mastery", 0.0) <= 0.65
            ]
            threshold = [{"topic_id": t["topic_id"], "topic_name": t["name"], "reason": "near-threshold 0.45-0.65"} for t in near[:2]]
        else:
            mixed = sorted(topics_all, key=lambda t: mastery_by_tid.get(t["topic_id"], {}).get("mastery", 0.5))
            weakest_new = [{"topic_id": t["topic_id"], "topic_name": t["name"], "reason": "mixed pre-exam review"} for t in mixed[:6]]
        slots = (weakest_new + spaced + threshold)[:6]
        days.append({
            "day": day_idx + 1,
            "date": day_date.strftime("%Y-%m-%d"),
            "is_review_lock": bool(is_review_lock),
            "slots": slots,
            "focus_summary": f"{len(weakest_new)} weak/new + {len(spaced)} spaced + {len(threshold)} near-threshold" if not is_review_lock else "pre-exam mixed review",
        })
    return {
        "user_email": user_email,
        "days_until_exam": days_until_exam,
        "exam_date": exam_date,
        "days": days,
    }


def generate_flashcards(user_email: str, subject: Optional[str] = None, limit: int = 12,
                         only_weak: bool = True) -> dict[str, Any]:
    topics = storage.list_topics(subject)
    weak_ids = {w["topic_id"] for w in storage._weak_topics(user_email, subject)} if only_weak else None
    card_types = ["define", "cloze", "compare"]
    cards: list[dict[str, Any]] = []
    sibling_pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    siblings = [t for t in topics if t.get("parent_id")]
    by_parent: dict[str, list[dict[str, Any]]] = {}
    for s in siblings:
        by_parent.setdefault(s["parent_id"], []).append(s)
    for kids in by_parent.values():
        for i in range(len(kids)):
            for j in range(i + 1, len(kids)):
                sibling_pairs.append((kids[i], kids[j]))
    si = 0
    for t in topics:
        if only_weak and weak_ids is not None and t["topic_id"] not in weak_ids:
            continue
        concepts = t.get("concepts", []) or []
        for idx, c in enumerate(concepts[:3]):
            ct = card_types[idx % len(card_types)]
            if ct == "compare" and si < len(sibling_pairs):
                a, b = sibling_pairs[si]
                si += 1
                a_conc = (a.get("concepts") or [{}])[0]
                b_conc = (b.get("concepts") or [{}])[0]
                cards.append({
                    "card_id": hashlib.sha1(f"{a['topic_id']}:vs:{b['topic_id']}".encode()).hexdigest()[:16],
                    "type": "compare",
                    "topic_id": t["topic_id"],
                    "topic_name": t["name"],
                    "front": f"Compare {a['name']} vs {b['name']}.",
                    "back": f"{a['name']}: {a_conc.get('definition', '')}\n\nvs\n\n{b['name']}: {b_conc.get('definition', '')}",
                })
            else:
                card = llm.synthetic_flashcard(c["name"], c["definition"], card_type=ct if ct != "compare" else "define")
                cid = c.get("concept_id") or hashlib.sha1(c["name"].encode()).hexdigest()[:16]
                cards.append({
                    "card_id": hashlib.sha1(f"{cid}:{ct}".encode()).hexdigest()[:16],
                    "type": card["type"],
                    "topic_id": t["topic_id"],
                    "topic_name": t["name"],
                    "front": card["front"],
                    "back": card["back"],
                })
            if len(cards) >= limit:
                return {
                    "user_email": user_email, "subject": subject,
                    "only_weak": only_weak, "cards": cards,
                }
    return {
        "user_email": user_email,
        "subject": subject,
        "only_weak": only_weak,
        "cards": cards,
    }
