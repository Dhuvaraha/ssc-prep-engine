import re


SECTION_ALIASES = {
    "general intelligence and reasoning": "reasoning",
    "general intelligence & reasoning": "reasoning",
    "general awareness": "general-awareness",
    "quantitative aptitude": "quant",
    "english comprehension": "english",
}

ANSWER_TOKEN = re.compile(r"(?<!\d)(\d{1,3})\s*\.\s*([A-D])\b", re.IGNORECASE)


def parse_answer_page(text: str) -> dict[tuple[str, int], int]:
    """Parse sectioned answer-key text from a CGL page.

    Returns {(subject_slug, question_number): option_position}.
    """
    if "answer" not in text.lower():
        return {}

    normalized = text.lower()
    headings: list[tuple[int, str, str]] = []
    for heading, slug in SECTION_ALIASES.items():
        start = 0
        while True:
            index = normalized.find(heading, start)
            if index < 0:
                break
            headings.append((index, heading, slug))
            start = index + len(heading)

    headings.sort(key=lambda item: item[0])
    answers: dict[tuple[str, int], int] = {}

    for idx, (position, heading, slug) in enumerate(headings):
        body_start = position + len(heading)
        body_end = headings[idx + 1][0] if idx + 1 < len(headings) else len(text)
        body = text[body_start:body_end]
        for match in ANSWER_TOKEN.finditer(body):
            number = int(match.group(1))
            option = "ABCD".index(match.group(2).upper()) + 1
            answers[(slug, number)] = option

    return answers
