"""Orchestrates calls to the LLM gateway for concept extraction, quiz
generation, flashcards, and practice questions — always through
core.prompts (trust boundaries) and core.validator (output validation)."""
from __future__ import annotations

import uuid

from core import prompts, validator
from core.llm_gateway import GatewayError, call_llm_json
from core.schemas import Flashcard, PracticeQuestion, QuizQuestion


class GenerationError(Exception):
    """User-facing generation failure (already a clean message)."""


def extract_concepts(document_text: str) -> list[str]:
    try:
        response = call_llm_json(prompts.concept_extraction_prompt(document_text))
    except GatewayError as e:
        raise GenerationError(str(e)) from e

    concepts = validator.validate_concepts(response.data)
    if not concepts:
        raise GenerationError("Couldn't identify concepts from this document. Try a document with more structured content.")
    return concepts


def generate_quiz(document_text: str, concepts: list[str], difficulty: str, num_questions: int) -> list[QuizQuestion]:
    try:
        response = call_llm_json(
            prompts.quiz_generation_prompt(document_text, concepts, difficulty, num_questions),
            max_tokens=4000,
        )
    except GatewayError as e:
        raise GenerationError(str(e)) from e

    valid = validator.validate_quiz_questions(response.data)
    if not valid:
        raise GenerationError("The AI couldn't generate valid questions from this document. Please try again.")
    return [
        QuizQuestion(
            id=str(uuid.uuid4())[:8],
            question=q["question"],
            options=q["options"],
            answer=q["answer"],
            explanation=q["explanation"],
            concept=q["concept"],
            difficulty=q["difficulty"],
        )
        for q in valid
    ]


def generate_adaptive_quiz(
    document_text: str,
    difficulty: str,
    num_questions: int,
    previous_questions: list[str],
    weak_concepts: list[str],
    strong_concepts: list[str],
) -> list[QuizQuestion]:
    try:
        response = call_llm_json(
            prompts.adaptive_quiz_prompt(
                document_text, difficulty, num_questions, previous_questions, weak_concepts, strong_concepts
            ),
            max_tokens=4000,
        )
    except GatewayError as e:
        raise GenerationError(str(e)) from e

    valid = validator.validate_quiz_questions(response.data)
    if not valid:
        raise GenerationError("The AI couldn't generate valid follow-up questions. Please try again.")
    return [
        QuizQuestion(
            id=str(uuid.uuid4())[:8],
            question=q["question"],
            options=q["options"],
            answer=q["answer"],
            explanation=q["explanation"],
            concept=q["concept"],
            difficulty=q["difficulty"],
        )
        for q in valid
    ]


def generate_flashcards(document_text: str, concepts: list[str], num_cards: int = 10) -> list[Flashcard]:
    try:
        response = call_llm_json(prompts.flashcard_prompt(document_text, concepts, num_cards), max_tokens=3000)
    except GatewayError as e:
        raise GenerationError(str(e)) from e

    valid = validator.validate_flashcards(response.data)
    if not valid:
        raise GenerationError("The AI couldn't generate flashcards from this document. Please try again.")
    return [Flashcard(front=c["front"], back=c["back"], concept=c["concept"]) for c in valid]


def generate_practice_questions(
    document_text: str, concepts: list[str], difficulty: str, num_questions: int = 5
) -> list[PracticeQuestion]:
    try:
        response = call_llm_json(
            prompts.practice_question_prompt(document_text, concepts, difficulty, num_questions), max_tokens=3000
        )
    except GatewayError as e:
        raise GenerationError(str(e)) from e

    valid = validator.validate_practice_questions(response.data)
    if not valid:
        raise GenerationError("The AI couldn't generate practice questions from this document. Please try again.")
    return [
        PracticeQuestion(
            question=q["question"],
            expected_answer=q["expected_answer"],
            explanation=q["explanation"],
            concept=q["concept"],
            difficulty=q["difficulty"],
        )
        for q in valid
    ]
