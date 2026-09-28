# 🧠 Adaptive AI Learning Platform

An AI Adaptive Assessment and Learning System — not just "PDF → ChatGPT → MCQs."

## 1. Problem

Most document-to-quiz tools generate questions once and stop. They don't
know what the learner actually struggled with, so every subsequent quiz is
just as generic as the first.

## 2. Solution

Upload a PDF or text document. The platform:
1. Extracts and understands the material (identifies key concepts).
2. Generates a quiz, flashcards, or practice questions grounded in that material.
3. Scores the quiz and measures **per-concept mastery**, not just an overall %.
4. Lets the learner ask for the next quiz to be **easier, the same, or harder**.
5. Generates a genuinely new quiz that targets weak concepts, respects the
   requested difficulty, and never just rewords a previous question.

The loop doesn't stop at the quiz — the learner's performance shapes what
gets generated next.

## 3. Key features (implemented now)

- PDF/TXT upload with size, type, and content validation
- Robust text extraction (handles multi-page PDFs, scanned/blank pages, encrypted PDFs, malformed files)
- Concept extraction from source material
- MCQ quiz generation (configurable count/difficulty), grounded in the source
- Flashcard generation
- Open-ended practice question generation
- Interactive quiz UI with preserved answers and no early answer reveal
- Overall + per-concept scoring and mastery breakdown
- Adaptive next-quiz generation: same/harder/easier, targets weak concepts,
  explicitly avoids repeating or lightly rewording previous questions
- Structured JSON output from the LLM, validated before use
- Prompt-injection defense (uploaded content is fenced as untrusted data)
- Retry/timeout/error handling around the LLM call
- No hardcoded secrets; `.env`-based configuration

## 4. Architecture

```
USER → Streamlit UI → Validation (core/security.py)
     → Document Processor (core/document_processor.py)
     → LLM Gateway (core/llm_gateway.py) — the only module that calls the API
     → Output Validator (core/validator.py)
     → Quiz / Flashcards / Practice (core/quiz_engine.py)
     → Performance Analyzer (core/performance_analyzer.py)
     → Adaptive Engine (core/adaptive_engine.py) → back into LLM Gateway
       with a targeted prompt (weak concepts, prior questions, new difficulty)
```

```
project/
├── app.py                     # Streamlit UI / orchestration
├── requirements.txt
├── .env.example
├── core/
│   ├── security.py            # file + input validation, injection defenses
│   ├── document_processor.py  # PDF/TXT extraction
│   ├── prompts.py             # prompt templates, trust-boundary separation
│   ├── llm_gateway.py         # sole point of contact with the LLM API
│   ├── validator.py           # validates LLM JSON output
│   ├── quiz_engine.py         # orchestrates generation calls
│   ├── performance_analyzer.py# scoring + concept mastery
│   ├── adaptive_engine.py     # next-difficulty + targeting logic
│   └── schemas.py             # dataclasses shared across modules
├── utils/helpers.py
└── tests/                     # unit tests (39, all passing, mocked LLM calls)
```

## 5. Adaptive learning mechanism

After a quiz, the learner picks 🔵 Less difficult / 🟢 Same / 🔴 More difficult.
`adaptive_engine.next_difficulty()` maps that to easy/medium/hard deterministically
(not left to the LLM's judgement). The app then aggregates concept mastery
across the whole session and builds a prompt (`prompts.adaptive_quiz_prompt`)
that gives the LLM: the source material, the new difficulty with explicit
criteria, every previously-asked question (so it can avoid duplicates/rewordings),
and the weak/strong concepts to prioritize.

## 6. LLM usage

- Provider: Groq API (`GROQ_API_KEY` in `.env`), OpenAI-compatible chat completions
  endpoint, JSON mode enabled (`response_format: json_object`).
- All prompts are built in `core/prompts.py` with four explicitly separated
  sections: system instructions, trusted application state, untrusted document
  content, and learner data.
- All responses are parsed and validated in `core/validator.py` before use —
  malformed or incomplete output is rejected and retried, never rendered.

## 7. Security

- Uploaded files: extension, MIME-type (best-effort), size, and emptiness
  checks; path-traversal/control-character filenames rejected.
- Uploaded content is never executed and is only read as text.
- Uploaded document text is wrapped in an explicit "untrusted reference
  material" fence in every prompt, with an instruction to ignore embedded
  commands and never reveal system instructions/credentials.
- A lightweight heuristic flags likely injection attempts in the UI (for
  transparency) — this never changes grading or generation logic, since
  the real defense is the prompt fencing above.
- All user-controlled generation parameters (question count, difficulty)
  are validated against a fixed allow-list before use.
- Secrets are read from environment variables only; `.env` is gitignored;
  `.env.example` ships with no real credentials.
- LLM output is fully validated (required fields, exactly 4 options, answer
  must be one of the options, no duplicate options, valid difficulty) before
  it's ever rendered or scored.
- Errors never leak stack traces, API keys, internal paths, or prompts to
  the user — only clean, user-facing messages.

## 8. Privacy

- The document is kept in Streamlit session state (in memory) for the
  current session only — it is not written to disk and not persisted
  after the session ends.
- Raw document content and raw user answers are never written to logs;
  only metadata (status codes, latency, attempt counts) is logged.
- The document text and session-derived performance data are sent to the
  configured LLM provider (Groq) only as needed to generate content —
  no unrelated identity data is included.

## 9. Technology choices

Streamlit (fast, demo-friendly UI) + Python. `pypdf` for PDF text extraction.
`requests` for direct HTTP calls to Groq's OpenAI-compatible endpoint (keeps
the LLM Gateway dependency-light and easy to audit). Session state instead
of a database — this is an MVP; no data needs to outlive the session.

## 10. Known limitations

- Session-only state: closing the browser tab loses quiz history (by design, for privacy — see §8).
- Scanned/image-only PDFs aren't handled (no OCR pipeline in this MVP).
- No real authentication — a single implicit "session" stands in for a user.
- No persistent rate limiting; the LLM Gateway retries on transient failures
  but doesn't cap total requests per user. Flagged here as a production
  requirement rather than implemented as a stub.
- Single quiz "session" per browser tab; no multi-user/classroom view.

## 11. Future / production architecture

```
PDF/TXT/Images → Multimodal ingestion → Content structuring → Chunking
→ Embeddings → Vector DB → Retriever → LLM Gateway → Validation → Learning system
```

Also: persistent learner profiles across sessions/documents, real auth with
Student/Teacher/Admin roles (documented below), a proper rate limiter, and
a teacher-facing class performance dashboard.

**Future roles (not implemented, documented for extension):**
- **Student** — upload, generate, take quizzes/flashcards/practice, view own performance.
- **Teacher** — create/share material, view learner/class performance.
- **Admin** — system management.

## 12. How to run

```bash
git clone <this repo>
cd adaptive-learning
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt

cp .env.example .env
# edit .env and set GROQ_API_KEY=<your key>

streamlit run app.py
```

Then open the URL Streamlit prints (usually http://localhost:8501).

Run the tests:

```bash
python tests/test_document_processor.py
python tests/test_validator.py
python tests/test_adaptive_engine.py
python tests/test_quiz_engine.py
python tests/test_security.py
```

## 13. Demo flow

1. Upload a PDF/TXT → see extracted concepts.
2. Generate a medium-difficulty quiz.
3. Answer it (mix of right/wrong on purpose) → submit.
4. See overall score + per-concept mastery (a weak concept will show red 🔴).
5. Click **🔴 More difficult** → a new quiz appears at "hard" difficulty,
   explicitly targeting the weak concept, with different questions than before.
6. Point out to the judge: same source document, same concept, but a
   different reasoning pattern than the first quiz — that's the adaptive loop.
