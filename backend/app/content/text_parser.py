import re
from dataclasses import dataclass


QUESTION_START = re.compile(r"(?m)^\s*(\d{1,3})[.)]\s+")
ANSWER_LINE = re.compile(r"(?im)^\s*Answer\s*:\s*([A-D1-4])\s*$")
OPTION_LINE = re.compile(r"(?m)^[ \t\xa0]*([A-D])(?:[ \t\xa0]+(.*?))?[ \t\xa0]*$")


@dataclass(slots=True)
class ParsedCandidate:
    number: int
    question_text: str
    options: list[tuple[int, str]]
    correct_option: int | None
    raw_text: str


def _last_abcd_sequence(matches: list[re.Match[str]]) -> list[re.Match[str]]:
    """Return the last ordered A→B→C→D sequence.

    Taking the last complete sequence avoids treating question-body lines such as
    "A can complete the work..." as answer option A.
    """
    sequences: list[list[re.Match[str]]] = []
    for start, match in enumerate(matches):
        if match.group(1) != "A":
            continue
        sequence = [match]
        expected = iter(("B", "C", "D"))
        target = next(expected, None)
        for later in matches[start + 1:]:
            if later.group(1) == target:
                sequence.append(later)
                target = next(expected, None)
                if target is None:
                    sequences.append(sequence)
                    break
    return sequences[-1] if sequences else []


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

        option_matches = _last_abcd_sequence(list(OPTION_LINE.finditer(block)))
        if not option_matches:
            continue

        options: list[tuple[int, str]] = []
        for option_match in option_matches:
            position = "ABCD".index(option_match.group(1)) + 1
            options.append((position, (option_match.group(2) or "").strip()))

        first_option_at = option_matches[0].start()
        question_text = block[:first_option_at].strip()

        if question_text:
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
