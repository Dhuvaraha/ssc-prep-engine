from __future__ import annotations

from dataclasses import dataclass


VISUAL_REASONING_TOPICS = {
    "counting-figures",
    "dice-and-cubes",
    "embedded-figures",
    "figure-series",
    "mirror-and-water-images",
    "paper-folding-and-cutting",
}

DYNAMIC_GA_TOPICS = {
    "current-affairs",
    "sports",
    "awards-and-honours",
}


@dataclass(frozen=True)
class TopicReadiness:
    subject_slug: str
    topic_slug: str
    verified_questions: int
    lesson_blocks: int
    archetypes: int
    flashcards: int
    visual_questions: int = 0
    official_questions: int = 0
    newest_year: int | None = None


def readiness_failures(item: TopicReadiness, *, current_year: int = 2026) -> list[str]:
    failures: list[str] = []

    if item.subject_slug in {"reasoning", "quant", "english"}:
        if item.verified_questions < 100:
            failures.append("verified_questions<100")
        if item.lesson_blocks < 10:
            failures.append("lesson_blocks<10")
        if item.archetypes < 8:
            failures.append("archetypes<8")

    if item.subject_slug == "general-awareness":
        if item.topic_slug in DYNAMIC_GA_TOPICS:
            if item.verified_questions < 20:
                failures.append("verified_questions<20")
            if item.official_questions < 15:
                failures.append("official_questions<15")
            if item.newest_year is None or item.newest_year < current_year:
                failures.append("dynamic_content_not_current")
            if item.flashcards < 15:
                failures.append("flashcards<15")
        else:
            if item.verified_questions < 30:
                failures.append("verified_questions<30")
            if item.flashcards < 25:
                failures.append("flashcards<25")
        if item.lesson_blocks < 10:
            failures.append("lesson_blocks<10")
        if item.archetypes < 8:
            failures.append("archetypes<8")

    if item.topic_slug in VISUAL_REASONING_TOPICS and item.visual_questions < 50:
        failures.append("visual_questions<50")

    return failures


def is_topic_ready(item: TopicReadiness, *, current_year: int = 2026) -> bool:
    return not readiness_failures(item, current_year=current_year)
