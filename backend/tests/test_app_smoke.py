def test_application_imports():
    from app.main import app

    assert app.title == "SSC Prep Engine API"


def test_all_tables_register():
    from app.db import Base
    __import__("app.models")

    expected = {
        "users",
        "exams",
        "subjects",
        "topics",
        "questions",
        "question_options",
        "question_attempts",
        "topic_mastery",
        "revision_items",
        "lessons",
        "mock_attempts",
        "mock_attempt_questions",
        "bookmarks",
        "flashcards",
        "flashcard_progress",
        "exam_targets",
        "daily_plan_tasks",
    }
    assert expected.issubset(set(Base.metadata.tables))
