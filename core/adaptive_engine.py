"""Decides the next quiz's difficulty and concept targeting based on the
learner's choice ("same"/"harder"/"easier") and their performance history.
This is where the "closing the loop" logic lives — deliberately kept small
and explicit rather than delegated to the LLM."""
from __future__ import annotations

from core.performance_analyzer import aggregate_history
from core.schemas import QuizAttemptResult

DIFFICULTY_ORDER = ["easy", "medium", "hard"]


def next_difficulty(current_difficulty: str, action: str) -> str:
    idx = DIFFICULTY_ORDER.index(current_difficulty) if current_difficulty in DIFFICULTY_ORDER else 1
    if action == "harder":
        idx = min(idx + 1, len(DIFFICULTY_ORDER) - 1)
    elif action == "easier":
        idx = max(idx - 1, 0)
    # "same" leaves idx unchanged
    return DIFFICULTY_ORDER[idx]


def build_adaptive_targets(attempts: list[QuizAttemptResult]) -> tuple[list[str], list[str], list[str]]:
    """Returns (previous_question_texts, weak_concepts, strong_concepts)
    across the whole session so far, used to build the targeted prompt."""
    previous_questions = [q.question for attempt in attempts for q in attempt.questions]
    mastery = aggregate_history(attempts)
    weak = sorted([c for c, pct in mastery.items() if pct <= 60.0])
    strong = sorted([c for c, pct in mastery.items() if pct >= 80.0])
    return previous_questions, weak, strong
