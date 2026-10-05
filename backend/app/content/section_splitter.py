import re
from dataclasses import dataclass


SUBJECT_HEADINGS = {
    "general intelligence and reasoning": "reasoning",
    "general intelligence & reasoning": "reasoning",
    "reasoning": "reasoning",
    "general awareness": "general-awareness",
    "quantitative aptitude": "quant",
    "quant": "quant",
    "english comprehension": "english",
    "english": "english",
}

SHIFT_PATTERN = re.compile(
    r"(?i)(?:ssc\s+cgl[^\n]*?)?(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+20\d{2})?[^\n]{0,80}?(shift[-\s]?\d+)"
)


@dataclass(slots=True)
class PageContext:
    subject_slug: str | None
    shift_label: str | None


def detect_subject(text: str, current: str | None = None) -> str | None:
    normalized = re.sub(r"\s+", " ", text).lower()
    best: tuple[int, str] | None = None
    for heading, slug in SUBJECT_HEADINGS.items():
        index = normalized.find(heading)
        if index >= 0 and (best is None or index < best[0]):
            best = (index, slug)
    return best[1] if best else current


def detect_shift(text: str, current: str | None = None) -> str | None:
    match = SHIFT_PATTERN.search(text)
    if not match:
        return current
    date_part = (match.group(1) or "").strip()
    shift_part = match.group(2).replace(" ", "-")
    return f"{date_part} {shift_part}".strip()
