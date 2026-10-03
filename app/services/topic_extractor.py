import hashlib
import json
import re
from typing import Any

SUBJECT_KEYWORDS = {
    "Operating Systems": [
        "paging", "page fault", "tlb", "memory management", "logical address", "physical address",
        "process", "thread", "deadlock", "mutual exclusion", "hold and wait", "circular wait",
        "semaphore", "mutex", "scheduling", "round robin", "sjf", "thrashing", "working set",
        "banker's algorithm", "safe state", "frame", "page table", "swap", "context switch",
    ],
    "Computer Networks": [
        "tcp", "udp", "ip", "osi", "router", "switch", "packet", "ethernet", "dns", "http",
        "congestion", "routing", "subnet", "firewall", "nat",
    ],
    "Database Systems": [
        "sql", "transaction", "acid", "normalization", "bcnf", "join", "index", "b+ tree",
        "concurrency", "lock", "deadlock", "query", "erd", "relational",
    ],
}

def _is_clean_text(s: str) -> bool:
    if not s or len(s) < 2:
        return False
    if "\ufffd" in s or "\x00" in s:
        return False
    printable = sum(1 for ch in s if 32 <= ord(ch) <= 126 or ord(ch) in (10, 13, 9))
    return (printable / len(s)) >= 0.85


CONCEPT_PATTERN = re.compile(r"([A-Z][A-Za-z&+/\- ]{2,40})\s*:\s*([^\n]{10,300})")


def _classify_subject(text: str, hint: str | None = None) -> str:
    if hint:
        for subj in SUBJECT_KEYWORDS:
            if subj.lower() == hint.lower() or hint.lower() in subj.lower() or subj.lower() in hint.lower():
                return subj
    scores: dict[str, int] = {s: 0 for s in SUBJECT_KEYWORDS}
    lower = text.lower()
    for subj, kws in SUBJECT_KEYWORDS.items():
        for kw in kws:
            if kw in lower:
                scores[subj] += 1
    best = max(scores.items(), key=lambda x: x[1])
    if best[1] > 0:
        return best[0]
    return hint or "General"


def extract_topics_and_concepts(text: str, subject_hint: str | None = None,
                                chunk_index: int = 0) -> dict[str, Any]:
    subject = _classify_subject(text, subject_hint)
    kws = SUBJECT_KEYWORDS.get(subject, [])
    lower = text.lower()
    found_topics = []
    for topic_id, topic_name, prereq, parent in _default_topic_rows_for(subject):
        nm = topic_name.lower()
        if nm in lower:
            found_topics.append({
                "topic_id": topic_id,
                "subject": subject,
                "name": topic_name,
                "confidence": min(1.0, 0.4 + 0.05 * len(kws)),
                "prereq_json": prereq,
                "parent_id": parent,
            })
    for kw in kws[:10]:
        if kw in lower and not any(t["name"].lower() == kw for t in found_topics):
            tid = hashlib.sha1(f"{subject}:{kw}:{chunk_index}".encode()).hexdigest()[:16]
            found_topics.append({
                "topic_id": tid,
                "subject": subject,
                "name": kw.title(),
                "confidence": 0.6,
                "prereq_json": None,
                "parent_id": None,
            })
    if not found_topics:
        tid = hashlib.sha1(f"{subject}:root:{chunk_index}".encode()).hexdigest()[:16]
        found_topics.append({
            "topic_id": tid,
            "subject": subject,
            "name": f"{subject} Concepts",
            "confidence": 0.5,
            "prereq_json": None,
            "parent_id": None,
        })

    matches = CONCEPT_PATTERN.findall(text)
    concepts = []
    seen = set()
    primary_topic = found_topics[0]
    for name, definition in matches:
        name = name.strip().rstrip(".")
        definition = definition.strip().rstrip(".")
        if 2 <= len(name) <= 60 and len(definition) >= 10 and name not in seen:
            if not _is_clean_text(name) or not _is_clean_text(definition):
                continue
            cid = hashlib.sha1(f"{primary_topic['topic_id']}:{name}".encode()).hexdigest()[:20]
            concepts.append({
                "concept_id": cid,
                "topic_id": primary_topic["topic_id"],
                "name": name,
                "definition": definition,
            })
            seen.add(name)
        if len(concepts) >= 8:
            break

    if not concepts:
        for idx, sent in enumerate(re.split(r"(?<=[.!?])\s+", text.strip())[:5]):
            words = sent.split()
            if len(words) >= 5 and len(words) <= 40:
                concept_name = " ".join(w for w in words if len(w) > 3)[:40].title() or f"Concept {idx+1}"
                cid = hashlib.sha1(f"{primary_topic['topic_id']}:def{idx}:{chunk_index}".encode()).hexdigest()[:20]
                concepts.append({
                    "concept_id": cid,
                    "topic_id": primary_topic["topic_id"],
                    "name": concept_name,
                    "definition": sent.rstrip("."),
                })
    return {
        "subject": subject,
        "topics": found_topics[:8],
        "concepts": concepts,
    }


def _default_topic_rows_for(subject: str) -> list[tuple[str, str, str | None, str | None]]:
    if subject == "Operating Systems":
        return [
            ("os_paging", "Paging", json.dumps(["os_memory_management"]), "os_memory_management"),
            ("os_memory_management", "Memory Management", json.dumps(["os_processes"]), None),
            ("os_processes", "Processes and Threads", None, None),
            ("os_deadlocks", "Deadlocks", json.dumps(["os_processes", "os_memory_management"]), None),
            ("os_semaphores", "Semaphores and Synchronization", json.dumps(["os_processes"]), "os_processes"),
            ("os_scheduling", "CPU Scheduling", json.dumps(["os_processes"]), "os_processes"),
            ("os_thrashing", "Thrashing", json.dumps(["os_paging", "os_memory_management"]), "os_paging"),
            ("os_bankers", "Banker's Algorithm", json.dumps(["os_deadlocks"]), "os_deadlocks"),
        ]
    return []
