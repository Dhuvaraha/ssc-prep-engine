import re
from dataclasses import dataclass


QUESTION_START = re.compile(r"(?m)^\s*(\d{1,3})[.)]\s+")
ANSWER_LINE = re.compile(r"(?im)^\s*Answer\s*:\s*([A-D1-4])\s*$")
OPTION_LINE = re.compile(r"(?m)^\s*([A-D])(?:[ \t\xa0]{2,}(.*?))?\s*$")


@dataclass(slots=True)
class ParsedCandidate:
    number: int
    question_text: str
    options: list[tuple[int, str]]
    correct_option: int | None
    raw_text: str


def parse_text_candidates(text: str) -> list[ParsedCandidate]:
    """Extract review candidates from imperfect PDF text.

    This never marks content verified because equations, columns and image options
    can be damaged during PDF text extraction.
    """
    matches = list(QUESTION_START.finditer(text))
    results: list[ParsedCandidate] = []

    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.end():end].strip()
        if not block:
            continue

        answer_match = ANSWER_LINE.search(block)
        answer: int | None = None
        if answer_match:
            token = answer_match.group(1).upper()
            answer = "ABCD".index(token) + 1 if token in "ABCD" else int(token)

        option_matches = list(OPTION_LINE.finditer(block))
        options: list[tuple[int, str]] = []
        for option_match in option_matches[:4]:
            position = "ABCD".index(option_match.group(1)) + 1
            options.append((position, (option_match.group(2) or "").strip()))

        first_option_at = option_matches[0].start() if option_matches else len(block)
        question_text = block[:first_option_at].strip()

        if question_text and len(options) >= 2:
            results.append(
                ParsedCandidate(
                    number=int(match.group(1)),
                    question_text=question_text,
                    options=options,
                    correct_option=answer,
                    raw_text=block,
                )
            )

    return results
