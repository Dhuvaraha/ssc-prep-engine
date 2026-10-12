from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Exam, MockAttempt, MockAttemptQuestion, Question, Subject, User
from app.services.mock_engine import _questions_for_subject
from app.services.practice_integrity import expose


def test_mock_prefers_unseen_even_over_official_labels_and_abandoned_exposure():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        user = User(email="exposure@example.test", password_hash="synthetic")
        other = User(email="other@example.test", password_hash="synthetic")
        exam = Exam(slug="ssc-cgl-tier-1", name="Synthetic", duration_minutes=60)
        db.add_all([user, other, exam]); db.flush()
        subject = Subject(exam_id=exam.id, slug="quant", name="Quant")
        db.add(subject); db.flush()
        old = MockAttempt(user_id=user.id, exam_id=exam.id, mode="sectional",
                          subject_slug="quant", duration_minutes=15, status="abandoned")
        db.add(old); db.flush()
        seen, unseen = set(), set()
        for level in (1, 2, 3):
            for i in range(40):
                q = Question(exam_id=exam.id, subject_id=subject.id,
                             question_text=f"Synthetic unique level {level} item {i}",
                             difficulty=level, correct_option=1, verification_status="verified",
                             source_type="official" if i < 20 else "original", year=2026)
                db.add(q); db.flush()
                if i < 20:
                    seen.add(q.id)
                    db.add(MockAttemptQuestion(attempt_id=old.id, question_id=q.id,
                                               section_slug="quant", position=q.id))
                else:
                    unseen.add(q.id)
        db.commit()
        selected = _questions_for_subject(db, exam_id=exam.id, subject_slug="quant", count=25,
                                          user_id=user.id)
        assert len(selected) == 25
        assert {q.id for q in selected} <= unseen
        assert {level: sum(q.difficulty == level for q in selected) for level in (1, 2, 3)} == {1: 7, 2: 12, 3: 6}
        # An exhausted pool still supplies a full mock. It does not quietly shorten
        # the exam, change its blueprint, or pretend repeated questions are unseen.
        all_selected = _questions_for_subject(db, exam_id=exam.id, subject_slug="quant", count=120,
                                              user_id=user.id)
        assert {q.id for q in all_selected} == seen | unseen
        legacy = db.get(Question, min(seen))
        legacy_duplicate = Question(exam_id=exam.id, subject_id=subject.id,
                                    question_text=legacy.question_text, difficulty=legacy.difficulty,
                                    correct_option=1, verification_status="verified")
        db.add(legacy_duplicate); db.commit()
        next_selection = _questions_for_subject(db, exam_id=exam.id, subject_slug="quant", count=25,
                                                user_id=user.id)
        assert legacy_duplicate.id not in {q.id for q in next_selection}
        assert {q.id for q in next_selection} <= unseen
        # Explanations/solved lessons can expose answers before any submission.
        # A matching-content duplicate ID must also lose unseen priority.
        for question in selected:
            expose(db, other.id, question, "solved_example")
        db.commit()
        other_selection = _questions_for_subject(db, exam_id=exam.id, subject_slug="quant", count=25,
                                                 user_id=other.id)
        assert not {q.id for q in selected} & {q.id for q in other_selection}
        duplicate = Question(exam_id=exam.id, subject_id=subject.id,
                             question_text=selected[0].question_text, difficulty=selected[0].difficulty,
                             correct_option=1, verification_status="verified")
        db.add(duplicate); db.commit()
        other_selection = _questions_for_subject(db, exam_id=exam.id, subject_slug="quant", count=25,
                                                 user_id=other.id)
        assert duplicate.id not in {q.id for q in other_selection}
    engine.dispose()
