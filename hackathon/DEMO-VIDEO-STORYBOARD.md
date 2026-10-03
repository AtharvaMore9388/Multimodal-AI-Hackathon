# 🎬 YouTube Demo Video Storyboard & Script — StudyBuddy AI
**Multimodal AI Hackathon 2026 — Track D: Personalized Tutoring & Adaptive Learning**  
**Target Duration:** ~5 to 6 minutes  
**Format:** 1080p 60fps / 30fps screen recording + voiceover  
**Platform:** YouTube (Upload as Unlisted or Public)

---

## 📋 Pre-Recording Checklist (2 Minutes)

1. [x] **Backend & Web App Running**:
   - Web application live at `http://127.0.0.1:8000/`
   - Swagger API docs live at `http://127.0.0.1:8000/docs`
2. [x] **Browser Setup**:
   - Open browser (Chrome / Edge) in Full Screen (F11 or maximize window) at `http://127.0.0.1:8000/`
   - Zoom level set to 100% or 110% for crisp readability.
   - Clean tabs (close bookmarks bar if possible).
3. [x] **Audio / Mic**:
   - Clear microphone with minimal background noise.
4. [x] **Recording Tool Options**:
   - **Windows built-in**: Press `Win + Alt + R` to record screen immediately.
   - **OBS Studio**: Display Capture or Window Capture (1920x1080).
   - **Loom / Clipchamp**: 1-click browser/screen capture.

---

## ⏱️ Shot-by-Shot Script & Action Guide

---

### 🎬 Scene 1: Introduction & The Core Problem (0:00 – 0:45)
- **On Screen:** Start on the **Dashboard** (`http://127.0.0.1:8000/`) with the dark glassmorphic UI, live stats (13 topics, 5 documents, 68% mastery), and quick action cards.
- **Action:** Move the mouse cursor smoothly across the 4 stat counters and the status indicators.
- **Spoken Script (Word-for-Word):**
> *"Hi everyone! Welcome to our demonstration of **StudyBuddy AI**, built for Track D: Personalized Tutoring and Adaptive Learning.  
> As engineering students preparing for exams, our biggest pain point isn't a lack of study materials—it’s **trust and organization**. When students feed lecture slides, textbooks, and videos into standard LLMs, the answers often hallucinate, lack exact citations, or provide generic outside knowledge without telling us which slide or page our professor actually tested.  
> StudyBuddy AI solves this with three pillars: **Multimodal Ingestion with strict provenance**, **Source-Grounded RAG with explicit out-of-scope boundaries**, and a **Bayesian Knowledge Tracing Learner Model** that tracks per-topic mastery and drives adaptive quizzes."*

---

### 🎬 Scene 2: Multimodal Ingestion & Knowledge Extraction (0:45 – 1:45)
- **On Screen:** Click on the **Ingest & Library** tab (`/upload`). Show the drag-and-drop zone and the document table.
- **Action:**
  1. Point out the supported formats: PDF textbooks, PPTX slides, MP4/MP3 lecture videos.
  2. Click the **"✨ Ingest Sample OS Notes"** button (or drop a lecture file).
  3. Show the instant green confirmation box highlighting:
     - `Extracted Topics`
     - `Concepts Defined`
     - `Chunks Created with Provenance`
  4. In the table below, click **"Inspect Chunks"** on one document to reveal the chunk modal showing exact page numbers, slide indexes, and OCR diagram count.
- **Spoken Script (Word-for-Word):**
> *"Let's begin with Multimodal Ingestion. StudyBuddy accepts textbooks, lecture slides, and audio-video recordings without manual preprocessing.  
> When a document is uploaded, our pipeline chunks the content and runs an automated topic and concept extractor. Notice how every single chunk is tagged with its exact origin—page numbers for PDFs, slide indexes for PPTX, and timestamp intervals for audio and video, alongside OCR figure detection.  
> These provenance units are simultaneously stored in a vector index for retrieval and in SQLite for relational queries."*

---

### 🎬 Scene 3: Source-Grounded Chat & Scope Discipline (1:45 – 3:00)
- **On Screen:** Click on the **Source-Grounded Chat** tab (`/chat`).
- **Action:**
  1. Click the quick prompt: **"What is a page table and how does paging address translation work?"** and press **Send**.
  2. Point out:
     - The green **`[SOURCE-BACKED] Confidence: 90%`** badge.
     - The structured answer.
     - The clickable **Cited Source chips** (`[1] Doc · p.1 (88%)`). Click one to open the **Exact Provenance Modal** showing the original excerpt.
     - Click the **"🔊 Listen (TTS)"** button to showcase speech synthesis.
  3. Switch the Language dropdown to **"Bilingual Hindi (हिंदी)"** and ask a question to show multilingual explanation support.
  4. Now click the quick prompt: **"Who won the FIFA World Cup 2022 in Qatar?"** and press **Send**.
  5. Emphasize the red **`[UNSOURCED] Outside Material Warning (NO_CONTEXT)`** banner!
- **Spoken Script (Word-for-Word):**
> *"Now let's move to our grounded chat engine. When we ask 'What is a page table?', StudyBuddy retrieves relevant chunks and responds with a green **[SOURCE-BACKED]** badge.  
> Every response cites exact sources. When I click this citation chip, a modal opens displaying the exact excerpt, source document, page, and relevance score. We also have audio TTS and bilingual support in Hindi for conceptual clarity.  
> But here is what makes our system truly compliant with Rubric 2b: **Scope Discipline**. Watch what happens when I ask an off-topic question: 'Who won the FIFA World Cup?'.  
> The system strictly refuses to hallucinate from world knowledge and flags it with a red **[UNSOURCED]** banner, explicitly informing the student that the topic is outside the ingested course syllabus."*

---

### 🎬 Scene 4: Adaptive Assessment & Misconception Report (3:00 – 4:15)
- **On Screen:** Click on the **Adaptive Quiz** tab (`/quiz`).
- **Action:**
  1. Click **"🎯 Diagnostic Quiz"** (Rubric 4b Cold-Start onboarding).
  2. Show 5 diverse questions across topics (MCQ, Short Answer, Numerical).
  3. Answer a question: select Option C for MCQ, type an answer for short text, input a number for numerical.
  4. Click **"✓ Submit & Grade Assessment"**.
  5. Scroll down to show the comprehensive **Post-Assessment Report**:
     - Score Percentage (`80% or 100%`)
     - **Weak Topics to Review** tags (e.g. `Paging`, `Thrashing`)
     - **Targeted Misconception Diagnostic** card with specific revision hints
     - Question deduplication fingerprinting (ensures students never see repeated questions across assessments).
- **Spoken Script (Word-for-Word):**
> *"Next is our Adaptive Assessment pipeline. For new students, we provide a Cold-Start Diagnostic Quiz covering 5 high-level topics.  
> StudyBuddy generates three distinct question types: Multiple Choice with deduplicated option sets, Short Answer evaluated using keyword Jaccard overlap against ideal explanations, and Numerical questions evaluated within precision tolerances.  
> Every question is indexed with a SHA-1 fingerprint to prevent repetition. When we submit, the grader doesn't just give a score—it outputs a detailed diagnostic report highlighting the student's weakest topics and identifying specific conceptual misconceptions with actionable study hints."*

---

### 🎬 Scene 5: Learner Model, BKT Mastery & 14-Day Spaced Schedule (4:15 – 5:15)
- **On Screen:** Click on the **Learner Model & BKT** tab (`/mastery`).
- **Action:**
  1. Show the **Bayesian Knowledge Tracing (BKT) Mastery Bars** updating in real time with color-coded mastery (Emerald >70%, Amber 40-70%, Red <40%).
  2. Scroll to the **14-Day Spaced Repetition Study Plan** calendar grid:
     - Point out Day 1 to Day 14 slots balanced between weak topics, spaced reviews, and near-threshold items.
  3. Scroll to the **Weak-Topic Revision Flashcards**:
     - Click a card to demonstrate the smooth **3D Flip animation** revealing the source-backed concept definition or comparison.
- **Spoken Script (Word-for-Word):**
> *"Behind the scenes, every quiz answer and grounded conversation updates our **Learner Model** using Bayesian Knowledge Tracing with Exponential Moving Averages.  
> On the Mastery dashboard, you can see live progress bars for every course topic. Below that is an automated **14-day Spaced Repetition calendar** based on Ebbinghaus forgetting curves, distributing daily study slots between weak topics and spaced reviews.  
> We also synthesize interactive 3D flip flashcards—including definitions, comparisons, and cloze prompts—targeted specifically at the topics where the student scored lowest."*

---

### 🎬 Scene 6: Course Flow Map, RAGAS Benchmarks & Closing (5:15 – 6:00)
- **On Screen:**
  1. Click on the **Course Flow Map** tab (`/graph`): show the interactive SVG DAG with solid blue prerequisite arrows and dashed amber subtopic arrows. Click a node to open the concept definitions drawer.
  2. Click on the **RAGAS & Benchmarks** tab (`/benchmark`): click the **"🚀 Run RAGAS Evaluation"** button.
  3. Watch the metric scorecards update live:
     - Context Precision: `0.94`
     - Context Recall: `0.91`
     - Answer Relevance: `0.88`
     - Faithfulness: `0.95`
     - Scope Accuracy: `100% (2/2 off-topic correctly caught)`
  4. Click **"Run Simulation"** to display the multi-session student cohort gains (+32% mastery gain).
  5. Return to the **Dashboard** for closing words.
- **Spoken Script (Word-for-Word):**
> *"Finally, we offer a Visual Course Flow Map rendered as an interactive SVG DAG showing topic prerequisites and hierarchical subtopics.  
> And to prove our system's accuracy, our evaluation tab runs a 6-metric benchmark compatible with RAGAS and DeepEval on our team-built gold test set—measuring precision, recall, relevance, faithfulness, and scope accuracy. We also evaluate personalized learning through multi-session student simulations.  
> StudyBuddy AI brings complete source grounding, adaptive assessment, and transparent learner modeling into one unified companion. Thank you for watching!"*

---

## 📝 YouTube Submission Metadata (Copy & Paste Ready)

### Video Title:
```
StudyBuddy AI — Multimodal Adaptive Learning Companion (Track D | Hackathon 2026)
```

### Video Description:
```markdown
StudyBuddy AI is a source-grounded multimodal learning companion built for Track D: Personalized Tutoring & Adaptive Learning (Multimodal AI Hackathon 2026 / DevOps CA2).

Key Features Demonstrated:
0:00 - Introduction & The Midterm Problem
0:45 - Multimodal Ingestion (PDF, PPTX, Video/Audio) with Exact Provenance
1:45 - Source-Grounded RAG Chat, Citation Clickbacks & Scope Discipline (Rubric 2b)
3:00 - Adaptive Assessment Pipeline (MCQ, Short Answer, Numerical) & Misconceptions Report
4:15 - Bayesian Knowledge Tracing (BKT) Mastery, 14-Day Spaced Calendar & 3D Flashcards
5:15 - Visual Course Flow DAG Map & RAGAS 6-Metric Benchmark Suite
5:50 - Multi-Session Student Simulation & Closing

Tech Stack:
FastAPI, Python 3.10, SQLite WAL, ChromaDB, Sentence Transformers, Next.js / Vanilla UI, RAGAS Metrics.

GitHub Repository: aditisharmas11/DevOps-CA2_2023_27
Track D: Personalized Tutoring & Adaptive Learning
```

### Video Tags:
```
Multimodal AI, AI Tutor, RAG, Adaptive Learning, Bayesian Knowledge Tracing, Source Grounding, Education AI, FastAPI, Hackathon 2026
```
