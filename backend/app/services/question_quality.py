import re

from app.models import Question


def _normalize(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).lower()


def question_content_signature(question: Question) -> tuple:
    return (
        _normalize(question.question_text),
        _normalize(question.question_image_url),
        tuple(
            (option.position, _normalize(option.text), _normalize(option.image_url))
            for option in question.options
        ),
    )


def unique_questions(questions: list[Question]) -> list[Question]:
    seen: set[tuple] = set()
    result: list[Question] = []
    for question in questions:
        signature = question_content_signature(question)
        if signature in seen:
            continue
        seen.add(signature)
        result.append(question)
    return result
