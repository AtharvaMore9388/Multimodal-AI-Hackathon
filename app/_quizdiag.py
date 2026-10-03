import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

LOG = Path("_quizdiag.log")
LOG.write_text("start\n")

try:
    from app.core import storage
    LOG.write_text(LOG.read_text() + "storage imported\n")
    storage.DB_PATH = ROOT.parent.parent / "app" / "study_buddy.db" if False else (Path(__file__).resolve().parent / "study_buddy.db")
    LOG.write_text(LOG.read_text() + f"DB: {storage.DB_PATH}\n")
    storage.init_db()
    LOG.write_text(LOG.read_text() + "DB init called OK\n")
    topics = storage.list_topics("Operating Systems")
    LOG.write_text(LOG.read_text() + f"topics count: {len(topics)}\n")
    for t in topics[:3]:
        LOG.write_text(LOG.read_text() + f"  {t['topic_id']} {t['name']} concepts={len(t.get('concepts',[]))}\n")
except Exception as e:
    import traceback
    LOG.write_text(LOG.read_text() + f"storage FAIL: {e}\n{traceback.format_exc()}\n")
    sys.exit(1)

try:
    from app.services import quiz as quiz_svc
    LOG.write_text(LOG.read_text() + "quiz svc imported\n")
    qs = quiz_svc.generate_questions(
        subject="Operating Systems", topic="os_paging", count=3,
        difficulty="medium", qtypes=["mcq","short","numerical"],
        user_email="diag@x.y", mode="standard",
    )
    LOG.write_text(LOG.read_text() + f"generate returned {len(qs)} qs\n")
    for i, q in enumerate(qs):
        LOG.write_text(LOG.read_text() + f"  Q{i+1}: {q.get('qtype')} qid={q.get('qid','?')} q[:80]={str(q.get('question_text',''))[:80]}\n")
        LOG.write_text(LOG.read_text() + f"       correct={q.get('correct_answer','?')} citation[:100]={str(q.get('citation_summary',''))[:100]}\n")
    LOG.write_text(LOG.read_text() + "quiz OK\n")
except Exception as e:
    import traceback
    LOG.write_text(LOG.read_text() + f"quiz FAIL: {e}\n{traceback.format_exc()}\n")
    sys.exit(1)

try:
    from app.services import ingest as ingest_svc
    LOG.write_text(LOG.read_text() + "ingest svc imported\n")
    sample = b"Paging divides memory into pages and frames. Page Table translates pages to frames. Page Fault loads missing pages from disk. Deadlock has four conditions: Mutual Exclusion, Hold and Wait, No Preemption, Circular Wait. Banker's Algorithm avoids deadlock via safe state. Semaphores provide synchronization. Processes have PCBs; Threads share address space. Round Robin uses time quantums. SJF minimizes average waiting. Thrashing is fixed via Working Set. Mutex Lock is a binary semaphore. Counting Semaphore controls N resources. Logical Address comes from the CPU; Physical Address goes to RAM chips."
    result = ingest_svc.ingest_file("sample.txt", sample, subject="Operating Systems", user_email="diag@x.y")
    LOG.write_text(LOG.read_text() + f"ingest result: chunks={result.get('chunks_ingested')} topics={len(result.get('topics_detected',[]))} concepts={len(result.get('concepts_detected',[]))}\n")
except Exception as e:
    import traceback
    LOG.write_text(LOG.read_text() + f"ingest FAIL: {e}\n{traceback.format_exc()}\n")

try:
    from app.services import rag as rag_svc
    LOG.write_text(LOG.read_text() + "rag svc imported\n")
    r = rag_svc.ask("What is a page table?", subject="Operating Systems", user_email="diag@x.y")
    LOG.write_text(LOG.read_text() + f"chat scope_label={r.get('scope_label')} sources={len(r.get('sources',[]))} in_scope={r.get('in_scope')}\n")
    LOG.write_text(LOG.read_text() + f"answer[:250]: {str(r.get('answer_text',''))[:250]}\n")
    r2 = rag_svc.ask("FIFA winner 2022?", subject="Operating Systems")
    LOG.write_text(LOG.read_text() + f"chat unsourced scope_label={r2.get('scope_label')} in_scope={r2.get('in_scope')}\n")
except Exception as e:
    import traceback
    LOG.write_text(LOG.read_text() + f"rag FAIL: {e}\n{traceback.format_exc()}\n")

try:
    from app.services import evaluation as ev
    from app.evaluation import test_set
    LOG.write_text(LOG.read_text() + "evaluation imported\n")
    sim = ev.run_simulated_study("Operating Systems")
    LOG.write_text(LOG.read_text() + f"sim study profiles={sim.get('num_profiles')} gain={sim.get('avg_mastery_gain')} rep_rate={sim.get('question_repetition_rate')}\n")
    rag = ev.run_rag_eval("smoke-gold", test_set.OS_GOLD_SET, "Operating Systems")
    LOG.write_text(LOG.read_text() + f"ragas summary={rag.get('summary')}\n")
except Exception as e:
    import traceback
    LOG.write_text(LOG.read_text() + f"evaluation FAIL: {e}\n{traceback.format_exc()}\n")

LOG.write_text(LOG.read_text() + "ALL DONE\n")
