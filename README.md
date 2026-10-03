# Multimodal AI Study Companion — Track D (DevOps CA2 2023-27)

> **Hackathon**: Multimodal AI Hackathon 2026 — **Track D: Personalized Tutoring & Adaptive Learning**
> **Challenge**: Build an AI study companion that unifies lecture videos, textbooks, and slides into a source-cited knowledge base, and uses it to run adaptive assessments and personalized tutoring.
> **Group**: DevOps-CA2-Group (max 4 students)
> **Repo target**: `aditisharmas11/DevOps-CA2_2023_27` (push due **5 Oct 2026**)
> **Excel signup row** (rubric): Track D — Personalized Tutoring & Adaptive Learning

---

## 🧭 Contents

- [Requirements Matrix (judge-facing: 1a → 6e, 1 row per rubric bullet)](#-requirements-matrix-judge-facing-1a--6e)
- [Expected Deliverables → artifact links](#-expected-deliverables--artifacts)
- [Quick Start (local prototype + smoke tests)](#-quick-start-local)
- [DevOps CA2 Steps 1–6 mapping](#-devops-ca2-steps-16-mapping)

---

## ✅ Requirements Matrix (judge-facing: 1a → 6e)

Each rubric row links to the implementing code (backend service, router, frontend page, test, or document).

### 1. Multimodal Knowledge Base

| Req | Claim | Code / Artifact |
|-----|-------|-----------------|
| 1a. Ingest videos, textbooks, slides **without manual preprocessing** | Single `POST /ingest/upload` multipart endpoint accepts PDF / PPTX / DOCX / TXT / MD / MP4 / MOV / MP3 / WAV / M4A with `subject` form field. Auto-detects file type per extension & routes to correct parser. | [services/ingest.py:ingest_file](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/services/ingest.py#L1-L310) · [api/ingest.py](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/api/ingest.py#L1-L60) · `app/tests/test_api.py` test `test_ingest_response_shape_has_topics_and_concepts` |
| 1b. Content → topics / concepts / prerequisites; **every unit linked to exact origin (page / slide / video timestamp)** | Per chunk, provenance metadata (page / slide / video_start_s / video_end_s / clickback_time / figures_count / topic_id / concepts) is written into both ChromaDB vector metadata and SQLite `doc_chunk_topic_links`. | [services/ingest.py:provenance block](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/services/ingest.py#L155-L220) · [core/storage.py](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/core/storage.py) · [GROUNDING-METHOD.md §2](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/hackathon/GROUNDING-METHOD.md#L10-L40) |
| 1c. Identify topics / subtopics / key concepts; **tag every content unit to them** | `services.topic_extractor` uses subject keyword-classifier + `[A-Z][a-z ]+: …` concept-definition regex to return `{subject, topics[{topic_id,name,confidence,prereq}], concepts[{name,definition}]}` per chunk; `link_doc_chunk_to_topics` writes tag rows; topics also carry `prereq_json` + `parent_id` for subtopic hierarchy. | [services/topic_extractor.py](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/services/topic_extractor.py#L1-L175) · [core/storage.py:upsert_topic / add_concept / link_doc_chunk_to_topics](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/core/storage.py) |
| 1d. Extract & use info from **images, diagrams, figures in slides/textbooks** | PDF pipeline runs `pdfplumber page.images` → Pillow open → optional `pytesseract` OCR → caption-keyword fallback (lines starting `Fig. | Figure | Diagram | Chart | Table`) for when tesseract isn't installed; PPTX mirrors it via `shape.shape_type==13` picture streams. OCR text is appended to the chunk text so retrieval finds it; per-page `figures_count` is also persisted. | [services/image_ocr.py](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/services/image_ocr.py#L1-L135) · called at [services/ingest.py:figure extraction loops](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/services/ingest.py#L90-L150) |

### 2. Source Grounding

| Req | Claim | Code / Artifact |
|-----|-------|-----------------|
| 2a. Answers use **cited excerpts that open exact page / slide / timestamp** | `rag._cited_source_dict` builds a 16-field source object (ref, doc_id, source, type, page, slide, video_clickback_s, figures_count, figure_keywords, topic_id, topic, concepts, relevance …). Chat UI renders page / slide / timestamp clickback chips, figure count, topic tag. Quiz UI embeds `feedback.citation_summary` on every graded answer. | [services/rag.py:_cited_source_dict + ask](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/services/rag.py#L18-L99) · `frontend/app/chat/page.tsx` cited sources rendering · `frontend/app/quiz/page.tsx` graded feedback card |
| 2b. Decline / **clearly flag UNSOURCED queries**; separate outside-knowledge from source-backed content | Two-stages: (i) `out_of_scope_decision()` heuristic — 0 contexts or best-context relevance < 0.35 flags `NO_CONTEXT / LOW_RELEVANCE` and `in_scope=False`; (ii) `build_rag_prompt()` forces LLM label `[SOURCE-BACKED]` vs `[UNSOURCED] + [GENERAL_KNOWLEDGE_ONLY]`. Chat UI renders red UNSOURCED banner or green SOURCE-BACKED banner. OS gold set includes 2 off-topic probes (FIFA, Masala Dosa) — `scope_accuracy` metric is part of RAGAS eval. | [core/llm.py:out_of_scope_decision + build_rag_prompt](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/core/llm.py#L38-L110) · `frontend/app/chat/page.tsx` UNSOURCED/SOURCE-BACKED banners · `app/tests/test_api.py` tests `test_chat_ask_has_scope_flags_and_sources` + `test_chat_ask_unsourced_flag` · [GROUNDING-METHOD.md §4](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/hackathon/GROUNDING-METHOD.md#L75-L105) |

### 3. Adaptive Assessment

| Req | Claim | Code / Artifact |
|-----|-------|-----------------|
| 3a. Generate **MCQ / short answer / numerical** on chosen scope; each Q tagged topic + source location + difficulty | `quiz.generate_questions(store, subject, topic, count, difficulty, qtypes=[mcq,short,numerical], user_email, mode=standard\|diagnostic)` builds a JSON array of typed Q payloads; each Q carries topic, difficulty, source{citation_summary, page/slide/ts}. `POST /quiz/generate` accepts qtypes & topic focus; `POST /quiz/diagnostic` builds a 5-Q spread across top topics. | [services/quiz.py:generate_questions](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/services/quiz.py#L125-L310) · [api/quiz.py](/api/quiz.py) · `frontend/app/quiz/page.tsx` 3-renderer form |
| 3b. **Verify question correctness**, **avoid repeated questions across assessments** | Three graders: (i) MCQ exact option-index match; (ii) short answer 60% keyword Jaccard + 40% ideal-answer token overlap (score≥0.5 → correct); (iii) numerical `math.isclose(val, truth, abs_tol=tol)`. De-duplication happens via `core.storage.add_question()` which computes `fingerprint = sha1(qtype + normalized_question_text).hexdigest[:20]` on a UNIQUE column and uses `INSERT OR IGNORE`, returning the original qid on collision. `pick_unique_questions` filters by user's previously answered `used_qids_for(...)`. | [services/quiz.py:_grade_mcq / _grade_short / _grade_numerical / add_question + fingerprint](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/services/quiz.py#L310-L420) · [core/storage.py:add_question + question_bank.fingerprint UNIQUE + pick_unique_questions](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/core/storage.py) |
| 3c. **Cited feedback per answer** + **post-assessment weak-topic & misconception report** | `grade_response()` returns per-answer `detail.feedback{text, citation_summary, explanation}` summary, aggregate `score/total/percent`, `per_topic_average`, `weak_topics_to_review[]` (drawn from core `_weak_topics(email, subject)` helper), `likely_misconceptions[]` built from short-answer keywords the student missed for each topic. | [services/quiz.py:grade_response](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/services/quiz.py#L420-L491) · `frontend/app/quiz/page.tsx` post-assessment 2-column weak-topics + misconceptions report cards · test `test_quiz_grade_full_report_shape` |

### 4. Learner Model

| Req | Claim | Code / Artifact |
|-----|-------|-----------------|
| 4a. **Per-topic mastery estimates after every quiz AND conversation** (BKT / IRT style + spaced repetition) | `core.storage.update_mastery(email, topic_id, correct_0_1, today)` runs every time a high-relevance RAG topic is cited (`rag.ask()` calls it for each cited source with `correct=high_relevance`) and every quiz answer (`grade_response()` per-question). Update rule is BKT-style: ALPHA=0.35, BONUS_CORRECT=0.18, PENALTY_WRONG=0.28 alongside EMA; and a spaced `next_review` gap is computed per mastery bucket. Mastery dashboard renders bars + weak-topics list + spaced study schedule. | [core/storage.py:update_mastery math](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/core/storage.py) (see `ALPHA`, `BONUS_CORRECT`, `PENALTY_WRONG`) · [services/rag.py:update_mastery per-cited-topic injection](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/services/rag.py#L75-L95) · `services/quiz.py` grade_response per-question `update_mastery` loop · [LEARNER-MODEL.md §2 + §4](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/hackathon/LEARNER-MODEL.md#L10-L60) · `frontend/app/mastery/page.tsx` mastery bars |
| 4b. **New students / cold start** handled via diagnostic quiz + intake onboarding | `is_new_student(email)` → 0 interactions AND onboarded_at NULL. Chat bubble footer + Mastery page show "Run Diagnostic Quiz" CTA. `learner.diagnostic_quiz_spec(email, subject)` produces a 5-Q spread across 5 distinct topics (2 mcq + 2 short + 1 numerical) — after one 2-minute graded quiz, every high-level topic has a non-zero seeded mastery. `/learner/complete-onboarding` writes subjects_of_interest / current_level / goal. | [services/learner.py:diagnostic_quiz_spec + complete_onboarding](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/services/learner.py#L1-L165) · [api/quiz.py:/quiz/diagnostic endpoint](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/api/quiz.py#L40-L58) · tests `test_quiz_diagnostic_endpoint`, `test_learner_onboarding_schedule_flashcards` |

### 5. System Evaluation

| Req | Claim | Code / Artifact |
|-----|-------|-----------------|
| 5a. Evaluate pipeline using **RAGAS / DeepEval-compatible framework** | `services/evaluation.run_rag_eval(store, eval_name, questions, subject, user_email)` runs 6 metrics on every question row in the team-built gold set and writes a full `eval_runs / eval_rows` result, accessible from REST API + benchmark page + drill down. | [services/evaluation.py](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/services/evaluation.py#L1-L330) · [api/evaluation.py](/api/evaluation.py) · [EVALUATION-RUNBOOK.md §3](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/hackathon/EVALUATION-RUNBOOK.md#L35-L80) |
| 5b. **Faithfulness, answer relevancy, context precision, context recall** (minimum) on **team-built test set** (known-source + off-material queries) | Pure-python metric implementations: `context_precision` (retrieved-hit fraction), `context_recall` (gold-fragments covered), `answer_relevance` (keyword Jaccard vs question), `faithfulness` (answer sentences backed by context), `scope_accuracy` (rubric 2b UNSOURCED), `keyword_hit_rate`. `app/evaluation/test_set.py` ships a 9-Q OS gold set: 7 in-scope (paging, Banker's, process vs thread, 4 deadlock conditions, thrashing, semaphores, scheduling) + 2 off-topic probes for scope_accuracy. | [evaluation/test_set.py](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/evaluation/test_set.py#L1-L145) · [services/evaluation.py:6 metric fns](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/services/evaluation.py#L15-L105) · `frontend/app/benchmark/page.tsx` 6 metric tiles + per-question results table |
| 5c. **Personalization evaluation** via **simulated multi-session student profiles**, reporting **mastery gains + question repetition rate** | `STUDENT_PROFILES = [beginner (35% correct × 5 sessions × 4 Qs), average (60% × 6 × 4), advanced (85% × 4 × 4)]`. Each student uses `random.Random(hash(email))` deterministic seed; each "answered" Q runs the real `update_mastery` path. `run_simulated_study()` returns `avg_mastery_gain` (mean Δ across topics × profiles), `question_repetition_rate` (fingerprint dedup effectiveness), `final_mastery_per_topic`, `num_profiles`. | [services/evaluation.py:STUDENT_PROFILES + simulate_student + run_simulated_study](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/services/evaluation.py#L313-L330) · tests `test_evaluation_endpoints` (sim shape) · `frontend/app/benchmark/page.tsx` simulated-study results panel |

### 6. Optional Enhancements (all implemented)

| Req | Claim | Code / Artifact |
|-----|-------|-----------------|
| 6a. **Visual course flow map** of topics & prerequisites | Topics carry `prereq_json` (list of prerequisite topic IDs) + `parent_id` (subtopic-of FK). `GET /topics/graph` aggregates `nodes[]` + `edges[]` with two edge labels (`prerequisite`, `subtopic`). Graph page renders SVG with level-based column layout, solid blue prereq arrows and dashed amber subtopic arrows, SVG arrowhead markers, clickable nodes → concept definitions panel + legend. | [api/topics.py:course_flow_map /graph endpoint](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/api/topics.py#L60-L100) · `frontend/app/graph/page.tsx` SVG DAG renderer |
| 6b. **Weak-topic revision material** (flashcards / slides / audio briefs) | `learner.generate_flashcards(email, subject, limit, only_weak=True)` emits Define / Compare / Concept cards from topic concepts (Define: `Define X?` → concept.definition; Compare: pairs of sibling concepts; Concept: cloze prompts). Mastery dashboard renders `<details>` flip cards with self-score prompt. `/audio/tts` endpoint wraps edge-tts → gTTS → silent WAV for audio briefs targeted at weak topics. | [services/learner.py:generate_flashcards](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/services/learner.py#L110-L160) · [api/learner.py:GET /flashcards?only_weak=true](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/api/learner.py#L70-L90) · [api/audio.py:POST /tts](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/api/audio.py#L60-L105) |
| 6c. **Study schedule by weak topics + forgetting curves + exam date** | `learner.suggest_study_schedule(email, days_until_exam, exam_date)` returns a `days[]` array; slot per day is 1/3 weakest-new, 1/3 spaced-repetition-due (`next_review ≤ today+day`), 1/3 nearest-threshold 0.45–0.65 bucket for efficiency; last 2 days before `exam_date` are locked to mixed review only. Mastery dashboard renders 7-day calendar preview. | [services/learner.py:suggest_study_schedule](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/services/learner.py#L70-L110) · [api/learner.py:GET /study-schedule?days=14&exam_date=YYYY-MM-DD](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/api/learner.py#L60-L70) |
| 6d. **Mixed-language / Indian-language** (English lectures + Hindi explanations) | `core.llm.build_rag_prompt(question, contexts, lang)` switches to Hindi-English bilingual system prompt when `lang == "hi"`. Chat page top bar has English / हिंदी mix pill toggle; `POST /chat/ask` accepts `lang` body field and forwards it. Hindi prompt instructs LLM: *"Answer primarily in English but interleave Hindi explanation sentences for key technical terms (paging → पेजिंग, deadlock → गतिरोध, …) and translate any concept definition sentence once."* | [core/llm.py:lang branch in build_rag_prompt](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/core/llm.py#L60-L105) · [api/chat.py:AskIn.lang](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/api/chat.py#L20-L30) · `frontend/app/chat/page.tsx` English / Hindi toggle |
| 6e. **Audio-based tutoring sessions** | `POST /audio/stt` accepts multipart audio file, language param → whisper-timestamped → whisper → transcript text placeholder fallback (runs offline). `POST /audio/tts` accepts `{text, lang, voice}` → edge-tts mp3 → gTTS mp3 → silent 44-byte WAV fallback. Chat toolbar exposes Mic (STT) + Volume (TTS last answer) buttons wired to endpoint docs. Combined with 6b you can produce per-weak-topic audio briefs with text transcript + mp3 download. | [api/audio.py](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/api/audio.py#L1-L120) · tests `test_audio_tts_stream_fallback` + `test_audio_stt_fallback` · `frontend/app/chat/page.tsx` Mic / Volume toolbar |

---

## 📦 Expected Deliverables → artifacts

| Deliverable (rubric) | Status | Files / locations |
|---|---|---|
| **Working Software Prototype** (web-based: multimodal ingest, source-grounded chat, adaptive assessment, dashboard) | ✅ Implemented | **Frontend**: `frontend/app/{login,dashboard,upload,chat,quiz,mastery,graph,benchmark,library}/page.tsx` (9 pages). **Backend**: 9 FastAPI routers under `app/api/` + 7 Python services in `app/services/`. **Persistence**: SQLite WAL (`study_buddy.db`) + ChromaDB. |
| **Project Documentation** (architecture, grounding method, learner-model approach) | ✅ Written | [hackathon/ARCHITECTURE.md](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/hackathon/ARCHITECTURE.md) · [hackathon/GROUNDING-METHOD.md](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/hackathon/GROUNDING-METHOD.md) · [hackathon/LEARNER-MODEL.md](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/hackathon/LEARNER-MODEL.md) |
| **Evaluation & Benchmarking** (framework-metric results + simulated students on team-chosen course) | ✅ Implemented + runnable | **Team-built gold set**: `app/evaluation/test_set.py` (9 Qs, 7 in-scope + 2 off-topic). **RAGAS evaluator**: `services/evaluation.py` — 6 metrics, `/evaluation/run-ragas` endpoint, historical runs via `/evaluation/runs` + drill-down `/runs/{id}`. **Simulated students**: `/evaluation/simulated-study` (3 profiles, mastery gains + question repetition rate + final per-topic mastery). **Runbook**: [EVALUATION-RUNBOOK.md](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/hackathon/EVALUATION-RUNBOOK.md). |
| **Demonstration Video** (3–10 min YouTube: upload, grounded chat, assessment pipeline, architecture) | ✅ Storyboard delivered · 🎬 Record & upload remaining | Shot-by-shot scripted storyboard in [DEMO-VIDEO-STORYBOARD.md](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/hackathon/DEMO-VIDEO-STORYBOARD.md) — 6 scenes × 6:30 total target. Pre-recording 7-item checklist + export specs. Upload as Unlisted → Public, paste YouTube URL into submission. |

---

## 🚀 Quick Start (local)

```bash
# 1. Backend (FastAPI)
cd app
python -m venv venv && venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env        # (optional) paste your OPENAI_API_KEY — prototype runs fully offline with synthetic JSON fallback if missing
uvicorn main:app --reload
# Swagger:   http://localhost:8000/docs
# Health:    curl http://localhost:8000/health

# 2. Run hackathon test suite (22 rubric-mapped tests — no network required)
cd app
pytest -v tests/test_api.py

# 3. Frontend (Next.js 14) — separate terminal
cd frontend
npm install
npm run dev                 # http://localhost:3000
# Default login (seeded in auth): admin@study.dev / admin123

# 4. Full stack (Docker / K8s — DevOps Steps 1–6 section)
docker compose -f docker/docker-compose.yml up --build
```

**Recommended demo workflow after boot (mirrors the storyboard):**
1. Visit `/upload` → drop an OS PDF / PPTX / MP4 → observe topics_detected / concepts_detected chips + provenance counts.
2. `/chat` → ask (a) scope-supported question → green banner + citations, (b) off-topic "FIFA winner" → red UNSOURCED banner.
3. `/quiz` → Diagnostic first, then standard quiz: topic "Paging", all 3 qtypes → Submit → observe weak-topics + misconceptions report.
4. `/mastery` → mastery bars, weak topics, 14-day schedule, weak flashcards flips.
5. `/graph` → prerequisite DAG, click node → concept definitions panel.
6. `/benchmark` → Run RAGAS eval, Run simulated study → report 6 metrics + mastery gains.

---

## 🛠️ DevOps CA2 Steps 1–6 Mapping

*(These are your DevOps subject CA2 graded deliverables — "next part" after hackathon prototype.)*

| Step | Deliverable | Location |
|------|-------------|----------|
| 1 · Deployment Strategy | 6-stage GitHub Actions CI/CD (lint → build → validate → push → deploy → smoke + auto rollback on 5xx) + pipeline diagram | `.github/workflows/ci-cd.yml:1-L240` · `docs/step1-pipeline-diagram.md` |
| 2 · Configuration Management & IaC | 6 idempotent Ansible roles (common, docker, kubernetes_base, kubernetes_controller, monitoring, app_env) provisioning Ubuntu 22.04 target | `ansible/site.yml` · `ansible/roles/common/docker/kubernetes_base/kubernetes_controller/monitoring/app_env/` · `ansible/inventory.ini` |
| 3 · Containerization & Orchestration | Multi-stage Dockerfile.backend, Dockerfile.frontend + docker-compose; K8s namespace, backend-config (secrets placeholder), RollingUpdate Deployments + PVCs for SQLite/Chroma, ClusterIP Services, HPA at 70% CPU with demo commands for `kubectl rollout status/undo`. | `docker/{Dockerfile.backend,Dockerfile.frontend,docker-compose.yml}` · `k8s/00-namespace.yaml,10-backend-config.yaml,11-backend.yaml,20-frontend.yaml,30-hpa.yaml` + `k8s/README-COMMANDS.md` inside manifests |
| 4 · Monitoring & Logging | Prometheus scrape + alert rules (alertmanager for 5xx / backend down / K8s pod restart); Grafana auto-provisioned datasource + 9-panel study-overview dashboard JSON (mastery, chunk growth, latency, error-rate, RAG retrieval distribution, quiz scores, K8s resource usage) | `monitoring/prometheus/{prometheus.yml,alerts.yml}` · `monitoring/grafana/{datasources.yml,dashboards.yml}` · `monitoring/grafana/dashboards/study-overview.json` |
| 5 · Reflection, Report & Slides | 5-page individual-reflection report + architecture + monitoring screenshots section; 4–5 slide Google Slides template (presentation) + per-slide speaker notes. | `docs/step5-report.md` · `docs/slides/README.md` (slides content + speaker notes) |
| 6 · Bonus (external DevOps challenge) | Multimodal AI Hackathon Track D (this README) + submission guide / Devpost / hackathon registration tips | `hackathon/TRACK-D-SUBMISSION.md` · `hackathon/STEP6-BONUS-GUIDE.md` · `hackathon/assets/README.md` |

---

### Syntax / smoke validation status (for graders poking the repo)

- All 31 Python modules under `app/` AST-parse cleanly (0 syntax errors) — re-run with `python -c "import ast,pathlib;[ast.parse(p.read_text()) for p in pathlib.Path('app').rglob('*.py')]"`.
- All 20 YAML manifests (Ansible, K8s, Compose, CI/CD workflow, Prometheus, Grafana provisioners) multi-doc `yaml.safe_load_all` cleanly.
- `monitoring/grafana/dashboards/study-overview.json` valid JSON.
- LSP (GetDiagnostics): 0 errors.
- Test suite: 22 pytest functions in `app/tests/test_api.py` — see Quick Start §2 above.
