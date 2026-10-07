from __future__ import annotations

import re
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Exam, Question, QuestionOption, Subject, Topic


_NUMBER_RE = re.compile(
    r"^\s*([+-]?\d+(?:\.\d+)?)"
    r"(\s*(?:%|°|km|m|cm|mm|kg|g|years?|days?|hours?|minutes?|seconds?|st|nd|rd|th)?)\s*$",
    re.IGNORECASE,
)
_FRACTION_RE = re.compile(r"^\s*([+-]?\d+)\s*/\s*(\d+)(.*)$")
_RATIO_RE = re.compile(r"^\s*([+-]?\d+)\s*:\s*([+-]?\d+)(.*)$")
_ALPHA_TOKEN_RE = re.compile(r"^[A-Za-z]+$")


def _normalise_text(value: str | None) -> str:
    return " ".join((value or "").split()).casefold()


def _identity(option: QuestionOption) -> tuple[str, str]:
    return (
        _normalise_text(option.text),
        (option.image_url or "").strip(),
    )


def _candidate_is_available(candidate: str, existing: set[str]) -> bool:
    return bool(candidate.strip()) and _normalise_text(candidate) not in existing


def _format_decimal_like(original: str, value: Decimal) -> str:
    if "." in original:
        decimals = len(original.split(".", 1)[1])
        return f"{value:.{decimals}f}"
    return str(int(value))


def _numeric_candidate(text: str, existing: set[str]) -> str | None:
    match = _NUMBER_RE.match(text)
    if not match:
        return None

    raw_number, suffix = match.groups()
    try:
        number = Decimal(raw_number)
    except InvalidOperation:
        return None

    if "." in raw_number:
        decimals = len(raw_number.split(".", 1)[1])
        smallest = Decimal(1).scaleb(-decimals)
        deltas = [
            smallest,
            -smallest,
            smallest * 2,
            -smallest * 2,
            Decimal(1),
            Decimal(-1),
        ]
    else:
        deltas = [
            Decimal(1),
            Decimal(-1),
            Decimal(2),
            Decimal(-2),
            Decimal(5),
            Decimal(-5),
            Decimal(10),
            Decimal(-10),
        ]

    for delta in deltas:
        candidate_number = number + delta
        candidate = _format_decimal_like(raw_number, candidate_number) + suffix
        if _candidate_is_available(candidate, existing):
            return candidate
    return None


def _fraction_candidate(text: str, existing: set[str]) -> str | None:
    match = _FRACTION_RE.match(text)
    if not match:
        return None
    numerator, denominator, suffix = match.groups()
    n = int(numerator)
    d = int(denominator)
    if d == 0:
        return None

    for delta in (1, -1, 2, -2):
        candidate = f"{n + delta}/{d}{suffix}"
        if _candidate_is_available(candidate, existing):
            return candidate
    for delta in (1, 2):
        candidate = f"{n}/{d + delta}{suffix}"
        if _candidate_is_available(candidate, existing):
            return candidate
    return None


def _ratio_candidate(text: str, existing: set[str]) -> str | None:
    match = _RATIO_RE.match(text)
    if not match:
        return None
    left, right, suffix = match.groups()
    a = int(left)
    b = int(right)
    for delta in (1, -1, 2, -2):
        candidate = f"{a + delta}:{b}{suffix}"
        if _candidate_is_available(candidate, existing):
            return candidate
    for delta in (1, -1, 2, -2):
        candidate = f"{a}:{b + delta}{suffix}"
        if _candidate_is_available(candidate, existing):
            return candidate
    return None


def _word_candidate(text: str, existing: set[str]) -> str | None:
    stripped = text.strip()
    if not _ALPHA_TOKEN_RE.fullmatch(stripped) or len(stripped) < 2:
        return None

    alphabet = "abcdefghijklmnopqrstuvwxyz"
    for offset in (1, 2, 3, -1):
        last = stripped[-1]
        index = alphabet.index(last.lower())
        replacement = alphabet[(index + offset) % 26]
        if last.isupper():
            replacement = replacement.upper()
        candidate = stripped[:-1] + replacement
        if _candidate_is_available(candidate, existing):
            return candidate

    if len(stripped) >= 3:
        candidate = stripped[:-1]
        if _candidate_is_available(candidate, existing):
            return candidate
    return None


def _trigonometry_candidate(existing: set[str]) -> str | None:
    pool = (
        "0",
        "1",
        "-1",
        "1/2",
        "√2/2",
        "√3/2",
        "1/√2",
        "1/√3",
        "√3",
        "2",
        "30°",
        "45°",
        "60°",
        "90°",
    )
    for candidate in pool:
        if _candidate_is_available(candidate, existing):
            return candidate
    return None


def _replacement_text(
    *,
    topic_slug: str,
    duplicate_text: str,
    existing: set[str],
) -> tuple[str, str]:
    candidate = _numeric_candidate(duplicate_text, existing)
    if candidate is not None:
        return candidate, "numeric"

    candidate = _fraction_candidate(duplicate_text, existing)
    if candidate is not None:
        return candidate, "fraction"

    candidate = _ratio_candidate(duplicate_text, existing)
    if candidate is not None:
        return candidate, "ratio"

    if topic_slug == "trigonometry":
        candidate = _trigonometry_candidate(existing)
        if candidate is not None:
            return candidate, "trigonometry-pool"

    if topic_slug in {"spelling", "letter-series"}:
        candidate = _word_candidate(duplicate_text, existing)
        if candidate is not None:
            return candidate, "word-mutation"

    for candidate in ("None of these", "None of the above"):
        if _candidate_is_available(candidate, existing):
            return candidate, "none-of-these"

    raise ValueError("Could not create a safe unique distractor")


def _load_verified_questions(db: Session, exam_id: int) -> list[Question]:
    return list(
        db.scalars(
            select(Question)
            .options(selectinload(Question.options))
            .where(
                Question.exam_id == exam_id,
                Question.verification_status == "verified",
            )
            .order_by(Question.id)
        ).unique()
    )


def build_content_repair_plan(
    db: Session,
    *,
    exam_slug: str = "ssc-cgl-tier-1",
) -> dict:
    exam = db.scalar(select(Exam).where(Exam.slug == exam_slug))
    if not exam:
        raise ValueError("Exam not found")

    topics = {
        topic.id: topic
        for topic in db.scalars(
            select(Topic)
            .join(Subject, Subject.id == Topic.subject_id)
            .where(Subject.exam_id == exam.id)
        )
    }

    strategies: Counter[str] = Counter()
    duplicate_questions = 0
    replacement_count = 0
    correct_payload_duplicates = 0
    unsupported_image_duplicates = 0
    planned_replacements: list[tuple[QuestionOption, str, str]] = []
    missing_pattern_questions: list[tuple[Question, str]] = []

    for question in _load_verified_questions(db, exam.id):
        topic = topics.get(question.topic_id) if question.topic_id is not None else None
        topic_slug = topic.slug if topic else "unassigned"

        groups: dict[tuple[str, str], list[QuestionOption]] = defaultdict(list)
        for option in question.options:
            groups[_identity(option)].append(option)

        repeated = [rows for identity, rows in groups.items() if identity != ("", "") and len(rows) > 1]
        if repeated:
            duplicate_questions += 1

        existing = {_normalise_text(option.text) for option in question.options if option.text}

        for rows in repeated:
            correct_row = next(
                (row for row in rows if row.position == question.correct_option),
                None,
            )
            keep = correct_row or min(rows, key=lambda row: row.position)
            if correct_row is not None:
                correct_payload_duplicates += 1

            for option in rows:
                if option.id == keep.id:
                    continue
                if option.image_url:
                    unsupported_image_duplicates += 1
                    strategies["unsupported-image"] += 1
                    continue

                replacement, strategy = _replacement_text(
                    topic_slug=topic_slug,
                    duplicate_text=option.text or "",
                    existing=existing,
                )
                existing.add(_normalise_text(replacement))
                planned_replacements.append((option, replacement, strategy))
                strategies[strategy] += 1
                replacement_count += 1

        if not question.pattern_type or not question.pattern_type.strip():
            pattern = f"{topic_slug}-core"
            missing_pattern_questions.append((question, pattern))

    return {
        "exam_slug": exam.slug,
        "duplicate_questions": duplicate_questions,
        "replacement_count": replacement_count,
        "correct_payload_duplicates": correct_payload_duplicates,
        "unsupported_image_duplicates": unsupported_image_duplicates,
        "missing_pattern_count": len(missing_pattern_questions),
        "strategies": dict(strategies.most_common()),
        "_replacements": planned_replacements,
        "_patterns": missing_pattern_questions,
    }


def serialise_repair_plan(plan: dict) -> dict:
    return {
        key: value
        for key, value in plan.items()
        if not key.startswith("_")
    }


def repair_content_integrity(
    db: Session,
    *,
    exam_slug: str = "ssc-cgl-tier-1",
    apply: bool = False,
) -> dict:
    plan = build_content_repair_plan(db, exam_slug=exam_slug)
    public_plan = serialise_repair_plan(plan)

    if not apply:
        return public_plan

    if plan["unsupported_image_duplicates"]:
        raise ValueError("Repair plan contains unsupported duplicate image options")

    for option, replacement, _ in plan["_replacements"]:
        option.text = replacement

    for question, pattern in plan["_patterns"]:
        question.pattern_type = pattern

    db.commit()
    return public_plan
