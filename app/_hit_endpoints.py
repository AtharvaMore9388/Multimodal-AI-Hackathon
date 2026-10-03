import asyncio
import httpx

URLS = [
    "http://127.0.0.1:8000/health",
    "http://127.0.0.1:8000/",
    "http://127.0.0.1:8000/topics/graph",
]

async def main():
    async with httpx.AsyncClient(timeout=10.0) as client:
        for url in URLS:
            try:
                r = await client.get(url)
                print(f"GET {url}")
                print(f"  status: {r.status_code}")
                body = r.json()
                if isinstance(body, dict):
                    keys = list(body.keys())[:10]
                    print(f"  keys: {keys}")
                    if url.endswith("/health"):
                        print(f"  body: {body}")
                    if url.endswith("/graph"):
                        print(f"  nodes: {len(body.get('nodes',[]))} edges: {len(body.get('edges',[]))}")
                print()
            except Exception as e:
                print(f"GET {url} -> ERROR: {e}\n")

asyncio.run(main())

print("--- Chat test (scope-supported question) ---")
try:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import httpx as hx
    resp = hx.post("http://127.0.0.1:8000/chat/ask", json={
        "question": "What is a page table?",
        "subject": "Operating Systems",
        "user_email": "demo@study.dev",
        "lang": "en",
    }, timeout=15.0)
    print(f"status: {resp.status_code}")
    data = resp.json()
    print(f"scope_label: {data.get('scope_label')}")
    print(f"in_scope: {data.get('in_scope')}")
    print(f"sources: {len(data.get('sources',[]))}")
    print(f"answer[:300]: {str(data.get('answer_text',''))[:300]}")
except Exception as e:
    print(f"chat ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n--- Chat test (UNSOURCED off-topic question) ---")
try:
    import httpx as hx2
    resp = hx2.post("http://127.0.0.1:8000/chat/ask", json={
        "question": "Who won the FIFA World Cup 2022?",
        "subject": "Operating Systems",
        "user_email": "demo@study.dev",
    }, timeout=15.0)
    print(f"status: {resp.status_code}")
    data = resp.json()
    print(f"scope_label: {data.get('scope_label')}")
    print(f"in_scope: {data.get('in_scope')}")
except Exception as e:
    print(f"chat unsourced ERROR: {e}")

print("\n--- Quiz generate test ---")
try:
    import httpx as hx3
    resp = hx3.post("http://127.0.0.1:8000/quiz/generate", json={
        "subject": "Operating Systems",
        "topic": "Paging",
        "count": 5,
        "difficulty": "medium",
        "qtypes": ["mcq", "short", "numerical"],
        "user_email": "demo@study.dev",
    }, timeout=15.0)
    print(f"status: {resp.status_code}")
    data = resp.json()
    qs = data.get("questions", [])
    print(f"questions generated: {len(qs)}")
    types = [q.get("qtype") for q in qs]
    print(f"qtypes: {types}")
    if qs:
        print(f"first qid: {qs[0].get('qid')}")
        print(f"first citation_summary[:120]: {str(qs[0].get('citation_summary',''))[:120]}")
except Exception as e:
    print(f"quiz generate ERROR: {e}")
    import traceback
    traceback.print_exc()
