import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.adaptive_engine import next_difficulty, build_adaptive_targets
from core.performance_analyzer import analyze
from core.schemas import QuizQuestion


def make_q(id_, concept, difficulty="medium"):
    return QuizQuestion(
        id=id_, question=f"Q about {concept} {id_}", options=["A", "B", "C", "D"],
        answer="A", explanation="because", concept=concept, difficulty=difficulty,
    )


def test_harder_from_medium():
    assert next_difficulty("medium", "harder") == "hard"

def test_harder_caps_at_hard():
    assert next_difficulty("hard", "harder") == "hard"

def test_easier_from_medium():
    assert next_difficulty("medium", "easier") == "easy"

def test_easier_floors_at_easy():
    assert next_difficulty("easy", "easier") == "easy"

def test_same_unchanged():
    assert next_difficulty("hard", "same") == "hard"

def test_weak_concept_detection():
    qs = [make_q("1", "Normalization"), make_q("2", "Normalization"), make_q("3", "2NF")]
    answers = {"1": "A", "2": "B", "3": "A"}  # q2 wrong -> Normalization 50%, 2NF 100%
    result = analyze(qs, answers, "medium")
    assert "Normalization" in result.weak_concepts
    assert "2NF" in result.strong_concepts
    assert result.score_pct == round(100 * 2 / 3, 1)

def test_build_adaptive_targets_aggregates_across_attempts():
    qs1 = [make_q("1", "A"), make_q("2", "B")]
    attempt1 = analyze(qs1, {"1": "A", "2": "wrong"}, "easy")  # B wrong
    qs2 = [make_q("3", "B"), make_q("4", "C")]
    attempt2 = analyze(qs2, {"3": "A", "4": "A"}, "medium")  # both correct

    prev_q, weak, strong = build_adaptive_targets([attempt1, attempt2])
    assert len(prev_q) == 4
    assert "B" in weak or "B" in strong  # B: 1/2 correct = 50% -> weak
    assert "C" in strong  # 1/1 correct = 100%


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
