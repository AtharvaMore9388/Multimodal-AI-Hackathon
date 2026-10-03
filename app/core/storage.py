import sqlite3
import hashlib
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "study_buddy.db"

ALPHA = 0.22
BONUS_CORRECT = 1.0
PENALTY_WRONG = 0.0
MASTERY_THRESHOLD = 0.75

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    subject TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    user_email TEXT,
    total_pages INTEGER DEFAULT 0,
    total_slides INTEGER DEFAULT 0,
    duration_seconds REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS doc_chunks (
    chunk_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    page INTEGER,
    slide INTEGER,
    video_start_s REAL,
    video_end_s REAL,
    figures_count INTEGER DEFAULT 0,
    figure_keywords TEXT,
    embedding_json TEXT,
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
);

CREATE TABLE IF NOT EXISTS topics (
    topic_id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    name TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    prereq_json TEXT,
    parent_id TEXT,
    FOREIGN KEY (parent_id) REFERENCES topics(topic_id)
);

CREATE TABLE IF NOT EXISTS concepts (
    concept_id TEXT PRIMARY KEY,
    topic_id TEXT NOT NULL,
    name TEXT NOT NULL,
    definition TEXT NOT NULL,
    FOREIGN KEY (topic_id) REFERENCES topics(topic_id)
);

CREATE TABLE IF NOT EXISTS doc_chunk_topic_links (
    chunk_id TEXT NOT NULL,
    topic_id TEXT NOT NULL,
    relevance REAL DEFAULT 1.0,
    PRIMARY KEY (chunk_id, topic_id),
    FOREIGN KEY (chunk_id) REFERENCES doc_chunks(chunk_id),
    FOREIGN KEY (topic_id) REFERENCES topics(topic_id)
);

CREATE TABLE IF NOT EXISTS question_bank (
    qid TEXT PRIMARY KEY,
    fingerprint TEXT UNIQUE NOT NULL,
    qtype TEXT NOT NULL,
    subject TEXT NOT NULL,
    topic_id TEXT,
    difficulty TEXT DEFAULT 'medium',
    question_text TEXT NOT NULL,
    options_json TEXT,
    correct_answer TEXT NOT NULL,
    ideal_answer TEXT,
    source_doc_id TEXT,
    source_page INTEGER,
    source_slide INTEGER,
    source_video_ts REAL,
    citation_summary TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (topic_id) REFERENCES topics(topic_id)
);

CREATE TABLE IF NOT EXISTS user_quiz_answers (
    answer_id TEXT PRIMARY KEY,
    user_email TEXT NOT NULL,
    qid TEXT NOT NULL,
    quiz_run_id TEXT,
    user_answer TEXT,
    is_correct INTEGER NOT NULL,
    score REAL,
    answered_at TEXT NOT NULL,
    FOREIGN KEY (qid) REFERENCES question_bank(qid)
);

CREATE TABLE IF NOT EXISTS user_mastery (
    user_email TEXT NOT NULL,
    topic_id TEXT NOT NULL,
    mastery REAL NOT NULL DEFAULT 0.1,
    attempts INTEGER NOT NULL DEFAULT 0,
    correct_count INTEGER NOT NULL DEFAULT 0,
    last_updated TEXT NOT NULL,
    next_review TEXT,
    PRIMARY KEY (user_email, topic_id),
    FOREIGN KEY (topic_id) REFERENCES topics(topic_id)
);

CREATE TABLE IF NOT EXISTS user_interactions (
    interaction_id TEXT PRIMARY KEY,
    user_email TEXT NOT NULL,
    interaction_type TEXT NOT NULL,
    topic_id TEXT,
    relevance REAL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_onboarding (
    user_email TEXT PRIMARY KEY,
    onboarded_at TEXT,
    subjects_of_interest TEXT,
    current_level TEXT,
    goal TEXT
);

CREATE TABLE IF NOT EXISTS eval_runs (
    run_id TEXT PRIMARY KEY,
    eval_name TEXT NOT NULL,
    subject TEXT NOT NULL,
    user_email TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    summary_json TEXT
);

CREATE TABLE IF NOT EXISTS eval_rows (
    row_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    question TEXT NOT NULL,
    gold_contexts_json TEXT,
    gold_answer TEXT,
    system_answer TEXT,
    retrieved_contexts_json TEXT,
    in_scope INTEGER,
    metrics_json TEXT,
    FOREIGN KEY (run_id) REFERENCES eval_runs(run_id)
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        _seed_default_topics(conn)
    finally:
        conn.close()


def _seed_default_topics(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys=OFF")
    try:
        subject = "Operating Systems"
        default_topics = [
            ("os_paging", "Paging", json.dumps(["os_memory_management"]), "os_memory_management"),
            ("os_memory_management", "Memory Management", json.dumps(["os_processes"]), None),
            ("os_processes", "Processes and Threads", None, None),
            ("os_deadlocks", "Deadlocks", json.dumps(["os_processes", "os_memory_management"]), None),
            ("os_semaphores", "Semaphores and Synchronization", json.dumps(["os_processes"]), "os_processes"),
            ("os_scheduling", "CPU Scheduling", json.dumps(["os_processes"]), "os_processes"),
            ("os_thrashing", "Thrashing", json.dumps(["os_paging", "os_memory_management"]), "os_paging"),
            ("os_bankers", "Banker's Algorithm", json.dumps(["os_deadlocks"]), "os_deadlocks"),
        ]
        concepts = [
            ("os_paging", "Page Table", "A data structure used by the OS to map logical page numbers to physical frame addresses."),
            ("os_paging", "Page Fault", "An interrupt raised when a page is not present in physical memory, requiring a disk load."),
            ("os_paging", "TLB", "Translation Lookaside Buffer - a cache for recent page table lookups."),
            ("os_memory_management", "Logical Address", "Address generated by the CPU, translated by the MMU."),
            ("os_memory_management", "Physical Address", "Actual address on the RAM chips seen by the memory bus."),
            ("os_processes", "Process", "An instance of a running program with its own address space and PCB."),
            ("os_processes", "Thread", "A lightweight execution unit sharing the parent process's address space."),
            ("os_deadlocks", "Mutual Exclusion", "Deadlock condition 1: at least one resource held in non-sharable mode."),
            ("os_deadlocks", "Hold and Wait", "Deadlock condition 2: a process holds resources while requesting more held by others."),
            ("os_deadlocks", "No Preemption", "Deadlock condition 3: resources cannot be forcibly taken from holders."),
            ("os_deadlocks", "Circular Wait", "Deadlock condition 4: a chain of processes exists where each waits for the next."),
            ("os_semaphores", "Mutex Lock", "A binary semaphore providing mutual exclusion over a critical section."),
            ("os_semaphores", "Counting Semaphore", "A semaphore with value >= 0 controlling access to N identical resources."),
            ("os_scheduling", "Round Robin", "Preemptive scheduler giving each process a fixed time quantum slice."),
            ("os_scheduling", "SJF", "Shortest Job First - optimal schedule for minimal average waiting time."),
            ("os_thrashing", "Working Set", "The set of pages a process actively uses in a locality window."),
            ("os_bankers", "Safe State", "A state where an allocation order exists such that every process can finish."),
        ]
        for tid, name, prereq, parent in default_topics:
            conn.execute(
                "INSERT OR IGNORE INTO topics(topic_id, subject, name, prereq_json, parent_id) VALUES (?,?,?,?,?)",
                (tid, subject, name, prereq, parent),
            )
        for tid, cname, cdef in concepts:
            cid = hashlib.sha1(f"{tid}:{cname}".encode()).hexdigest()[:20]
            conn.execute(
                "INSERT OR IGNORE INTO concepts(concept_id, topic_id, name, definition) VALUES (?,?,?,?)",
                (cid, tid, cname, cdef),
            )
        conn.commit()
    finally:
        conn.execute("PRAGMA foreign_keys=ON")


def add_document(doc: dict[str, Any]) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO documents(doc_id, filename, file_type, subject, uploaded_at, user_email, total_pages, total_slides, duration_seconds) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                doc["doc_id"], doc["filename"], doc["file_type"], doc["subject"], doc["uploaded_at"],
                doc.get("user_email"), doc.get("total_pages", 0), doc.get("total_slides", 0),
                doc.get("duration_seconds", 0),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def add_doc_chunk(chunk: dict[str, Any]) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO doc_chunks(chunk_id, doc_id, chunk_index, text, page, slide, video_start_s, video_end_s, figures_count, figure_keywords) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                chunk["chunk_id"], chunk["doc_id"], chunk["chunk_index"], chunk["text"],
                chunk.get("page"), chunk.get("slide"), chunk.get("video_start_s"),
                chunk.get("video_end_s"), chunk.get("figures_count", 0),
                chunk.get("figure_keywords"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def upsert_topic(topic: dict[str, Any]) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO topics(topic_id, subject, name, confidence, prereq_json, parent_id) VALUES (?,?,?,?,?,?)",
            (
                topic["topic_id"], topic["subject"], topic["name"],
                topic.get("confidence", 1.0), topic.get("prereq_json"), topic.get("parent_id"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def add_concept(concept: dict[str, Any]) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO concepts(concept_id, topic_id, name, definition) VALUES (?,?,?,?)",
            (concept["concept_id"], concept["topic_id"], concept["name"], concept["definition"]),
        )
        conn.commit()
    finally:
        conn.close()


def link_doc_chunk_to_topics(chunk_id: str, topic_relevance: list[tuple[str, float]]) -> None:
    conn = _connect()
    try:
        for topic_id, rel in topic_relevance:
            conn.execute(
                "INSERT OR REPLACE INTO doc_chunk_topic_links(chunk_id, topic_id, relevance) VALUES (?,?,?)",
                (chunk_id, topic_id, rel),
            )
        conn.commit()
    finally:
        conn.close()


def _normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())


def add_question(q: dict[str, Any]) -> str:
    norm = _normalize(q["question_text"])
    fingerprint = hashlib.sha1(f"{q['qtype']}:{norm}".encode()).hexdigest()[:20]
    qid = q.get("qid") or fingerprint
    conn = _connect()
    try:
        conn.execute(
            """INSERT OR IGNORE INTO question_bank
               (qid, fingerprint, qtype, subject, topic_id, difficulty, question_text,
                options_json, correct_answer, ideal_answer, source_doc_id, source_page,
                source_slide, source_video_ts, citation_summary, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                qid, fingerprint, q["qtype"], q["subject"], q.get("topic_id"),
                q.get("difficulty", "medium"), q["question_text"],
                q.get("options_json"), q["correct_answer"], q.get("ideal_answer", ""),
                q.get("source_doc_id"), q.get("source_page"), q.get("source_slide"),
                q.get("source_video_ts"), q.get("citation_summary"),
                q.get("created_at", datetime.utcnow().isoformat()),
            ),
        )
        cur = conn.execute("SELECT qid FROM question_bank WHERE fingerprint=?", (fingerprint,))
        row = cur.fetchone()
        conn.commit()
        return row["qid"] if row else qid
    finally:
        conn.close()


def used_qids_for(user_email: str) -> set[str]:
    conn = _connect()
    try:
        cur = conn.execute(
            "SELECT qid FROM user_quiz_answers WHERE user_email=?", (user_email,)
        )
        return {row["qid"] for row in cur.fetchall()}
    finally:
        conn.close()


def pick_unique_questions(user_email: str, count: int, topic_id: Optional[str] = None,
                          difficulty: Optional[str] = None, subject: Optional[str] = None) -> list[dict[str, Any]]:
    used = used_qids_for(user_email)
    conn = _connect()
    try:
        sql = "SELECT * FROM question_bank WHERE 1=1"
        params: list[Any] = []
        if topic_id:
            sql += " AND topic_id=?"
            params.append(topic_id)
        if difficulty:
            sql += " AND difficulty=?"
            params.append(difficulty)
        if subject:
            sql += " AND subject=?"
            params.append(subject)
        cur = conn.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        fresh = [r for r in rows if r["qid"] not in used]
        chosen = fresh[:count] if len(fresh) >= count else (fresh + rows[: max(0, count - len(fresh))])
        return chosen[:count]
    finally:
        conn.close()


def record_answer(user_email: str, qid: str, user_answer: str,
                  is_correct: bool, score: float, quiz_run_id: Optional[str] = None) -> None:
    aid = hashlib.sha1(f"{user_email}:{qid}:{datetime.utcnow().isoformat()}".encode()).hexdigest()[:20]
    conn = _connect()
    try:
        conn.execute(
            """INSERT INTO user_quiz_answers(answer_id, user_email, qid, quiz_run_id, user_answer, is_correct, score, answered_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (aid, user_email, qid, quiz_run_id, user_answer, 1 if is_correct else 0,
             score, datetime.utcnow().isoformat()),
        )
        cur = conn.execute("SELECT topic_id FROM question_bank WHERE qid=?", (qid,))
        row = cur.fetchone()
        topic_id = row["topic_id"] if row else None
        conn.commit()
    finally:
        conn.close()
    if topic_id:
        update_mastery(user_email, topic_id, 1 if is_correct else 0)


def update_mastery(user_email: str, topic_id: str, correct_0_1: int,
                   today: Optional[datetime] = None, skip_bkt: bool = False) -> dict[str, Any]:
    today = today or datetime.utcnow()
    conn = _connect()
    try:
        cur = conn.execute(
            "SELECT mastery, attempts, correct_count FROM user_mastery WHERE user_email=? AND topic_id=?",
            (user_email, topic_id),
        )
        row = cur.fetchone()
        if row:
            current = row["mastery"]
            attempts = row["attempts"] + 1
            correct_count = row["correct_count"] + correct_0_1
        else:
            current = 0.1
            attempts = 1
            correct_count = correct_0_1

        if skip_bkt:
            new_mastery = current
        else:
            observation = BONUS_CORRECT if correct_0_1 else -PENALTY_WRONG
            new_mastery = current + ALPHA * (observation - current)
            new_mastery = max(0.0, min(1.0, new_mastery))

        if new_mastery >= 0.85:
            gap_days = 14
        elif new_mastery >= 0.7:
            gap_days = 7
        elif new_mastery >= 0.5:
            gap_days = 3
        elif new_mastery >= 0.3:
            gap_days = 1
        else:
            gap_days = 0
        next_review = (today + timedelta(days=gap_days)).isoformat()

        conn.execute(
            """INSERT INTO user_mastery(user_email, topic_id, mastery, attempts, correct_count, last_updated, next_review)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(user_email, topic_id) DO UPDATE SET
               mastery=excluded.mastery,
               attempts=excluded.attempts,
               correct_count=excluded.correct_count,
               last_updated=excluded.last_updated,
               next_review=excluded.next_review""",
            (user_email, topic_id, new_mastery, attempts, correct_count,
             today.isoformat(), next_review),
        )
        conn.commit()
        iid = hashlib.sha1(f"{user_email}:{topic_id}:{today.isoformat()}:{correct_0_1}".encode()).hexdigest()[:20]
        conn.execute(
            "INSERT OR IGNORE INTO user_interactions(interaction_id, user_email, interaction_type, topic_id, relevance, created_at) VALUES (?,?,?,?,?,?)",
            (iid, user_email, "mastery_update", topic_id, float(correct_0_1), today.isoformat()),
        )
        conn.commit()
        return {"mastery": new_mastery, "attempts": attempts, "next_review": next_review}
    finally:
        conn.close()


def get_mastery(user_email: str, subject: Optional[str] = None) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        sql = """SELECT um.*, t.name AS topic_name, t.subject FROM user_mastery um
                 LEFT JOIN topics t ON t.topic_id = um.topic_id
                 WHERE um.user_email=?"""
        params: list[Any] = [user_email]
        if subject:
            sql += " AND t.subject=?"
            params.append(subject)
        cur = conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def _weak_topics(user_email: str, subject: Optional[str] = None, threshold: float = 0.5) -> list[dict[str, Any]]:
    rows = get_mastery(user_email, subject)
    return [r for r in rows if r["mastery"] < threshold]


def is_new_student(user_email: str) -> bool:
    conn = _connect()
    try:
        cur1 = conn.execute(
            "SELECT COUNT(*) AS c FROM user_interactions WHERE user_email=?", (user_email,)
        )
        interactions = cur1.fetchone()["c"]
        cur2 = conn.execute(
            "SELECT onboarded_at FROM user_onboarding WHERE user_email=?", (user_email,)
        )
        row = cur2.fetchone()
        onboarded = row["onboarded_at"] if row else None
        return interactions == 0 and onboarded is None
    finally:
        conn.close()


def complete_onboarding(user_email: str, subjects_of_interest: list[str],
                        current_level: str, goal: str) -> None:
    conn = _connect()
    try:
        conn.execute(
            """INSERT INTO user_onboarding(user_email, onboarded_at, subjects_of_interest, current_level, goal)
               VALUES (?,?,?,?,?)
               ON CONFLICT(user_email) DO UPDATE SET
               onboarded_at=excluded.onboarded_at,
               subjects_of_interest=excluded.subjects_of_interest,
               current_level=excluded.current_level,
               goal=excluded.goal""",
            (user_email, datetime.utcnow().isoformat(), json.dumps(subjects_of_interest),
             current_level, goal),
        )
        conn.commit()
    finally:
        conn.close()


def list_topics(subject: Optional[str] = None) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        sql = "SELECT * FROM topics"
        params: list[Any] = []
        if subject:
            sql += " WHERE subject=?"
            params.append(subject)
        cur = conn.execute(sql, params)
        topics = [dict(r) for r in cur.fetchall()]
        for t in topics:
            cur2 = conn.execute("SELECT concept_id, name, definition FROM concepts WHERE topic_id=?", (t["topic_id"],))
            t["concepts"] = [dict(r) for r in cur2.fetchall()]
        return topics
    finally:
        conn.close()


def course_flow_map(subject: Optional[str] = None) -> dict[str, Any]:
    topics = list_topics(subject)
    nodes = []
    edges = []
    for t in topics:
        nodes.append({
            "id": t["topic_id"],
            "name": t["name"],
            "subject": t["subject"],
            "confidence": t.get("confidence", 1.0),
            "parent_id": t.get("parent_id"),
            "concepts": t.get("concepts", []),
        })
        if t.get("prereq_json"):
            try:
                prereqs = json.loads(t["prereq_json"])
                for p in prereqs:
                    edges.append({"from": p, "to": t["topic_id"], "label": "prerequisite"})
            except Exception:
                pass
        if t.get("parent_id"):
            edges.append({"from": t["parent_id"], "to": t["topic_id"], "label": "subtopic"})
    return {"nodes": nodes, "edges": edges}


def create_eval_run(eval_name: str, subject: str, user_email: Optional[str] = None) -> str:
    run_id = hashlib.sha1(f"{eval_name}:{datetime.utcnow().isoformat()}".encode()).hexdigest()[:20]
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO eval_runs(run_id, eval_name, subject, user_email, started_at) VALUES (?,?,?,?,?)",
            (run_id, eval_name, subject, user_email, datetime.utcnow().isoformat()),
        )
        conn.commit()
        return run_id
    finally:
        conn.close()


def add_eval_row(run_id: str, question: str, gold_contexts: list[str], gold_answer: str,
                 system_answer: str, retrieved_contexts: list[str], in_scope: bool,
                 metrics: dict[str, float]) -> None:
    row_id = hashlib.sha1(f"{run_id}:{question}".encode()).hexdigest()[:20]
    conn = _connect()
    try:
        conn.execute(
            """INSERT INTO eval_rows(row_id, run_id, question, gold_contexts_json, gold_answer,
                                     system_answer, retrieved_contexts_json, in_scope, metrics_json)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (row_id, run_id, question, json.dumps(gold_contexts), gold_answer,
             system_answer, json.dumps(retrieved_contexts), 1 if in_scope else 0,
             json.dumps(metrics)),
        )
        conn.commit()
    finally:
        conn.close()


def finalize_eval_run(run_id: str, summary: dict[str, Any]) -> None:
    conn = _connect()
    try:
        conn.execute(
            "UPDATE eval_runs SET completed_at=?, summary_json=? WHERE run_id=?",
            (datetime.utcnow().isoformat(), json.dumps(summary), run_id),
        )
        conn.commit()
    finally:
        conn.close()


def list_eval_runs() -> list[dict[str, Any]]:
    conn = _connect()
    try:
        cur = conn.execute("SELECT * FROM eval_runs ORDER BY started_at DESC")
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_eval_run(run_id: str) -> dict[str, Any]:
    conn = _connect()
    try:
        cur = conn.execute("SELECT * FROM eval_runs WHERE run_id=?", (run_id,))
        row = cur.fetchone()
        run = dict(row) if row else {}
        cur2 = conn.execute("SELECT * FROM eval_rows WHERE run_id=?", (run_id,))
        run["rows"] = [dict(r) for r in cur2.fetchall()]
        return run
    finally:
        conn.close()
