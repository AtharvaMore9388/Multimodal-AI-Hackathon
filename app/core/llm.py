import json
import os
import re
from typing import Any, Optional

LOW_RELEVANCE_THRESHOLD = 0.22


def out_of_scope_decision(contexts: list[dict[str, Any]], question: Optional[str] = None) -> tuple[bool, str]:
    if not contexts:
        return False, "NO_CONTEXT"
    best = max((c.get("relevance", 0.0) for c in contexts), default=0.0)
    if question:
        q_tokens = set(re.findall(r"[A-Za-z0-9_]+", (question or "").lower()))
        best_overlap = 0.0
        for c in contexts:
            c_text = (c.get("text") or c.get("excerpt") or "").lower()
            c_tokens = set(re.findall(r"[A-Za-z0-9_]+", c_text))
            if q_tokens and c_tokens:
                overlap = len(q_tokens & c_tokens) / max(1.0, len(q_tokens))
                best_overlap = max(best_overlap, overlap)
        if best_overlap < 0.08:
            return False, f"LOW_OVERLAP ({best_overlap:.2f})"
    if best < LOW_RELEVANCE_THRESHOLD:
        return False, f"LOW_RELEVANCE ({best:.2f})"
    return True, "IN_SCOPE"


SYSTEM_PROMPT_EN = """You are StudyBuddy, an AI tutoring assistant specialized in course material only.

Rules:
1. Answer strictly using the provided CITED CONTEXTS.
2. Every claim must be backed by a cited context.
3. If context does not cover the question, you MUST label the answer [UNSOURCED] with [GENERAL_KNOWLEDGE_ONLY] preamble and explicitly warn the user.
4. If context covers the question, label the answer [SOURCE-BACKED] and prefix key explanations with inline [ref:N] markers matching the context index.
5. Keep explanations concise, student-friendly, and structured.

Output format:
[SCOPE_LABEL]
Answer text with inline citations where applicable.
"""

SYSTEM_PROMPT_HI = """You are StudyBuddy, a bilingual AI tutoring assistant.

Rules:
1. Primarily write in English but interleave Hindi explanation sentences for key technical terms
   (examples: paging -> पेजिंग, deadlock -> गतिरोध, semaphore -> सेमाफोर, scheduling -> शेड्यूलिंग).
2. Translate any concept definition sentence once into Hindi right after the English definition.
3. Otherwise follow the same strict grounding rules: label [SOURCE-BACKED] or [UNSOURCED]/[GENERAL_KNOWLEDGE_ONLY], cite contexts with [ref:N].

Output format:
[SCOPE_LABEL]
Answer (bilingual English + Hindi for key terms) with inline citations.
"""


def build_rag_prompt(question: str, contexts: list[dict[str, Any]], lang: str = "en") -> str:
    lang = (lang or "en").lower()[:2]
    system = SYSTEM_PROMPT_HI if lang == "hi" else SYSTEM_PROMPT_EN
    ctx_lines = []
    for i, c in enumerate(contexts):
        src = c.get("source", "")
        page = c.get("page")
        slide = c.get("slide")
        ts = c.get("video_start_s")
        loc = ""
        if page:
            loc = f" page {page}"
        elif slide:
            loc = f" slide {slide}"
        elif ts is not None:
            loc = f" timestamp {ts:.0f}s"
        text = (c.get("text") or "").strip()[:1200]
        ctx_lines.append(f"[{i+1}] {src}{loc}: {text}")
    context_block = "\n".join(ctx_lines) if ctx_lines else "(No course contexts retrieved)"
    return f"""{system}

=== CITED CONTEXTS ===
{context_block}

=== STUDENT QUESTION ===
{question}

=== YOUR RESPONSE ===
"""


def _synthetic_extract(text: str, max_sentences: int = 3) -> str:
    sents = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(sents[:max_sentences])


def synthetic_rag_answer(question: str, contexts: list[dict[str, Any]], lang: str = "en") -> dict[str, Any]:
    in_scope, reason = out_of_scope_decision(contexts, question=question)
    if not in_scope:
        return {
            "scope_label": "UNSOURCED",
            "scope_reason": reason,
            "answer_text": "[UNSOURCED]\n[GENERAL_KNOWLEDGE_ONLY]\nThis question is not covered by the uploaded course material. Ask about the lectures, slides, or textbook you have ingested, and I will give a cited source-backed answer.",
            "sources": [],
        }
    q_tokens = set(re.findall(r"[A-Za-z0-9_]+", question.lower()))
    scored = []
    for i, c in enumerate(contexts):
        text = (c.get("text") or "").lower()
        c_tokens = set(re.findall(r"[A-Za-z0-9_]+", text))
        overlap = len(q_tokens & c_tokens) / max(1, len(q_tokens))
        scored.append((i, c, overlap))
    scored.sort(key=lambda x: x[2], reverse=True)
    best_idx, best_ctx, _ = scored[0]
    excerpt = _synthetic_extract(best_ctx.get("text", ""), max_sentences=3)
    refs = []
    for i, (_, c, overlap) in enumerate(scored[:3]):
        if overlap > 0 or i == 0:
            refs.append({
                "ref": f"[{len(refs)+1}]",
                **c,
                "relevance": c.get("relevance", 0.5 + 0.1 * (2 - i)),
            })
    answer_body = ""
    if lang == "hi":
        hi_terms = {
            "paging": "पेजिंग", "page": "पेज", "deadlock": "गतिरोध", "semaphore": "सेमाफोर",
            "scheduling": "शेड्यूलिंग", "process": "प्रोसेस", "thread": "थ्रेड",
            "memory": "मेमोरी", "fault": "फॉल्ट", "mutex": "म्यूटेक्स",
        }
        translated = excerpt
        for eng, hi in hi_terms.items():
            translated = re.sub(rf"\b{re.escape(eng)}\b", f"{eng} ({hi})", translated, flags=re.IGNORECASE)
        answer_body = (
            f"[SOURCE-BACKED]\nKey explanation [ref:{best_idx+1}]: {translated}\n\n"
            f"Summary: Based on {len(refs)} cited course source(s), the answer is drawn from the passages above."
        )
    else:
        answer_body = (
            f"[SOURCE-BACKED]\nThe answer is based on the following cited source passage [ref:{best_idx+1}]:\n\n"
            f"{excerpt}\n\n"
            f"This draws from {len(refs)} context chunk(s) retrieved from your course material."
        )
    return {
        "scope_label": "SOURCE-BACKED",
        "scope_reason": reason,
        "answer_text": answer_body,
        "sources": refs,
    }


def synthetic_quiz_question(topic_name: str, concept_name: str, concept_def: str,
                            qtype: str = "mcq", difficulty: str = "medium",
                            variant: int = 0, rng: Any = None) -> dict[str, Any]:
    qtype = (qtype or "mcq").lower()
    if rng is None:
        import random as _r
        rng = _r.Random(f"{topic_name}:{concept_name}:{variant}")
    diff_prefix = {
        "easy": "Basic",
        "medium": "Intermediate",
        "hard": "Advanced",
    }.get(difficulty, "Concept")
    if qtype == "short":
        variants = [
            f"Define {concept_name} in the context of {topic_name}.",
            f"Explain what {concept_name} means with respect to {topic_name}.",
            f"In {topic_name}, briefly describe the purpose of {concept_name}.",
            f"What is the role of {concept_name} when studying {topic_name}?",
        ]
        qt = variants[variant % len(variants)]
        return {
            "qtype": "short",
            "difficulty": difficulty,
            "question_text": f"[{diff_prefix}] {qt}",
            "correct_answer": concept_def,
            "ideal_answer": concept_def,
        }
    if qtype == "numerical":
        variants_params = [
            (4, 8), (3, 9), (2, 16), (5, 32), (6, 64),
        ]
        frames, pages = variants_params[variant % len(variants_params)]
        qt = (
            f"[{diff_prefix}] A system implements {concept_name} with {frames} frames and {pages} pages. "
            f"How many entries are stored in the page table (one entry per logical page)?"
        )
        return {
            "qtype": "numerical",
            "difficulty": difficulty,
            "question_text": qt,
            "correct_answer": str(pages),
            "ideal_answer": f"{pages} (one entry per logical page in a page-table based system)",
        }
    tokens = [t for t in re.findall(r"[A-Z][a-zA-Z]+", concept_def + " " + concept_name) if len(t) > 3]
    seen = set()
    distractors = []
    for t in tokens:
        if t not in seen and t.lower() != concept_name.lower():
            distractors.append(t)
            seen.add(t)
    extra_distro = [
        "Memory Segment", "I/O Buffer", "Cache Coherency", "Scheduler Tick",
        "Context Switch", "Interrupt Vector", "Kernel Trap", "Page Daemon",
    ]
    for ed in extra_distro:
        if ed not in distractors and len(distractors) < 3:
            distractors.append(ed)
    while len(distractors) < 3:
        distractors.append(f"Alternative-{concept_name}-{len(distractors)+1}")
    distractors = distractors[:3]
    options = [concept_name] + distractors
    rng.shuffle(options)
    correct_idx = options.index(concept_name)
    letters = ["A", "B", "C", "D"]
    mcq_variants = [
        f'Which of the following best matches the concept described as: "{concept_def[:160]}" under {topic_name}?',
        f"In the context of {topic_name}, which option identifies {concept_name} given the description: \"{concept_def[:130]}\"?",
        f'Pick the correct term that means: "{concept_def[:140]}" (topic: {topic_name}).',
        f"[{diff_prefix}] Choose the concept that satisfies: \"{concept_def[:140]}\".",
    ]
    qt = mcq_variants[variant % len(mcq_variants)]
    return {
        "qtype": "mcq",
        "difficulty": difficulty,
        "question_text": qt,
        "options_json": json.dumps([f"{letters[i]}. {opt}" for i, opt in enumerate(options[:4])], ensure_ascii=False),
        "correct_answer": letters[correct_idx],
        "ideal_answer": f"Option {letters[correct_idx]} ({concept_name}) correctly identifies: {concept_def}",
    }


def synthetic_flashcard(concept_name: str, concept_def: str, card_type: str = "define") -> dict[str, Any]:
    if card_type == "compare":
        return {
            "type": "compare",
            "front": f"Compare {concept_name} vs a sibling concept (e.g. Process vs Thread style).",
            "back": f"Focus: {concept_name} — {concept_def}. (Check sibling concept card for other side.)",
        }
    if card_type == "cloze":
        words = concept_def.split()
        if len(words) >= 4:
            hidden = words[len(words) // 2]
            cloze = " ".join("____" if w == hidden else w for w in words)
        else:
            cloze = "____: " + concept_def
        return {
            "type": "cloze",
            "front": f"Fill in the blank: {cloze}",
            "back": concept_def,
        }
    return {
        "type": "define",
        "front": f"Define {concept_name}.",
        "back": concept_def,
    }


def try_openai_chat(prompt: str, default: str, api_key: Optional[str] = None) -> str:
    key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not key or not key.startswith("sk-"):
        return default
    try:
        import httpx
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 600,
            },
            timeout=15.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        return default
    except Exception:
        return default
