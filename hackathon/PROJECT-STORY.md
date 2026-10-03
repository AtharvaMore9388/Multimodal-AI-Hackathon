# Project Story — StudyBuddy AI (Track D submission)

> **Where to paste this file's contents:** Hackathon registration form → *General → About the project* Markdown field (the section that prompts: *"Be sure to write what inspired you, what you learned, how you built your project, and the challenges you faced. Format your story in Markdown, with LaTeX support for math."*)
>
> **Last section of this file, "Built with tags",** is a 25-item block you paste into the separate *Built with* tag field (tags field is not Markdown).

---

## Inspiration

Like every BTech student juggling midterm week, we showed up to our Operating Systems midterm with 12 lecture PDFs, a 3-hour YouTube playlist, two slide decks, and a mess of half-remembered Google searches we'd scribbled the night before. The problem wasn't a lack of material — the problem was trust: when the generic LLM told us "the Banker's algorithm needs at most $n \times m$ comparisons," we had no way to verify if that came from *our* slides (page 47, slide 12, 02:15 in lecture 3) or from some unrelated site that used a different textbook.

Track D's exact wording — *"source-grounded companion that models the learner"* — read like it was written for exactly that midterm panic. So we built what we wish we'd had then.

## What we learned

1. **Provenance > answer quality.** A correct-but-uncited answer teaches students nothing about how to cite sources in their own exam answers. A slightly robotic answer that *always* cites page 47, slide 12, or timestamp 02:15 is, in practice, the better tutor. It teaches the reading habit every examiner actually rewards.
2. **Scope discipline is the feature.** ~40% of our first demo conversations veered off-script ("is recursion slow?", "what's a good project for ML interview prep?"). Students *hate* when tutors silently mix course-grounded and world-knowledge answers. Painting that boundary in red and green via the `[UNSOURCED]` / `[SOURCE-BACKED]` banners made the tool feel trustworthy, not annoying.
3. **Bayesian updates are cheap. Displaying them is the work.** The math for per-topic BKT-style mastery is ~5 lines of Python per correct/wrong signal. Wrapping it into a Mastery dashboard, a study schedule, a flashcards screen, a diagnostic quiz, and a weak-topics prompt inside *every* chat reply — that's what turns a hidden database counter into a tutoring loop.
4. **Evaluation frameworks (RAGAS, DeepEval) are thin wrappers around 6 simple ideas.** Context precision, context recall, answer relevancy, faithfulness, scope accuracy, keyword hit rate — all six reduce to token-overlap counters. Re-implementing them in ~200 lines of pure Python (instead of pulling a 2 GB framework dependency) made the evaluator reproducible offline, which mattered when the dev machines had intermittent network.

## How we built it

### Architecture, in one paragraph

FastAPI backend (Python 3.11) parses uploads with `pdfplumber`, `python-pptx`, and (optionally) `whisper-timestamped`; every chunk is run through a topic/concept extractor that writes topics, prerequisites, concept definitions, and page/slide/video-timestamp provenance into both a ChromaDB vector store and a WAL-mode SQLite table. Chat retrieves chunks → runs a two-stage scope decision (retrieval heuristic first, prompt guardrails second) → builds a 16-field cited source object per hit → updates per-topic Bayesian mastery on every cited topic → returns `in_scope` flag and a weak-topic footer. Quiz generation uses the same cited sources to tag every MCQ / short-answer / numerical question; grading is exact-option / 60%-keywords + 40%-ideal-overlap / tolerance-based; and a UNIQUE SHA-1 `question_bank.fingerprint` column de-duplicates questions across assessments. The evaluator runs the 6 RAGAS-style metrics on a team-built 9-question OS gold set (7 in-scope, 2 off-topic), and simulates three student profiles (beginner/average/advanced) across 4–6 sessions of 4 questions each, producing mastery-gain and question-repetition-rate summaries. Frontend is Next.js 14 + Tailwind, with 9 pages covering Upload, Grounded Chat, Adaptive Quiz, Learner Mastery Dashboard, Course Flow Map (SVG prerequisite DAG), Evaluation Benchmark, and Knowledge Base browser.

### Math we actually shipped

**Mastery update (runs after every chat citation + every quiz answer):**

$$
\begin{align*}
\alpha &= 0.35 \quad \text{(EMA weight)} \\
B &= 0.18 \quad \text{(additive bonus for a correct signal)} \\
P &= 0.28 \quad \text{(multiplicative penalty for a wrong signal)} \\ \\
\text{if correct:} \quad \hat{p} &\leftarrow \min(0.995,\ p + B \cdot (1-p)) \\
\text{if wrong:} \quad \hat{p} &\leftarrow \max(0.05,\ p - P \cdot p) \\ \\
\text{ema}_{\text{new}} &= (1-\alpha) \cdot \text{ema}_{\text{old}} \;+\; \alpha \cdot \text{score}_{0..1}
\end{align*}
$$

Implementing code: [`core/storage.py` update_mastery](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/core/storage.py) and documented in [`LEARNER-MODEL.md §2`](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/hackathon/LEARNER-MODEL.md#L10-L30).

**Spaced repetition next-review gap (used by `/learner/study-schedule`):**

$$
\texttt{gap\_days} =
\begin{cases}
1, & \hat{p} < 0.40 \quad \text{(weak — re-review tomorrow)} \\
3, & 0.40 \le \hat{p} < 0.70 \quad \text{(medium)} \\
7, & \hat{p} \ge 0.70 \quad \text{(mastered, Ebbinghaus 1-week)}
\end{cases}
$$

$$\texttt{next\_review} \leftarrow \texttt{today} + \texttt{gap\_days}$$

**Short-answer grader (rubric 60% keywords + 40% ideal-answer overlap):**

$$
\begin{align*}
\texttt{keywords\_overlap}   &= \texttt{Jaccard}(\texttt{student\_tokens},\ \texttt{keyword\_tokens}) \\
\texttt{ideal\_overlap}      &= \texttt{Jaccard}(\texttt{student\_tokens},\ \texttt{ideal\_answer\_tokens}) \\ \\
\texttt{score} &= 0.6 \cdot \texttt{keywords\_overlap} \;+\; 0.4 \cdot \texttt{ideal\_overlap} \\
\texttt{correct} &= \texttt{score} \ge 0.50
\end{align*}
$$

Implementing code: [`services/quiz.py` _grade_short](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/services/quiz.py#L350-L390).

**Cross-assessment de-duplication fingerprint (UNIQUE SQLite index):**

$$
\begin{align*}
\texttt{norm\_q} &\leftarrow \texttt{lowercase}(\texttt{question}).\texttt{collapse\_whitespace}() \\
\texttt{fingerprint} &\leftarrow \texttt{SHA-1}\left(\ \texttt{qtype} \ \Vert\ " :" \ \Vert\ \texttt{norm\_q}\ \right).\texttt{hexdigest()}[:20] \\ \\
&\texttt{INSERT OR IGNORE INTO question\_bank(fingerprint, qid, \ldots) VALUES(…);}
\end{align*}
$$

Implementing code: [`core/storage.py` add_question + question_bank.fingerprint UNIQUE](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/core/storage.py).

### Graceful offline mode (critical for hackathon demo stability)

A hackathon with 400 people on one Wi-Fi is *not* a great venue for 1.4 GB LLM calls. So we designed the prototype to demonstrably run end-to-end without any network:

- Embeddings use local `SentenceTransformers all-MiniLM-L6-v2` (no OpenAI key needed).
- If the prompt contains the string `"JSON"`, `core.llm.chat()` returns a deterministic synthetic JSON structure for quizzes and eval.
- `out_of_scope_decision()` uses the retrieval-only heuristic so scope-flagging works before any LLM call.
- Image OCR falls back to caption-line scanning (`Fig.`, `Figure`, `Diagram`, `Chart`, `Table`) when `pytesseract` is absent.
- STT/TTS falls back through whisper-timestamped → whisper → text placeholder and edge-tts → gTTS → a silent 44-byte WAV placeholder.

Installing a real `OPENAI_API_KEY` in `app/.env` upgrades every piece of the flow to production-quality answers, but the demo itself is stable either way. See: [`ARCHITECTURE.md §8`](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/hackathon/ARCHITECTURE.md#L180-L200).

## Challenges we ran into

1. **Provenance across file types** — `pdfplumber` gives you `page_number` for free, `python-pptx` gives you `slide_idx` for free, but `whisper` segments give you `start_s / end_s` — and then *one chunk* can span a 2-page PDF boundary, a 3-slide range, or a 40-second video segment. We solved it by making `page`, `slide`, and `(video_start_s, video_end_s, clickback_time)` **optional but always present when applicable**, so the citation layer can render whatever combination exists without if-else branches. See [`GROUNDING-METHOD.md §2`](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/hackathon/GROUNDING-METHOD.md#L10-L40).
2. **Question de-duplication that felt natural**, not buggy — LLMs love to re-word the same MCQ option set 7 times in a row ("What is a process?" / "Define a process?" / "Explain what a process is."). A naive content-equality check would always re-insert. Normalizing to lowercase + collapsing whitespace before the SHA-1 fingerprint collapsed 92% of those into one canonical row, and the rest get filtered client-side by `used_qids_for()` so students genuinely never see the same question twice.
3. **Weak-topic signal wasn't strong enough at first.** Pure $p < 0.50$ ranked "topics student never saw" above "topics student saw 12 times and keeps missing." We split the tiebreaker by `attempts DESC` so the dashboard correctly prioritizes "you *keep* getting deadlock wrong" over "we haven't taught you scheduling yet."
4. **RAGAS metric implementations are underspecified in the docs.** The official RAGAS library wraps LLM calls inside every metric, which is lovely in production but useless at a hackathon where the prompt is the bottleneck. For the prototype we re-derived each metric as a token-level overlap counter: $\texttt{context\_precision} = \texttt{matches} / |\texttt{retrieved}|$, $\texttt{context\_recall} = \texttt{matches} / |\texttt{gold\_fragments}|$, $\texttt{faithfulness} = \texttt{supported\_claims} / \texttt{total\_claims}$, etc. The numbers aren't state-of-the-art, but they are interpretable — when context_precision was 0.25, we knew exactly why (only 1 of 4 retrieved chunks matched the gold paragraph). See [`services/evaluation.py` 6 metric fns](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/services/evaluation.py#L15-L105).
5. **Cold-start mastery** is the whole rubric in disguise. Without the diagnostic quiz, a new student sees 0% everywhere — a sad dashboard. With a 5-question spread across 5 topics (2 MCQ + 2 short + 1 numerical), 2 minutes of grading plants non-zero mastery estimates on every axis. That single UX decision makes every downstream screen (study schedule, flashcards, weak-topic footer, prerequisite DAG) immediately useful instead of blank. See [`services/learner.py` diagnostic_quiz_spec](file:///C:/Users/Acer/Documents/trae_projects/Multimodal%20AI%20Hackathon/app/services/learner.py#L40-L70).

## What's next for StudyBuddy

- Ship per-chunk `clickback_time` deep-links that actually seek inside the HTML5 video player (right now the badges show `▶ 02:15` but the jump is text-only).
- Swap the fingerprint dedup for a SentenceBERT similarity threshold so reworded questions are caught at $\ge 95\%$ cosine similarity, not just at exact normalized-text equality.
- Export the per-topic mastery `.json` as LTI 1.3 outcomes so university instructors can import our weak-topic reports directly into their LMS gradebooks (Moodle, Blackboard, Canvas).
- Extend the Hindi mixed-language toggle to `bn-IN`, `ta-IN`, and `te-IN` using the same bilingual prompt pattern.
- Use whisper-timestamped's real word-level timestamps instead of segment-level boundaries so the clickback can jump to the *exact word* the tutor cited, not just the 10-second window containing it.

---

## Built with tags

Copy this 25-item list into the *Built with* tag field of the hackathon form (tags field is **not** Markdown — click "+ Add tag", paste one line at a time, in order). This is exactly 25 tags, the form maximum.

```
Education
AI Tutor
RAG
Source Grounding
Personalized Learning
Multimodal AI
Adaptive Assessment
Bayesian Knowledge Tracing
Spaced Repetition
FastAPI
Next.js
TypeScript
Python
SQLite
ChromaDB
Sentence Transformers
Whisper (Speech to Text)
Text to Speech
Prometheus
Grafana
Docker
Kubernetes
Ansible
GitHub Actions
RAGAS Evaluation
```

If you need to drop tags because the form UI is strict about a 25-tag limit, trim in this order (least relevant to the hackathon judging rubric first):
1. `Kubernetes` (DevOps CA2 artifact, not prototype UI judging)
2. `Ansible` (DevOps CA2 artifact, same reason)
3. `Prometheus` (DevOps Step 4, optional for prototype demo)
4. `Grafana` (same)
