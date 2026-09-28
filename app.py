"""
Adaptive AI Learning Platform — Streamlit MVP.

Flow: upload -> extract -> understand -> generate -> assess -> explain ->
analyze -> adapt -> reassess.
"""
from __future__ import annotations

import logging
import os

import streamlit as st
from dotenv import load_dotenv

from core import document_processor, quiz_engine, security
from core.adaptive_engine import build_adaptive_targets, next_difficulty
from core.document_processor import truncate_for_llm
from core.performance_analyzer import analyze
from core.quiz_engine import GenerationError
from core.schemas import QuizAttemptResult
from utils.helpers import format_bytes, mastery_color

load_dotenv()
logging.basicConfig(level=logging.INFO)

st.set_page_config(page_title="Adaptive AI Learning Platform", page_icon="🧠", layout="centered")

# ---------------------------------------------------------------- session --

def init_state():
    defaults = {
        "stage": "upload",          # upload -> ready -> quiz -> results
        "document_text": "",
        "filename": "",
        "concepts": [],
        "current_questions": [],
        "current_difficulty": "medium",
        "attempts": [],              # list[QuizAttemptResult]
        "user_answers": {},
        "flashcards": [],
        "practice_questions": [],
        "injection_warning": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


def reset_document():
    for k in ("document_text", "filename", "concepts", "current_questions", "attempts",
              "user_answers", "flashcards", "practice_questions", "injection_warning"):
        st.session_state[k] = [] if isinstance(st.session_state.get(k), list) else (
            {} if isinstance(st.session_state.get(k), dict) else ""
        )
    st.session_state["stage"] = "upload"
    st.session_state["current_difficulty"] = "medium"


# ------------------------------------------------------------------ header --

st.title("🧠 Adaptive AI Learning Platform")
st.caption("Upload material → generate a quiz → the platform adapts your next quiz to what you actually got wrong.")

if not os.environ.get("GROQ_API_KEY"):
    st.warning(
        "⚠️ GROQ_API_KEY is not set. Copy `.env.example` to `.env` and add your key before generating content.",
        icon="⚠️",
    )

with st.sidebar:
    st.subheader("Session")
    if st.session_state["filename"]:
        st.write(f"📄 **{st.session_state['filename']}**")
        st.write(f"Concepts identified: {len(st.session_state['concepts'])}")
        st.write(f"Quizzes taken this session: {len(st.session_state['attempts'])}")
        if st.button("Start over with a new document"):
            reset_document()
            st.rerun()
    else:
        st.write("No document loaded yet.")
    st.divider()
    st.caption(
        "Privacy: your document is processed in memory for this session only and is not persisted to disk or "
        "sent anywhere beyond the configured AI provider needed to generate content."
    )

# --------------------------------------------------------------- 1. upload --

if st.session_state["stage"] == "upload":
    st.subheader("1. Upload your material")
    uploaded = st.file_uploader("PDF or TXT", type=["pdf", "txt"])

    if uploaded is not None:
        file_bytes = uploaded.getvalue()
        validation = security.validate_uploaded_file(uploaded.name, len(file_bytes), uploaded.type)

        if not validation.ok:
            st.error(validation.message)
        else:
            st.write(f"**{uploaded.name}** — {format_bytes(len(file_bytes))}")
            with st.spinner("Extracting text..."):
                result = document_processor.extract_text(file_bytes, uploaded.name)

            if not result.ok:
                st.error(result.error)
            else:
                for w in result.warnings:
                    st.info(w)

                if security.looks_like_injection_attempt(result.text):
                    st.info(
                        "ℹ️ This document contains language that resembles an instruction to an AI system. "
                        "It will be treated strictly as reference content — any embedded instructions are ignored.",
                        icon="🛡️",
                    )

                st.success(f"Extracted {result.char_count:,} characters from {result.page_count} page(s).")

                if st.button("Understand this document →", type="primary"):
                    text_for_llm = truncate_for_llm(result.text)
                    with st.spinner("Identifying key concepts..."):
                        try:
                            concepts = quiz_engine.extract_concepts(text_for_llm)
                        except GenerationError as e:
                            st.error(str(e))
                            concepts = None

                    if concepts:
                        st.session_state["document_text"] = text_for_llm
                        st.session_state["filename"] = uploaded.name
                        st.session_state["concepts"] = concepts
                        st.session_state["stage"] = "ready"
                        st.rerun()

# ---------------------------------------------------------- 2. ready/select --

elif st.session_state["stage"] == "ready":
    st.subheader("2. Document ready")
    st.success(f"Loaded **{st.session_state['filename']}**")
    st.write("**Concepts identified:** " + ", ".join(st.session_state["concepts"]))

    tab_quiz, tab_flash, tab_practice = st.tabs(["📝 Quiz", "🗂️ Flashcards", "✍️ Practice Questions"])

    with tab_quiz:
        st.write("Generate an interactive multiple-choice quiz.")
        col1, col2 = st.columns(2)
        with col1:
            difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"], index=1)
        with col2:
            num_q = st.slider("Number of questions", security.MIN_QUESTIONS, security.MAX_QUESTIONS, 5)

        if st.button("Generate Quiz", type="primary"):
            with st.spinner("Generating your quiz..."):
                try:
                    questions = quiz_engine.generate_quiz(
                        st.session_state["document_text"], st.session_state["concepts"], difficulty, num_q
                    )
                except GenerationError as e:
                    st.error(str(e))
                    questions = None

            if questions:
                st.session_state["current_questions"] = questions
                st.session_state["current_difficulty"] = difficulty
                st.session_state["user_answers"] = {}
                st.session_state["stage"] = "quiz"
                st.rerun()

    with tab_flash:
        st.write("Generate flashcards for quick review.")
        if st.button("Generate Flashcards"):
            with st.spinner("Generating flashcards..."):
                try:
                    cards = quiz_engine.generate_flashcards(st.session_state["document_text"], st.session_state["concepts"])
                    st.session_state["flashcards"] = cards
                except GenerationError as e:
                    st.error(str(e))

        for i, card in enumerate(st.session_state["flashcards"]):
            with st.expander(f"{i + 1}. {card.front}  ·  _{card.concept}_"):
                st.write(card.back)

    with tab_practice:
        st.write("Generate open-ended practice questions.")
        p_difficulty = st.selectbox("Practice difficulty", ["easy", "medium", "hard"], index=1, key="practice_diff")
        if st.button("Generate Practice Questions"):
            with st.spinner("Generating practice questions..."):
                try:
                    pqs = quiz_engine.generate_practice_questions(
                        st.session_state["document_text"], st.session_state["concepts"], p_difficulty
                    )
                    st.session_state["practice_questions"] = pqs
                except GenerationError as e:
                    st.error(str(e))

        for i, pq in enumerate(st.session_state["practice_questions"]):
            st.markdown(f"**{i + 1}. {pq.question}**  ·  _{pq.concept} · {pq.difficulty}_")
            with st.expander("Show expected answer"):
                st.write(f"**Expected answer:** {pq.expected_answer}")
                st.write(f"**Why:** {pq.explanation}")

# -------------------------------------------------------------------- quiz --

elif st.session_state["stage"] == "quiz":
    questions = st.session_state["current_questions"]
    st.subheader(f"3. Quiz — {st.session_state['current_difficulty'].title()} difficulty")
    st.caption(f"{len(questions)} questions · answers are preserved as you go, nothing is graded until you submit.")

    with st.form("quiz_form"):
        for i, q in enumerate(questions):
            st.markdown(f"**{i + 1}. {q.question}**")
            key = f"answer_{q.id}"
            prior = st.session_state["user_answers"].get(q.id)
            choice = st.radio(
                "Choose one",
                q.options,
                index=q.options.index(prior) if prior in q.options else None,
                key=key,
                label_visibility="collapsed",
            )
            if choice is not None:
                st.session_state["user_answers"][q.id] = choice
            st.write("")
        submitted = st.form_submit_button("Submit Quiz", type="primary")

    if submitted:
        unanswered = [q for q in questions if q.id not in st.session_state["user_answers"]]
        if unanswered:
            st.error(f"Please answer all questions — {len(unanswered)} remaining.")
        else:
            result = analyze(questions, st.session_state["user_answers"], st.session_state["current_difficulty"])
            st.session_state["attempts"].append(result)
            st.session_state["stage"] = "results"
            st.rerun()

# ----------------------------------------------------------------- results --

elif st.session_state["stage"] == "results":
    attempt: QuizAttemptResult = st.session_state["attempts"][-1]
    st.subheader("4. Results")

    c1, c2, c3 = st.columns(3)
    c1.metric("Score", f"{attempt.score_pct}%")
    c2.metric("Correct", f"{attempt.correct_count}/{attempt.total_count}")
    c3.metric("Difficulty", attempt.difficulty.title())

    st.markdown("### Concept mastery")
    for concept, pct in sorted(attempt.concept_mastery.items(), key=lambda x: x[1]):
        st.write(f"{mastery_color(pct)} **{concept}** — {pct}%")
        st.progress(min(pct / 100, 1.0))

    st.markdown("### Review")
    for i, q in enumerate(attempt.questions):
        selected = attempt.user_answers.get(q.id)
        correct = selected == q.answer
        icon = "✅" if correct else "❌"
        with st.expander(f"{icon} {i + 1}. {q.question}"):
            st.write(f"Your answer: **{selected}**")
            if not correct:
                st.write(f"Correct answer: **{q.answer}**")
            st.write(f"**Explanation:** {q.explanation}")
            st.caption(f"Concept: {q.concept} · {q.difficulty}")

    st.divider()
    st.markdown("### Want more questions?")
    st.caption(
        "The next quiz will target your weak concepts, avoid repeating these questions, "
        "and adjust difficulty based on your choice."
    )

    if attempt.weak_concepts:
        st.info("🎯 Weakest concept(s) so far: " + ", ".join(attempt.weak_concepts))

    col1, col2, col3 = st.columns(3)
    action = None
    if col1.button("🔵 Less difficult"):
        action = "easier"
    if col2.button("🟢 Same difficulty"):
        action = "same"
    if col3.button("🔴 More difficult"):
        action = "harder"

    if action:
        new_difficulty = next_difficulty(attempt.difficulty, action)
        previous_questions, weak, strong = build_adaptive_targets(st.session_state["attempts"])

        with st.spinner(f"Generating your next quiz ({new_difficulty})..."):
            try:
                questions = quiz_engine.generate_adaptive_quiz(
                    st.session_state["document_text"],
                    new_difficulty,
                    len(attempt.questions),
                    previous_questions,
                    weak,
                    strong,
                )
            except GenerationError as e:
                st.error(str(e))
                questions = None

        if questions:
            st.session_state["current_questions"] = questions
            st.session_state["current_difficulty"] = new_difficulty
            st.session_state["user_answers"] = {}
            st.session_state["stage"] = "quiz"
            st.rerun()

    if st.button("⬅ Back to document menu"):
        st.session_state["stage"] = "ready"
        st.rerun()
