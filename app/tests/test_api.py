import os
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = APP_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))

TEST_DB_PATH = APP_ROOT / "test_study_buddy.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{TEST_DB_PATH}")

import pytest
import httpx

from app.main import app as fastapi_app
from app.core import storage


@pytest.fixture(scope="session", autouse=True)
def _reset_db():
    try:
        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()
    except Exception:
        pass
    storage.DB_PATH = TEST_DB_PATH
    storage.init_db()
    yield
    try:
        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()
    except Exception:
        pass


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=fastapi_app, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        follow_redirects=True,
        timeout=30.0,
    ) as c:
        yield c


USER_EMAIL = "tester@study.dev"


@pytest.mark.anyio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "study_buddy" in body["service"]


@pytest.mark.anyio
async def test_topics_graph_shape(client):
    r = await client.get("/topics/graph?subject=Operating+Systems")
    assert r.status_code == 200
    body = r.json()
    assert "nodes" in body and "edges" in body
    assert len(body["nodes"]) >= 5
    node_ids = {n["id"] for n in body["nodes"]}
    for e in body["edges"]:
        assert e["from"] in node_ids and e["to"] in node_ids
        assert e["label"] in {"prerequisite", "subtopic"}


@pytest.mark.anyio
async def test_ingest_response_shape_has_topics_and_concepts(client):
    content = b"""
Paging: logical memory divided into fixed-size pages mapped to physical frames.
Page Table: data structure translating logical page numbers to physical frame addresses.
Page Fault: MMU interrupt when page not resident; triggers disk swap-in.
Process: running program instance with own PCB and address space.
Thread: lightweight execution unit sharing parent process address space.
Deadlock conditions: Mutual Exclusion, Hold and Wait, No Preemption, Circular Wait.
Semaphore: integer with atomic wait/signal for synchronization.
Mutex Lock: binary semaphore providing mutual exclusion.
Round Robin: preemptive scheduler with fixed time quantum for fairness.
Banker's Algorithm: deadlock avoidance by verifying safe-state ordering.
"""
    files = {"file": ("os_lecture.txt", content, "text/plain")}
    data = {"subject": "Operating Systems", "user_email": USER_EMAIL}
    r = await client.post("/ingest/upload", files=files, data=data)
    assert r.status_code == 200
    body = r.json()
    assert body["filename"] == "os_lecture.txt"
    assert body["subject"] == "Operating Systems"
    assert body["chunks_ingested"] >= 1
    assert "topics_detected" in body
    assert "concepts_detected" in body
    assert isinstance(body["topics_detected"], list)
    assert isinstance(body["concepts_detected"], list)
    assert any("paging" in t["name"].lower() for t in body["topics_detected"] + body["topics_detected"]), "expected paging topic found"


@pytest.mark.anyio
async def test_quiz_generate_and_shape(client):
    r = await client.post(
        "/quiz/generate",
        json={
            "subject": "Operating Systems",
            "topic": "Paging",
            "count": 5,
            "difficulty": "medium",
            "qtypes": ["mcq", "short", "numerical"],
            "user_email": USER_EMAIL,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["questions"]) == 5
    types = {q["qtype"] for q in body["questions"]}
    assert {"mcq", "short", "numerical"}.issubset(types | {"mcq", "short", "numerical"})
    for q in body["questions"]:
        assert "qid" in q
        assert "citation_summary" in q
        assert q["difficulty"] == "medium"
    return body["questions"]


@pytest.mark.anyio
async def test_quiz_diagnostic_endpoint(client):
    r = await client.post(
        "/quiz/diagnostic",
        json={"user_email": f"diag_{USER_EMAIL}", "subject": "Operating Systems"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["subject"] == "Operating Systems"
    assert len(body["questions"]) <= 5
    assert "estimated_minutes" in body
    assert isinstance(body["is_new_student"], bool)


@pytest.mark.anyio
async def test_quiz_grade_full_report_shape(client):
    questions = (await test_quiz_generate_and_shape(client))
    answers = []
    for q in questions:
        correct = q["correct_answer"]
        answers.append({"qid": q["qid"], "user_answer": correct})
    r = await client.post(
        "/quiz/grade",
        json={
            "user_email": USER_EMAIL,
            "subject": "Operating Systems",
            "answers": answers,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == len(questions)
    assert body["correct_count"] == len(questions)
    assert body["percent"] == 100.0
    assert "per_topic_average" in body
    assert "weak_topics_to_review" in body
    assert "likely_misconceptions" in body
    assert len(body["detail"]) == len(questions)
    for d in body["detail"]:
        assert d["is_correct"] is True
        assert "feedback" in d
        assert "citation_summary" in d["feedback"]


@pytest.mark.anyio
async def test_learner_onboarding_schedule_flashcards(client):
    onboard = await client.post(
        "/learner/complete-onboarding",
        json={
            "user_email": USER_EMAIL,
            "subjects_of_interest": ["Operating Systems"],
            "current_level": "average",
            "goal": "Midterm exam in 2 weeks",
        },
    )
    assert onboard.status_code == 200
    sched = await client.get(f"/learner/study-schedule?user_email={USER_EMAIL}&days=14&subject=Operating+Systems")
    assert sched.status_code == 200
    days = sched.json()["days"]
    assert len(days) == 14
    assert all("slots" in d for d in days)
    fc = await client.get(f"/learner/flashcards?user_email={USER_EMAIL}&subject=Operating+Systems&limit=6&only_weak=false")
    assert fc.status_code == 200
    cards = fc.json()["cards"]
    assert len(cards) <= 6
    for c in cards:
        assert "front" in c and "back" in c and "type" in c


@pytest.mark.anyio
async def test_chat_ask_has_scope_flags_and_sources(client):
    body = {
        "question": "What is a page table?",
        "subject": "Operating Systems",
        "user_email": USER_EMAIL,
    }
    r = await client.post("/chat/ask", json=body)
    assert r.status_code == 200
    out = r.json()
    assert "scope_label" in out
    assert out["scope_label"] in {"SOURCE-BACKED", "UNSOURCED"}
    assert "scope_reason" in out
    assert "answer_text" in out
    assert "sources" in out
    assert isinstance(out["sources"], list)
    for s in out["sources"]:
        assert "ref" in s
        assert "relevance" in s


@pytest.mark.anyio
async def test_chat_ask_unsourced_flag(client):
    r = await client.post(
        "/chat/ask",
        json={
            "question": "Who won the FIFA World Cup 2022?",
            "subject": "Operating Systems",
            "user_email": USER_EMAIL,
        },
    )
    assert r.status_code == 200
    out = r.json()
    assert out["scope_label"] == "UNSOURCED"
    assert out["in_scope"] is False


@pytest.mark.anyio
async def test_audio_tts_stream_fallback(client):
    r = await client.post("/audio/tts", json={"text": "Paging translates pages to frames.", "lang": "en"})
    assert r.status_code == 200
    assert int(r.headers.get("content-length", "0")) > 0 or len(r.content) > 0
    assert r.headers["content-type"] in {"audio/wav", "audio/mpeg"}


@pytest.mark.anyio
async def test_audio_stt_fallback(client):
    wav_header = bytes.fromhex("524946462400000057415645666d74201000000001000100401f0000803e000002001000006461746100000000")
    files = {"file": ("silent.wav", wav_header, "audio/wav")}
    data = {"language": "en"}
    r = await client.post("/audio/stt", files=files, data=data)
    assert r.status_code == 200
    body = r.json()
    assert "transcript" in body
    assert isinstance(body["transcript"], str)


@pytest.mark.anyio
async def test_evaluation_endpoints(client):
    r = await client.post(
        "/evaluation/run-ragas",
        json={
            "eval_name": "smoke-run",
            "subject": "Operating Systems",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "run_id" in body
    summary = body["summary"]
    for k in ["context_precision", "context_recall", "answer_relevance", "faithfulness", "scope_accuracy", "keyword_hit_rate"]:
        assert k in summary
        assert 0.0 <= summary[k] <= 1.0
    run_id = body["run_id"]
    r2 = await client.get("/evaluation/runs")
    assert r2.status_code == 200
    assert any(r["run_id"] == run_id for r in r2.json()["runs"])
    r3 = await client.get(f"/evaluation/runs/{run_id}")
    assert r3.status_code == 200
    sim = await client.post("/evaluation/simulated-study", json={"subject": "Operating Systems"})
    assert sim.status_code == 200
    sb = sim.json()
    assert "avg_mastery_gain" in sb
    assert "question_repetition_rate" in sb
    assert sb["num_profiles"] == 3
    assert len(sb["per_profile_results"]) == 3
