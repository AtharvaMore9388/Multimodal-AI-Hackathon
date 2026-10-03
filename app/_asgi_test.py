import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

LOG = Path(__file__).resolve().parent / "_asgi_test.log"
lines = []
def P(msg):
    lines.append(str(msg))
    print(msg)

try:
    P("Importing app...")
    from app.main import app
    P("App imported OK")
except Exception as e:
    P(f"App import FAIL: {e}")
    import traceback
    P(traceback.format_exc())
    LOG.write_text("\n".join(lines))
    sys.exit(1)

try:
    import httpx
    P(f"httpx version: {httpx.__version__}")
    transport = httpx.ASGITransport(app=app)
    P("ASGITransport created OK")
except Exception as e:
    P(f"Transport FAIL: {e}")
    import traceback
    P(traceback.format_exc())
    LOG.write_text("\n".join(lines))
    sys.exit(1)

async def run():
    import asyncio
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        for path, method, payload in [
            ("/health", "GET", None),
            ("/", "GET", None),
            ("/topics/graph?subject=Operating+Systems", "GET", None),
            ("/chat/ask", "POST", {"question": "What is a page table?", "subject": "Operating Systems", "user_email": "demo@study.dev"}),
            ("/chat/ask", "POST", {"question": "Who won FIFA 2022?", "subject": "Operating Systems", "user_email": "demo@study.dev"}),
            ("/quiz/generate", "POST", {"subject": "Operating Systems", "topic": "os_paging", "count": 5, "qtypes": ["mcq","short","numerical"], "user_email": "demo@study.dev"}),
            ("/learner/is-new?user_email=demo_new@study.dev", "GET", None),
            ("/audio/tts", "POST", {"text": "Paging maps pages to frames.", "lang": "en"}),
        ]:
            try:
                if method == "GET":
                    r = await client.get(path, timeout=30.0)
                else:
                    r = await client.post(path, json=payload, timeout=30.0)
                P(f"\n{method} {path.split('?')[0]} -> {r.status_code}")
                try:
                    body = r.json()
                    if path == "/health":
                        P(f"  {body}")
                    elif "graph" in path:
                        P(f"  nodes={len(body.get('nodes',[]))} edges={len(body.get('edges',[]))}")
                    elif "chat/ask" in path:
                        P(f"  scope_label={body.get('scope_label')} in_scope={body.get('in_scope')} sources={len(body.get('sources',[]))}")
                        ans = str(body.get("answer_text", ""))[:180].replace("\n"," ")
                        P(f"  answer[:180]: {ans}")
                    elif "quiz/generate" in path:
                        qs = body.get("questions", [])
                        P(f"  q_count={len(qs)} types={[q.get('qtype') for q in qs]}")
                        if qs:
                            P(f"  first_q[:100]: {str(qs[0].get('question_text',''))[:100]}")
                            P(f"  citation[:140]: {str(qs[0].get('citation_summary',''))[:140]}")
                    elif "is-new" in path:
                        P(f"  {body}")
                    elif "audio/tts" in path:
                        P(f"  content-type={r.headers.get('content-type')} bytes={len(r.content)}")
                except Exception as je:
                    P(f"  JSON parse fail: {je}; text[:200]: {r.text[:200]}")
            except Exception as ex:
                P(f"  REQ FAIL: {ex}")
                import traceback
                P(traceback.format_exc())

import asyncio
asyncio.run(run())

P("\n--- Simulated study (no-HTTP) ---")
try:
    from app.services import evaluation as ev
    sim = ev.run_simulated_study(subject="Operating Systems")
    P(f"profiles: {sim.get('num_profiles')}")
    P(f"avg_mastery_gain: {sim.get('avg_mastery_gain')}")
    P(f"question_repetition_rate: {sim.get('question_repetition_rate')}")
    P(f"per_profile_results: {len(sim.get('per_profile_results',[]))}")
except Exception as e:
    P(f"Simulated study FAIL: {e}")
    import traceback
    P(traceback.format_exc())

P("\n--- RAGAS eval on team gold set ---")
try:
    from app.evaluation import test_set
    rag = ev.run_rag_eval("smoke-gold-set", test_set.OS_GOLD_SET, "Operating Systems")
    P(f"run_id: {rag.get('run_id')}")
    P(f"summary: {rag.get('summary')}")
except Exception as e:
    P(f"RAGAS FAIL: {e}")
    import traceback
    P(traceback.format_exc())

LOG.write_text("\n".join(lines))
print(f"\nLOG: {LOG}")
