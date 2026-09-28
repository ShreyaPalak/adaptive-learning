import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch
from core import quiz_engine
from core.llm_gateway import LLMResponse, GatewayError

GOOD_Q = {
    "question": "What is 2NF?",
    "options": ["A", "B", "C", "D"],
    "answer": "B",
    "explanation": "Because.",
    "concept": "2NF",
    "difficulty": "medium",
}


def test_generate_quiz_success():
    with patch("core.quiz_engine.call_llm_json", return_value=LLMResponse(data={"questions": [GOOD_Q]}, raw_text="")):
        qs = quiz_engine.generate_quiz("doc text", ["2NF"], "medium", 1)
    assert len(qs) == 1
    assert qs[0].answer == "B"
    assert qs[0].id  # got a generated id

def test_generate_quiz_malformed_output_raises_generation_error():
    with patch("core.quiz_engine.call_llm_json", return_value=LLMResponse(data={"questions": []}, raw_text="")):
        try:
            quiz_engine.generate_quiz("doc text", ["2NF"], "medium", 1)
            assert False, "expected GenerationError"
        except quiz_engine.GenerationError:
            pass

def test_generate_quiz_gateway_error_propagates_as_generation_error():
    with patch("core.quiz_engine.call_llm_json", side_effect=GatewayError("timed out")):
        try:
            quiz_engine.generate_quiz("doc text", ["2NF"], "medium", 1)
            assert False, "expected GenerationError"
        except quiz_engine.GenerationError as e:
            assert "timed out" in str(e)

def test_extract_concepts_success():
    with patch("core.quiz_engine.call_llm_json", return_value=LLMResponse(data={"concepts": ["A", "B"]}, raw_text="")):
        concepts = quiz_engine.extract_concepts("doc text")
    assert concepts == ["A", "B"]

def test_adaptive_quiz_avoids_crash_on_bad_json():
    with patch("core.quiz_engine.call_llm_json", return_value=LLMResponse(data={"nonsense": True}, raw_text="")):
        try:
            quiz_engine.generate_adaptive_quiz("doc", "hard", 3, [], ["X"], [])
            assert False, "expected GenerationError"
        except quiz_engine.GenerationError:
            pass

def test_generate_flashcards_success():
    with patch("core.quiz_engine.call_llm_json", return_value=LLMResponse(
        data={"flashcards": [{"front": "Q", "back": "A", "concept": "C"}]}, raw_text="")):
        cards = quiz_engine.generate_flashcards("doc", ["C"])
    assert len(cards) == 1


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
