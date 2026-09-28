"""Turns a completed quiz + the learner's answers into score and
concept-mastery data. Pure computation — no LLM calls here."""
from __future__ import annotations

from core.schemas import QuizAttemptResult, QuizQuestion

WEAK_THRESHOLD = 60.0   # % correct at or below this = weak concept
STRONG_THRESHOLD = 80.0  # % correct at or above this = strong concept


def analyze(questions: list[QuizQuestion], user_answers: dict[str, str], difficulty: str) -> QuizAttemptResult:
    total = len(questions)
    correct = 0

    concept_correct: dict[str, int] = {}
    concept_total: dict[str, int] = {}

    for q in questions:
        selected = user_answers.get(q.id)
        is_correct = selected == q.answer
        if is_correct:
            correct += 1
        concept_total[q.concept] = concept_total.get(q.concept, 0) + 1
        if is_correct:
            concept_correct[q.concept] = concept_correct.get(q.concept, 0) + 1

    concept_mastery = {
        concept: round(100.0 * concept_correct.get(concept, 0) / concept_total[concept], 1)
        for concept in concept_total
    }

    weak = sorted([c for c, pct in concept_mastery.items() if pct <= WEAK_THRESHOLD])
    strong = sorted([c for c, pct in concept_mastery.items() if pct >= STRONG_THRESHOLD])

    score_pct = round(100.0 * correct / total, 1) if total else 0.0

    return QuizAttemptResult(
        questions=questions,
        user_answers=user_answers,
        difficulty=difficulty,
        score_pct=score_pct,
        correct_count=correct,
        total_count=total,
        concept_mastery=concept_mastery,
        weak_concepts=weak,
        strong_concepts=strong,
    )


def aggregate_history(attempts: list[QuizAttemptResult]) -> dict[str, float]:
    """Combine concept mastery across all attempts so far in the session,
    so the adaptive engine can target concepts that are weak overall, not
    just in the most recent quiz."""
    concept_correct: dict[str, int] = {}
    concept_total: dict[str, int] = {}

    for attempt in attempts:
        for q in attempt.questions:
            selected = attempt.user_answers.get(q.id)
            concept_total[q.concept] = concept_total.get(q.concept, 0) + 1
            if selected == q.answer:
                concept_correct[q.concept] = concept_correct.get(q.concept, 0) + 1

    return {
        concept: round(100.0 * concept_correct.get(concept, 0) / concept_total[concept], 1)
        for concept in concept_total
    }
