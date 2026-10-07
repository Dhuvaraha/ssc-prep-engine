from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Exam, Question, Subject, Topic


def _release_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    exam = Exam(
        slug="ssc-cgl-tier-1",
        name="SSC CGL Tier I",
        duration_minutes=60,
        positive_marks=2.0,
        negative_marks=0.5,
    )
    db.add(exam)
    db.flush()

    subject = Subject(
        exam_id=exam.id,
        slug="reasoning",
        name="Reasoning",
        sort_order=1,
    )
    db.add(subject)
    db.flush()

    topic = Topic(
        subject_id=subject.id,
        slug="analogy",
        name="Analogy",
        priority=5,
    )
    db.add(topic)
    db.flush()

    for index in range(10):
        db.add(
            Question(
                exam_id=exam.id,
                subject_id=subject.id,
                topic_id=topic.id,
                question_text=f"HTTP release question {index}",
                correct_option=1,
                verification_status="verified",
                difficulty=(index % 3) + 1,
                expected_time_seconds=30,
                pattern_type=f"release-pattern-{index % 2}",
            )
        )
    db.commit()

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    return TestClient(app), db, topic


def test_http_release_flow_register_plan_mock_review_and_permissions():
    client, db, topic = _release_client()
    try:
        health = client.get("/health")
        assert health.status_code == 200

        preflight = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert preflight.status_code == 200
        assert preflight.headers["access-control-allow-origin"] == "http://localhost:5173"

        registration = client.post(
            "/api/v1/auth/register",
            json={
                "email": "release-http@example.com",
                "password": "Release123!",
                "display_name": " Release QA ",
            },
        )
        assert registration.status_code == 201
        auth = registration.json()
        token = auth["access_token"]
        assert auth["user"]["display_name"] == "Release QA"
        headers = {"Authorization": f"Bearer {token}"}

        me = client.get("/api/v1/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["email"] == "release-http@example.com"

        tree = client.get("/api/v1/content/tree?exam_slug=ssc-cgl-tier-1")
        assert tree.status_code == 200
        assert tree.json()["totals"]["questions"] == 10

        plan = client.put(
            "/api/v1/planner/config",
            headers=headers,
            json={
                "exam_slug": "ssc-cgl-tier-1",
                "exam_date": (date.today() + timedelta(days=30)).isoformat(),
                "daily_minutes": 180,
            },
        )
        assert plan.status_code == 200
        assert plan.json()["target"]["days_left"] >= 29
        assert plan.json()["tasks"]

        started = client.post(
            "/api/v1/mocks/start",
            headers=headers,
            json={"mode": "topic", "topic_id": topic.id, "subject_slug": None},
        )
        assert started.status_code == 200
        attempt = started.json()
        assert len(attempt["questions"]) == 10

        active = client.get("/api/v1/mocks/active/current", headers=headers)
        assert active.status_code == 200
        assert active.json()["attempt_id"] == attempt["attempt_id"]

        question_id = attempt["questions"][0]["question"]["id"]
        saved = client.patch(
            f"/api/v1/mocks/{attempt['attempt_id']}/response",
            headers=headers,
            json={
                "question_id": question_id,
                "selected_option": 1,
                "marked_for_review": False,
                "time_seconds": 12,
            },
        )
        assert saved.status_code == 200

        submitted = client.post(
            f"/api/v1/mocks/{attempt['attempt_id']}/submit",
            headers=headers,
        )
        assert submitted.status_code == 200
        assert submitted.json()["score"] == 2.0

        review = client.get(
            f"/api/v1/mocks/{attempt['attempt_id']}/review",
            headers=headers,
        )
        assert review.status_code == 200
        section = review.json()["sections"]["reasoning"]
        assert section["score"] == 2.0
        assert section["accuracy"] == 100.0

        no_active = client.get("/api/v1/mocks/active/current", headers=headers)
        assert no_active.status_code == 200
        assert no_active.json()["attempt_id"] is None

        review_admin = client.get("/api/v1/review/stats", headers=headers)
        assert review_admin.status_code == 403
    finally:
        app.dependency_overrides.clear()
        client.close()
        db.close()
