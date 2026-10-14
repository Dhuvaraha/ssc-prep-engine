"""Offline editorial screen for deep four-option teaching content.

This evaluates coverage and revision binding, NOT the truth of a fact or the
quality of pedagogy. It never publishes content or selects assessment answers.
"""
from collections.abc import Mapping, Sequence

REVIEWED_INSIGHT = "published"
REVIEWED_NOT_DIAGNOSTIC = "reviewed_not_diagnostic"


def evaluate_four_option_readiness(
    question: Mapping,
    reviews: Sequence[Mapping],
) -> dict:
    """Return fail-closed review gaps without exposing protected question text.

    The caller must supply editorially reviewed evidence for the exact captured
    question/answer revision. Existing unversioned option insight rows do not
    automatically qualify. Structural checks cannot certify factual accuracy.
    """
    problems: list[str] = []
    positions = [o.get("position") for o in question.get("options", [])]
    if len(positions) != 4 or any(type(p) is not int or p < 1 for p in positions) or len(set(positions)) != 4:
        problems.append("exactly_four_distinct_option_positions_required")

    key = question.get("correct_option")
    if type(key) is not int or key not in positions:
        problems.append("answer_key_not_in_options")

    question_revision = question.get("question_revision")
    answer_version = question.get("answer_version")
    if not isinstance(question_revision, str) or not question_revision.strip():
        problems.append("question_revision_missing")
    if not isinstance(answer_version, str) or not answer_version.strip():
        problems.append("answer_version_missing")

    if not isinstance(question.get("correct_explanation"), str) or not question["correct_explanation"].strip():
        problems.append("reviewed_correct_solution_missing")
    if question.get("correct_solution_reviewed") is not True or not _nonempty(question.get("correct_review_reference")):
        problems.append("correct_solution_editorial_evidence_missing")

    subject = question.get("subject")
    if subject not in {"general-awareness", "english", "quant", "reasoning"}:
        problems.append("unsupported_or_missing_subject")

    by_position: dict[int, Mapping] = {}
    for review in reviews:
        pos = review.get("position")
        if type(pos) is not int or pos not in positions or pos == key or pos in by_position:
            problems.append("invalid_duplicate_or_out_of_scope_option_review")
            continue
        by_position[pos] = review

    option_status: dict[int, str] = {}
    for pos in positions:
        if pos == key:
            option_status[pos] = "correct_solution_checked" if not any(
                p in problems for p in ("reviewed_correct_solution_missing", "correct_solution_editorial_evidence_missing")
            ) else "correct_solution_incomplete"
            continue
        review = by_position.get(pos)
        if review is None:
            option_status[pos] = "missing_review"
            problems.append(f"option_{pos}:missing_review")
            continue
        if review.get("question_revision") != question_revision or review.get("answer_version") != answer_version:
            option_status[pos] = "stale_or_unbound_review"
            problems.append(f"option_{pos}:stale_or_unbound_review")
            continue
        if not _nonempty(review.get("review_reference")) or not review.get("reviewed_at"):
            option_status[pos] = "unreviewed"
            problems.append(f"option_{pos}:independent_review_missing")
            continue

        status = review.get("status")
        if status == REVIEWED_INSIGHT:
            if not _nonempty(review.get("knowledge_text")) or not _nonempty(review.get("basis_reference")):
                option_status[pos] = "explanation_or_evidence_missing"
                problems.append(f"option_{pos}:explanation_or_evidence_missing")
            else:
                option_status[pos] = "reviewed_insight_present"
        elif status == REVIEWED_NOT_DIAGNOSTIC and subject in {"quant", "reasoning"}:
            if not _nonempty(review.get("reason")):
                option_status[pos] = "non_diagnostic_rationale_missing"
                problems.append(f"option_{pos}:non_diagnostic_rationale_missing")
            else:
                option_status[pos] = "reviewed_not_diagnostic"
        else:
            option_status[pos] = "unapproved_or_unsupported_status"
            problems.append(f"option_{pos}:unapproved_or_unsupported_status")

    return {
        "status": "structurally_ready_for_editorial_signoff" if not problems else "requires_review",
        "problems": problems,
        "option_status": option_status,
        "factual_accuracy_certified": False,
        "learner_published": False,
    }


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())
