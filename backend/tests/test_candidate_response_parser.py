from app.content.candidate_response_parser import parse_candidate_response


def test_parses_candidate_response_question_without_assuming_correctness():
    text = """Q.1 Find the next number in the series.
Ans 1. 10
2. 12
3. 14
4. 16
Question ID : 630680123
Option 1 ID : 1
Option 2 ID : 2
Option 3 ID : 3
Option 4 ID : 4
Status : Answered
Chosen Option : 2
"""
    questions = parse_candidate_response(text)
    assert len(questions) == 1
    assert questions[0].number == 1
    assert questions[0].chosen_option == 2
    assert questions[0].question_id == "630680123"
    assert [value for _, value in questions[0].options] == ["10", "12", "14", "16"]
