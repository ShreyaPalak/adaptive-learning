"""Plain dataclasses describing the shapes we expect the LLM (and the rest
of the app) to produce. Kept dependency-free so they're easy to serialize
into/out of Streamlit session state."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class QuizQuestion:
    id: str
    question: str
    options: list[str]
    answer: str
    explanation: str
    concept: str
    difficulty: str  # easy | medium | hard

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "question": self.question,
            "options": self.options,
            "answer": self.answer,
            "explanation": self.explanation,
            "concept": self.concept,
            "difficulty": self.difficulty,
        }


@dataclass
class Flashcard:
    front: str
    back: str
    concept: str


@dataclass
class PracticeQuestion:
    question: str
    expected_answer: str
    explanation: str
    concept: str
    difficulty: str


@dataclass
class ConceptSet:
    concepts: list[str] = field(default_factory=list)


@dataclass
class QuizAttemptResult:
    """One completed quiz, scored, kept in history to drive adaptation."""
    questions: list[QuizQuestion]
    user_answers: dict[str, str]  # question id -> selected option
    difficulty: str
    score_pct: float
    correct_count: int
    total_count: int
    concept_mastery: dict[str, float]  # concept -> % correct
    weak_concepts: list[str]
    strong_concepts: list[str]
