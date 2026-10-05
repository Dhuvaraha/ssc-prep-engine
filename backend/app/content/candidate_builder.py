from app.content.text_parser import ParsedCandidate
from app.content.topic_tagger import suggest_topic


VISUAL_MARKERS = (
    "figure",
    "mirror image",
    "paper is folded",
    "when unfolded",
    "dice",
    "venn diagram",
    "diagram",
    "graph",
    "histogram",
    "pie chart",
)


def build_review_candidate(
    candidate: ParsedCandidate,
    *,
    exam_slug: str,
    subject_slug: str,
    year: int | None,
    shift: str | None,
    source_reference: str,
) -> dict:
    topic_slug, confidence = suggest_topic(subject_slug, candidate.question_text)
    normalized = candidate.question_text.lower()
    requires_visual_review = any(marker in normalized for marker in VISUAL_MARKERS)

    return {
        "exam_slug": exam_slug,
        "subject_slug": subject_slug,
        "topic_slug": topic_slug,
        "topic_confidence": confidence,
        "question_number": candidate.number,
        "question_text": candidate.question_text,
        "options": [
            {"position": position, "text": text}
            for position, text in candidate.options
        ],
        "correct_option": candidate.correct_option,
        "year": year,
        "shift": shift,
        "source_type": "user_private",
        "source_reference": source_reference,
        "visibility": "private",
        "verification_status": "review_required",
        "requires_visual_review": requires_visual_review,
        "raw_text": candidate.raw_text,
    }
