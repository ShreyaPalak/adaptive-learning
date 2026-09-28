import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import validator

GOOD_Q = {
    "question": "What is 2NF?",
    "options": ["A", "B", "C", "D"],
    "answer": "B",
    "explanation": "Because B satisfies the rule.",
    "concept": "2NF",
    "difficulty": "medium",
}


def test_valid_question_passes():
    out = validator.validate_quiz_questions({"questions": [GOOD_Q]})
    assert out is not None and len(out) == 1

def test_missing_field_rejected():
    bad = dict(GOOD_Q)
    del bad["explanation"]
    out = validator.validate_quiz_questions({"questions": [bad]})
    assert out is None

def test_wrong_option_count_rejected():
    bad = dict(GOOD_Q)
    bad["options"] = ["A", "B", "C"]
    out = validator.validate_quiz_questions({"questions": [bad]})
    assert out is None

def test_answer_not_in_options_rejected():
    bad = dict(GOOD_Q)
    bad["answer"] = "Z"
    out = validator.validate_quiz_questions({"questions": [bad]})
    assert out is None

def test_duplicate_options_rejected():
    bad = dict(GOOD_Q)
    bad["options"] = ["A", "A", "C", "D"]
    out = validator.validate_quiz_questions({"questions": [bad]})
    assert out is None

def test_invalid_difficulty_rejected():
    bad = dict(GOOD_Q)
    bad["difficulty"] = "impossible"
    out = validator.validate_quiz_questions({"questions": [bad]})
    assert out is None

def test_duplicate_questions_deduplicated():
    out = validator.validate_quiz_questions({"questions": [GOOD_Q, dict(GOOD_Q)]})
    assert len(out) == 1

def test_missing_fields_key_returns_none():
    assert validator.validate_quiz_questions({}) is None

def test_flashcards_valid():
    cards = validator.validate_flashcards({"flashcards": [{"front": "Q", "back": "A", "concept": "C"}]})
    assert cards is not None and len(cards) == 1

def test_flashcards_missing_field_dropped():
    cards = validator.validate_flashcards({"flashcards": [{"front": "Q", "back": ""}]})
    assert cards is None

def test_practice_questions_valid():
    items = validator.validate_practice_questions({"practice_questions": [{
        "question": "Explain X", "expected_answer": "Y", "explanation": "Z",
        "concept": "C", "difficulty": "hard"}]})
    assert items is not None and len(items) == 1

def test_concepts_valid():
    concepts = validator.validate_concepts({"concepts": ["A", "B", ""]})
    assert concepts == ["A", "B"]


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
