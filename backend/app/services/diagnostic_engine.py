"""CGL Tier-I starting diagnostic: a *sample*, never an exam-readiness score.

Blueprint: four subjects × (3 foundation, 5 application, 2 challenge),
24 minutes, verified and independently answerable questions only. The
question bank does not disclose its answers until a completed submission.
"""
from collections import defaultdict

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import MockAttempt, MockAttemptQuestion, Question, Subject
from app.services.mock_engine import _hydrate_questions
from app.services.question_quality import unique_questions

DIAGNOSTIC_SLUGS = ("reasoning", "general-awareness", "quant", "english")
DIFFICULTY_COUNTS = ((1, 3), (2, 5), (3, 2))
DIAGNOSTIC_MINUTES = 24


def _valid_options(question: Question) -> bool:
    options = question.options
    if len(options) != 4 or {o.position for o in options} != {1, 2, 3, 4}:
        return False
    values = [(o.text or "").strip().casefold() or "img:" + (o.image_url or "").strip()
              for o in options]
    return all(values) and len(set(values)) == 4 and question.correct_option in {1, 2, 3, 4}


def select_diagnostic_questions(db: Session, *, exam_id: int, user_id: int) -> list[tuple[str, Question]]:
    """Select a consistent blueprint without reusing a prior submitted diagnostic.

    If the verified pool is insufficient, do not silently substitute easier
    items or claim comparable results. Previous diagnostic questions are held
    out for future independent assessments.
    """
    prior_ids = set(db.scalars(
        select(MockAttemptQuestion.question_id)
        .join(MockAttempt, MockAttempt.id == MockAttemptQuestion.attempt_id)
        .where(
            MockAttempt.user_id == user_id,
            MockAttempt.exam_id == exam_id,
            MockAttempt.mode == "diagnostic",
            MockAttempt.status == "submitted",
        )
    ))
    selection = []
    used_ids = set()
    for slug in DIAGNOSTIC_SLUGS:
        subject = db.scalar(select(Subject).where(Subject.exam_id == exam_id, Subject.slug == slug))
        if subject is None:
            raise ValueError(f"Diagnostic syllabus missing subject: {slug}")

        chosen = []
        topic_usage = defaultdict(int)
        pattern_usage = defaultdict(int)
        for difficulty, count in DIFFICULTY_COUNTS:
            # Round-robin candidate diversity by topic and archetype. Ranking
            # happens in SQL; we hydrate only a bounded window of option rows.
            ranked = (
                select(
                    Question.id.label("question_id"),
                    func.row_number().over(
                        partition_by=(Question.topic_id, Question.pattern_type),
                        order_by=(
                            case((Question.source_type == "official", 0), else_=1),
                            Question.id,
                        ),
                    ).label("rank"),
                )
                .where(
                    Question.exam_id == exam_id,
                    Question.subject_id == subject.id,
                    Question.difficulty == difficulty,
                    Question.verification_status == "verified",
                    Question.correct_option.in_((1, 2, 3, 4)),
                    Question.requires_visual_review.is_(False),
                    *([Question.id.not_in(prior_ids)] if prior_ids else []),
                )
                .subquery()
            )
            ids = list(db.scalars(
                select(ranked.c.question_id)
                .where(ranked.c.rank <= 10)
                .order_by(ranked.c.rank, ranked.c.question_id)
                .limit(300)
            ))
            candidates = unique_questions(_hydrate_questions(db, ids))
            candidates = [q for q in candidates if _valid_options(q) and q.id not in used_ids]
            candidates.sort(key=lambda q: (
                topic_usage[q.topic_id],
                pattern_usage[(q.topic_id, q.pattern_type)],
                q.id,
            ))
            picked = candidates[:count]
            if len(picked) != count:
                raise ValueError(
                    f"Insufficient verified, non-repeated {slug} difficulty {difficulty} "
                    f"diagnostic questions: need {count}, found {len(picked)}"
                )
            for question in picked:
                topic_usage[question.topic_id] += 1
                pattern_usage[(question.topic_id, question.pattern_type)] += 1
                used_ids.add(question.id)
            chosen.extend(picked)

        selection.extend((slug, q) for q in chosen)

    if len(selection) != 40 or len({q.id for _, q in selection}) != 40:
        raise ValueError("Diagnostic integrity failed: expected 40 distinct questions")
    return selection
