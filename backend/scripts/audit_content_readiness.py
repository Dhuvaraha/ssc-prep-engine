from __future__ import annotations

from datetime import date

from sqlalchemy import text

from app.content.readiness import TopicReadiness, readiness_failures
from app.db import SessionLocal


QUERY = text("""
SELECT
    s.slug AS subject_slug,
    t.slug AS topic_slug,
    COUNT(DISTINCT q.id) FILTER (WHERE q.verification_status='verified') AS verified_questions,
    COUNT(DISTINCT lb.id) FILTER (WHERE lb.is_published=true) AS lesson_blocks,
    COUNT(DISTINCT a.id) FILTER (WHERE a.is_published=true) AS archetypes,
    COUNT(DISTINCT f.id) FILTER (WHERE f.is_published=true) AS flashcards,
    COUNT(DISTINCT q.id) FILTER (
        WHERE q.verification_status='verified' AND q.question_image_url IS NOT NULL
    ) AS visual_questions,
    COUNT(DISTINCT q.id) FILTER (
        WHERE q.verification_status='verified' AND q.source_type='official'
    ) AS official_questions,
    MAX(q.year) AS newest_year
FROM topics t
JOIN subjects s ON s.id=t.subject_id
LEFT JOIN questions q ON q.topic_id=t.id
LEFT JOIN lessons l ON l.topic_id=t.id
LEFT JOIN lesson_blocks lb ON lb.lesson_id=l.id
LEFT JOIN question_archetypes a ON a.topic_id=t.id
LEFT JOIN flashcards f ON f.topic_id=t.id
GROUP BY s.slug,t.slug
ORDER BY s.slug,t.slug
""")


def main() -> None:
    db = SessionLocal()
    try:
        rows = db.execute(QUERY).mappings().all()
    finally:
        db.close()

    failures = 0
    for row in rows:
        item = TopicReadiness(
            subject_slug=row["subject_slug"],
            topic_slug=row["topic_slug"],
            verified_questions=int(row["verified_questions"] or 0),
            lesson_blocks=int(row["lesson_blocks"] or 0),
            archetypes=int(row["archetypes"] or 0),
            flashcards=int(row["flashcards"] or 0),
            visual_questions=int(row["visual_questions"] or 0),
            official_questions=int(row["official_questions"] or 0),
            newest_year=row["newest_year"],
        )
        problems = readiness_failures(item, current_year=date.today().year)
        status = "READY" if not problems else "PENDING: " + ", ".join(problems)
        print(f"{item.subject_slug:18} {item.topic_slug:42} {status}")
        if problems:
            failures += 1

    print(f"\nTopics checked: {len(rows)} | Pending: {failures}")


if __name__ == "__main__":
    main()
