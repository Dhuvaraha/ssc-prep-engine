from app.content.candidate_response_parser import CandidateResponseQuestion
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
    candidate: ParsedCandidate | CandidateResponseQuestion,
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

    correct_option = getattr(candidate, "correct_option", None)
    chosen_option = getattr(candidate, "chosen_option", None)
    source_question_id = getattr(candidate, "question_id", None)
    source_status = getattr(candidate, "status", None)

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
        "correct_option": correct_option,
        "year": year,
        "shift": shift,
        "source_type": "user_private",
        "source_reference": source_reference,
        "visibility": "private",
        "verification_status": "review_required",
        "requires_visual_review": requires_visual_review,
        "source_chosen_option": chosen_option,
        "source_question_id": source_question_id,
        "source_status": source_status,
        "raw_text": candidate.raw_text,
    }
