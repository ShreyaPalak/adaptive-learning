"""Validates LLM-generated structures before they ever reach the UI or
session state. Nothing downstream should trust raw LLM output directly."""
from __future__ import annotations

from core.security import VALID_DIFFICULTIES


def validate_concepts(data: dict) -> list[str] | None:
    concepts = data.get("concepts")
    if not isinstance(concepts, list) or not concepts:
        return None
    cleaned = [c.strip() for c in concepts if isinstance(c, str) and c.strip()]
    return cleaned or None


def _validate_single_question(q: dict) -> bool:
    if not isinstance(q, dict):
        return False
    required = ("question", "options", "answer", "explanation", "concept", "difficulty")
    if not all(k in q for k in required):
        return False
    if not isinstance(q["question"], str) or not q["question"].strip():
        return False
    if not isinstance(q["options"], list) or len(q["options"]) != 4:
        return False
    if not all(isinstance(o, str) and o.strip() for o in q["options"]):
        return False
    if len(set(q["options"])) != 4:  # no duplicate options
        return False
    if q["answer"] not in q["options"]:
        return False
    if not isinstance(q["explanation"], str) or not q["explanation"].strip():
        return False
    if not isinstance(q["concept"], str) or not q["concept"].strip():
        return False
    if q["difficulty"] not in VALID_DIFFICULTIES:
        return False
    return True


def validate_quiz_questions(data: dict, expected_count: int | None = None) -> list[dict] | None:
    questions = data.get("questions")
    if not isinstance(questions, list) or not questions:
        return None
    valid = [q for q in questions if _validate_single_question(q)]
    if not valid:
        return None
    # De-duplicate identical question text defensively.
    seen = set()
    deduped = []
    for q in valid:
        key = q["question"].strip().lower()
        if key not in seen:
            seen.add(key)
            deduped.append(q)
    return deduped


def validate_flashcards(data: dict) -> list[dict] | None:
    cards = data.get("flashcards")
    if not isinstance(cards, list) or not cards:
        return None
    valid = []
    for c in cards:
        if not isinstance(c, dict):
            continue
        if all(isinstance(c.get(k), str) and c.get(k, "").strip() for k in ("front", "back", "concept")):
            valid.append(c)
    return valid or None


def validate_practice_questions(data: dict) -> list[dict] | None:
    items = data.get("practice_questions")
    if not isinstance(items, list) or not items:
        return None
    required = ("question", "expected_answer", "explanation", "concept", "difficulty")
    valid = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if not all(isinstance(item.get(k), str) and item.get(k, "").strip() for k in required):
            continue
        if item["difficulty"] not in VALID_DIFFICULTIES:
            continue
        valid.append(item)
    return valid or None
