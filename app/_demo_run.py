import sys, os
sys.path.insert(0, os.getcwd())
import httpx

BASE = "http://127.0.0.1:8000"
EMAIL = "hackathon_judge@demo.dev"

print("=" * 60)
print("STUDYBUDDY HACKATHON DEMO - ENDPOINT WORKFLOW")
print("=" * 60)

def hit(step, url, method="GET", json_data=None, params=None):
    try:
        with httpx.Client(timeout=30) as c:
            if method == "POST":
                r = c.post(BASE + url, json=json_data, params=params)
            else:
                r = c.get(BASE + url, params=params)
        print(f"[{r.status_code}] {step}: {method} {url}")
        if r.status_code != 200:
            print("  err:", (r.text or "")[:200])
            return None
        return r.json()
    except Exception as e:
        print(f"[EXC] {step}:", e)
        return None

# 1
h = hit("1.Health", "/health")
if h:
    print("  ->", h.get("status"), h.get("service"))

# 2
t = hit("2.Topics graph", "/topics/graph", params={"subject": "Operating Systems"})
if t:
    print("  -> nodes:", len(t.get("nodes", [])), " edges:", len(t.get("edges", [])))

# 3 INGEST multipart
try:
    ingest_text = (
        "Paging: logical memory divided into fixed-size pages mapped to physical frames.\n"
        "Page Table: translates logical page numbers to physical frame addresses.\n"
        "Page Fault: MMU interrupt when page not resident; triggers disk swap-in.\n"
        "Segmentation: variable-sized logical segments with base/bounds registers.\n"
        "TLB: Translation Lookaside Buffer caches page table entries for fast lookup.\n"
    )
    files = {"file": ("os_memory.pdf", ingest_text.encode("utf-8"), "application/pdf")}
    data = {"user_email": EMAIL, "subject": "Operating Systems", "title": "OS Memory Management"}
    with httpx.Client(timeout=45) as c:
        r = c.post(BASE + "/ingest/upload", files=files, data=data)
    print(f"[{r.status_code}] 3.Ingest upload POST /ingest/upload")
    if r.status_code == 200:
        ing = r.json()
        print("  -> doc_id:", ing.get("document_id"))
        print("  -> topics detected:", len(ing.get("topics", [])))
        print("  -> concepts detected:", len(ing.get("concepts", [])))
        print("  -> chunks ingested:", ing.get("chunks", 0))
    else:
        print("  body:", (r.text or "")[:200])
except Exception as e:
    print(f"[EXC] 3.Ingest upload:", e)

# 4 CHAT source-backed
r = hit("4.Chat (page table)", "/chat/ask", "POST",
        json={"user_email": EMAIL, "question": "What is a page table and how does it work?"})
if r:
    print("  -> scope_label:", r.get("scope_label"))
    print("  -> in_scope:", r.get("in_scope"))
    print("  -> sources count:", len(r.get("sources") or []))
    ans = (r.get("answer") or "")[:140].replace("\n", " ")
    print("  -> answer snippet:", ans, "...")

# 5 CHAT unsourced
r = hit("5.Chat (FIFA off-topic)", "/chat/ask", "POST",
        json={"user_email": EMAIL, "question": "Who won FIFA World Cup 2022?"})
if r:
    print("  -> scope_label:", r.get("scope_label"))
    print("  -> in_scope:", r.get("in_scope"))
    print("  -> scope_reason:", r.get("scope_reason"))

# 6 QUIZ generate
q_gen = hit("6.Quiz generate", "/quiz/generate", "POST",
            json={"user_email": EMAIL, "subject": "Operating Systems", "count": 5,
                  "difficulty": "medium", "qtypes": ["mcq", "short", "numerical"]})
if q_gen:
    qs = q_gen.get("questions") or []
    print("  -> questions:", len(qs))
    print("  -> types:", sorted(set(q.get("type") for q in qs)))

    # 7 grade first
    if qs:
        q0 = qs[0]
        if q0.get("type") == "mcq":
            chosen = (q0.get("options") or ["A"])[0]
        else:
            chosen = "demo answer"
        r2 = hit("7.Quiz grade", "/quiz/grade", "POST",
                 json={"user_email": EMAIL, "question_id": q0["question_id"],
                       "user_answer": chosen})
        if r2:
            print("  -> is_correct:", r2.get("is_correct"),
                  " mastery_new:", r2.get("mastery_new"))

# 8 diagnostic
r = hit("8.Diagnostic quiz", "/quiz/diagnostic", "POST",
        json={"user_email": EMAIL, "subject": "Operating Systems"})
if r:
    print("  -> diagnostic questions:", len(r.get("questions") or []))

# 9 onboarding
r = hit("9.Onboarding", "/learner/complete-onboarding", "POST",
        json={"user_email": EMAIL, "subjects_of_interest": ["Operating Systems"],
              "current_level": "average", "goal": "Ace OS final exam"})
if r:
    print("  -> next_step:", (r.get("next_step") or "")[:60])

# 10 study schedule
r = hit("10.Study schedule (14d)", "/learner/study-schedule", "GET",
        params={"user_email": EMAIL, "days": 14, "subject": "Operating Systems"})
if r:
    print("  -> days:", len(r.get("days") or []))
    d = (r.get("days") or [{}])[0]
    print("  -> day1 slots:", len(d.get("slots") or []), " summary:", d.get("focus_summary"))

# 11 sim study
r = hit("11.Simulated study", "/evaluation/simulate-study", "POST",
        json={"subject": "Operating Systems", "sessions": 3,
              "profiles": ["beginner", "average", "advanced"]})
if r:
    print("  -> avg_mastery_gain:", r.get("avg_mastery_gain"))
    print("  -> repetition_rate:", r.get("repetition_rate"))
    print("  -> avg_accuracy:", r.get("avg_accuracy"))

# 12 eval runs
r = hit("12.Eval runs list", "/evaluation/runs")
if r:
    print("  -> runs:", len(r.get("runs") or []))

# 13 audio TTS
r = hit("13.Audio TTS fallback", "/audio/tts", "POST",
        json={"text": "Welcome to StudyBuddy.", "language": "en", "voice": "female"})
if r:
    has_audio = bool(r.get("audio_url") or r.get("audio_base64"))
    has_fb = bool(r.get("fallback_text"))
    print("  -> audio:", has_audio, " fallback_text:", has_fb)

# 14 is-new
r = hit("14.Is new student", "/learner/is-new", "GET",
        params={"user_email": EMAIL + ".fresh99"})
if r:
    print("  -> is_new:", r.get("is_new"))

print()
print("=" * 60)
print("HACKATHON DEMO COMPLETE — server at http://127.0.0.1:8000")
print("Swagger docs: http://127.0.0.1:8000/docs")
print("=" * 60)
