import re
from dataclasses import dataclass


QUESTION_START = re.compile(r"(?m)^\s*Q\.(\d{1,3})\s+")
OPTION_START = re.compile(r"(?m)^\s*(?:Ans\s*)?([1-4])\.\s*(.*)$")
QUESTION_ID = re.compile(r"Question ID\s*:\s*(\d+)", re.IGNORECASE)
STATUS = re.compile(r"Status\s*:\s*([^\n]+(?:\n(?!Chosen Option)[^\n]+)?)", re.IGNORECASE)
CHOSEN_OPTION = re.compile(r"Chosen Option\s*:\s*(--|[1-4])", re.IGNORECASE)


@dataclass(slots=True)
class CandidateResponseQuestion:
    number: int
    question_text: str
    options: list[tuple[int, str]]
    question_id: str | None
    status: str | None
    chosen_option: int | None
    correct_option: int | None
    raw_text: str


def parse_candidate_response(text: str) -> list[CandidateResponseQuestion]:
    matches = list(QUESTION_START.finditer(text))
    results: list[CandidateResponseQuestion] = []

    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.end():end].strip()
        if not block:
            continue

        question_id_match = QUESTION_ID.search(block)
        status_match = STATUS.search(block)
        chosen_match = CHOSEN_OPTION.search(block)

        option_matches = list(OPTION_START.finditer(block))
        options: list[tuple[int, str]] = []

        first_option_at = option_matches[0].start() if option_matches else len(block)
        question_text = block[:first_option_at].strip()

        for option_index, option_match in enumerate(option_matches[:4]):
            option_end = (
                option_matches[option_index + 1].start()
                if option_index + 1 < len(option_matches[:4])
                else len(block)
            )
            option_text = block[option_match.start(2):option_end]
            option_text = re.split(
                r"\nQuestion ID\s*:|\nOption\s+\d+\s+ID\s*:|\nStatus\s*:|\nChosen Option\s*:",
                option_text,
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0]
            options.append((int(option_match.group(1)), re.sub(r"\s+", " ", option_text).strip()))

        chosen_option = None
        if chosen_match and chosen_match.group(1) != "--":
            chosen_option = int(chosen_match.group(1))

        if question_text and len(options) >= 2:
            results.append(
                CandidateResponseQuestion(
                    number=int(match.group(1)),
                    question_text=re.sub(r"\s+", " ", question_text).strip(),
                    options=options,
                    question_id=question_id_match.group(1) if question_id_match else None,
                    status=re.sub(r"\s+", " ", status_match.group(1)).strip() if status_match else None,
                    chosen_option=chosen_option,
                    correct_option=None,
                    raw_text=block,
                )
            )

    return results
