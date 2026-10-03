import sys
from pathlib import Path

LOG = Path("_diag.log")
LOG.write_text("START\n")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
LOG.write_text(LOG.read_text() + f"ROOT={ROOT}\n")

try:
    from app.main import app
    LOG.write_text(LOG.read_text() + "APP IMPORTED OK\n")
    LOG.write_text(LOG.read_text() + f"Routes count: {len(app.routes)}\n")
    routes = [r.path for r in app.routes]
    LOG.write_text(LOG.read_text() + f"Routes: {routes}\n")
except Exception as e:
    import traceback
    LOG.write_text(LOG.read_text() + f"APP FAIL: {e}\n{traceback.format_exc()}\n")
    sys.exit(1)

try:
    import httpx
    LOG.write_text(LOG.read_text() + f"httpx version: {httpx.__version__}\n")
    tport = httpx.ASGITransport(app=app)
    LOG.write_text(LOG.read_text() + "Transport OK\n")
except Exception as e:
    import traceback
    LOG.write_text(LOG.read_text() + f"Transport FAIL: {e}\n{traceback.format_exc()}\n")
    sys.exit(1)

import asyncio
async def main():
    async with httpx.AsyncClient(transport=tport, base_url="http://testserver") as client:
        r = await client.get("/health", timeout=30)
        LOG.write_text(LOG.read_text() + f"/health status: {r.status_code}\n")
        LOG.write_text(LOG.read_text() + f"/health body: {r.text[:500]}\n")
        r2 = await client.get("/topics/graph", timeout=30)
        LOG.write_text(LOG.read_text() + f"/graph status: {r2.status_code}\n")
        j = r2.json()
        LOG.write_text(LOG.read_text() + f"/graph nodes={len(j.get('nodes',[]))} edges={len(j.get('edges',[]))}\n")
        r3 = await client.post("/chat/ask", json={"question":"What is a page fault?","subject":"Operating Systems","user_email":"a@b.c"}, timeout=30)
        LOG.write_text(LOG.read_text() + f"/chat status: {r3.status_code}\n")
        j3 = r3.json()
        LOG.write_text(LOG.read_text() + f"  scope_label={j3.get('scope_label')}\n")
        LOG.write_text(LOG.read_text() + f"  in_scope={j3.get('in_scope')}\n")
        LOG.write_text(LOG.read_text() + f"  sources={len(j3.get('sources',[]))}\n")
        r4 = await client.post("/quiz/generate", json={"subject":"Operating Systems","topic":"os_paging","count":5,"qtypes":["mcq","short","numerical"],"user_email":"a@b.c"}, timeout=30)
        LOG.write_text(LOG.read_text() + f"/quiz status: {r4.status_code}\n")
        j4 = r4.json()
        qs = j4.get("questions",[])
        LOG.write_text(LOG.read_text() + f"  qs={len(qs)} types={[q.get('qtype') for q in qs]}\n")
asyncio.run(main())
LOG.write_text(LOG.read_text() + "ALL DONE\n")
