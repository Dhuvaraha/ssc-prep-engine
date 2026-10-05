from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Exam, Question, Subject, User
from app.services.mock_engine import create_mock_attempt, submit_mock_attempt


def test_mini_mock_generation_and_scoring():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as db:
        user = User(email="test@example.com", password_hash="x")
        exam = Exam(
            slug="ssc-cgl-tier-1",
            name="SSC CGL Tier I",
            duration_minutes=60,
            positive_marks=2.0,
            negative_marks=0.5,
        )
        db.add_all([user, exam])
        db.flush()

        for index, slug in enumerate(
            ["reasoning", "general-awareness", "quant", "english"],
            start=1,
        ):
            subject = Subject(
                exam_id=exam.id,
                slug=slug,
                name=slug,
                sort_order=index,
            )
            db.add(subject)
            db.flush()
            db.add(
                Question(
                    exam_id=exam.id,
                    subject_id=subject.id,
                    question_text=f"{slug} question",
                    correct_option=1,
                    verification_status="verified",
                    difficulty=1,
                )
            )

        db.commit()

        attempt, rows = create_mock_attempt(
            db,
            user_id=user.id,
            mode="mini",
            subject_slug=None,
        )

        assert attempt.duration_minutes == 4
        assert len(rows) == 4

        for index, (row, _) in enumerate(rows):
            row.selected_option = 1 if index < 3 else 2
        db.commit()

        result = submit_mock_attempt(db, attempt=attempt, rows=rows)

        assert result["correct"] == 3
        assert result["incorrect"] == 1
        assert result["unattempted"] == 0
        assert result["score"] == 5.5
