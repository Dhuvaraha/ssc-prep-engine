from app.content.answer_key import parse_answer_page


def test_parses_sectioned_answer_key():
    text = """
Answers
General Intelligence and Reasoning
1.D 2.A 3.B 4.C
General Awareness
26.C 27.D
Quantitative Aptitude
51.A 52.B
English Comprehension
76.D 77.C
"""
    answers = parse_answer_page(text)
    assert answers[("reasoning", 1)] == 4
    assert answers[("general-awareness", 26)] == 3
    assert answers[("quant", 51)] == 1
    assert answers[("english", 76)] == 4
