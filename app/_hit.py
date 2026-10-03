import sys
import traceback
from pathlib import Path

LOG = Path(__file__).resolve().parent / "_hit_output.log"
f = open(LOG, "w")
_w = f.write

_w(f"PYTHON: {sys.executable}\n")

try:
    import httpx
    _w("httpx OK\n")
except Exception as e:
    _w(f"httpx FAIL: {e}\n")
    f.close()
    sys.exit(1)

urls = [
    "http://127.0.0.1:8000/health",
    "http://127.0.0.1:8000/",
    "http://127.0.0.1:8000/topics/graph",
]

try:
    with httpx.Client(timeout=5.0) as client:
        for url in urls:
            try:
                r = client.get(url)
                _w(f"GET {url} -> {r.status_code}\n")
                try:
                    body = r.json()
                    if url.endswith("/health"):
                        _w(f"  health body: {body}\n")
                    elif url.endswith("/graph"):
                        _w(f"  graph nodes: {len(body.get('nodes',[]))} edges: {len(body.get('edges',[]))}\n")
                    else:
                        _w(f"  keys: {list(body.keys())[:10]}\n")
                except Exception as je:
                    _w(f"  json parse error: {je}\n")
            except Exception as e:
                _w(f"GET {url} ERROR: {e}\n")
except Exception as e:
    _w(f"HTTP client error: {e}\n")
    traceback.print_exc(file=f)

_w("\n--- Chat test ---\n")
try:
    with httpx.Client(timeout=15.0) as client:
        r = client.post("http://127.0.0.1:8000/chat/ask", json={
            "question": "What is a page table?",
            "subject": "Operating Systems",
            "user_email": "demo@study.dev",
        })
        _w(f"chat status: {r.status_code}\n")
        if r.status_code == 200:
            d = r.json()
            _w(f"  scope_label: {d.get('scope_label')}\n")
            _w(f"  in_scope: {d.get('in_scope')}\n")
            _w(f"  sources count: {len(d.get('sources',[]))}\n")
            _w(f"  answer[:200]: {str(d.get('answer_text',''))[:200]}\n")
        else:
            _w(f"  response text[:500]: {r.text[:500]}\n")
except Exception as e:
    _w(f"chat ERROR: {e}\n")
    traceback.print_exc(file=f)

_w("\n--- Quiz generate test ---\n")
try:
    with httpx.Client(timeout=15.0) as client:
        r = client.post("http://127.0.0.1:8000/quiz/generate", json={
            "subject": "Operating Systems",
            "topic": "os_paging",
            "count": 5,
            "difficulty": "medium",
            "qtypes": ["mcq", "short", "numerical"],
            "user_email": "demo@study.dev",
        })
        _w(f"quiz status: {r.status_code}\n")
        if r.status_code == 200:
            d = r.json()
            qs = d.get("questions", [])
            _w(f"  questions count: {len(qs)}\n")
            _w(f"  types: {[q.get('qtype') for q in qs]}\n")
        else:
            _w(f"  response[:500]: {r.text[:500]}\n")
except Exception as e:
    _w(f"quiz ERROR: {e}\n")
    traceback.print_exc(file=f)

f.close()
print(f"LOG WRITTEN TO {LOG}")
