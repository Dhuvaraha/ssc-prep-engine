from app.content.readiness import TopicReadiness, is_topic_ready, readiness_failures


def test_reasoning_topic_requires_deep_bank():
    item = TopicReadiness(
        subject_slug="reasoning",
        topic_slug="blood-relations",
        verified_questions=100,
        lesson_blocks=12,
        archetypes=10,
        flashcards=5,
    )
    assert is_topic_ready(item)


def test_visual_reasoning_requires_visual_bank():
    item = TopicReadiness(
        subject_slug="reasoning",
        topic_slug="figure-series",
        verified_questions=105,
        lesson_blocks=12,
        archetypes=10,
        flashcards=2,
        visual_questions=20,
    )
    assert "visual_questions<50" in readiness_failures(item)


def test_static_ga_uses_fact_and_flashcard_thresholds():
    item = TopicReadiness(
        subject_slug="general-awareness",
        topic_slug="history",
        verified_questions=35,
        lesson_blocks=14,
        archetypes=10,
        flashcards=32,
    )
    assert is_topic_ready(item)


def test_dynamic_ga_requires_official_current_sources():
    item = TopicReadiness(
        subject_slug="general-awareness",
        topic_slug="current-affairs",
        verified_questions=20,
        lesson_blocks=12,
        archetypes=10,
        flashcards=17,
        official_questions=15,
        newest_year=2026,
    )
    assert is_topic_ready(item, current_year=2026)

    stale = TopicReadiness(
        subject_slug="general-awareness",
        topic_slug="current-affairs",
        verified_questions=20,
        lesson_blocks=12,
        archetypes=10,
        flashcards=17,
        official_questions=15,
        newest_year=2025,
    )
    assert "dynamic_content_not_current" in readiness_failures(stale, current_year=2026)
