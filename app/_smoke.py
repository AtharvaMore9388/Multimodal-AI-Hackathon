import sys
print("PYTHON:", sys.executable)

modules_ok = []
modules_fail = []

def _chk(name, imp=None):
    try:
        m = __import__(imp or name)
        modules_ok.append(name)
        print(f"OK: {name} -> {getattr(m, '__version__', 'n/a')}")
    except Exception as e:
        modules_fail.append((name, str(e)))
        print(f"FAIL: {name} -> {e}")

_chk("fastapi")
_chk("uvicorn")
_chk("pydantic")
_chk("dotenv", "dotenv")
_chk("python-multipart", "multipart")
_chk("httpx")
_chk("pytest")
_chk("sqlalchemy")
_chk("chromadb")
_chk("sentence_transformers")
_chk("pypdf")
_chk("pdfplumber")
_chk("pptx", "pptx")

print("\nImport main app:")
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
print(f"Adding to sys.path:", ROOT)
try:
    from app.main import app
    print("OK: main app imported successfully")
    print("Routes:", [r.path for r in app.routes][:10])
    modules_ok.append("app.main")
except Exception as e:
    import traceback
    modules_fail.append(("app.main", str(e)))
    print("FAIL app.main:", traceback.format_exc())

print(f"\n--- OK: {len(modules_ok)} | FAIL: {len(modules_fail)} ---")
for n, err in modules_fail:
    print(f"  FAIL {n}: {err[:120]}")

print("\nRun /health via TestClient:")
try:
    from fastapi.testclient import TestClient
    from app.main import app as a2
    c = TestClient(a2)
    resp = c.get("/health")
    print(f"/health status={resp.status_code} body={resp.json()}")
    modules_ok.append("testclient_health")

    resp2 = c.get("/topics/graph")
    print(f"/topics/graph status={resp2.status_code} keys={list(resp2.json())}")
    modules_ok.append("testclient_topics_graph")
except Exception as e:
    import traceback
    print("TEST FAIL:", traceback.format_exc())

sys.exit(0 if len(modules_fail) <= 2 else 1)
