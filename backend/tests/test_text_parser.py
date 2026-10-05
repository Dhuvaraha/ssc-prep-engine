from app.content.text_parser import parse_text_candidates


def test_parses_simple_question_block():
    text = """1. Find the next number in the series.
A 10
B 12
C 14
D 16
Answer: B
"""
    candidates = parse_text_candidates(text)
    assert len(candidates) == 1
    assert candidates[0].number == 1
    assert candidates[0].correct_option == 2
    assert len(candidates[0].options) == 4
