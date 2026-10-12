-- Read-only aggregate screen. Numeric-normalized repeats are candidates, not
-- proof of semantic duplication. Never use this output to delete or relabel rows.
WITH base AS (
    SELECT q.*, regexp_replace(lower(q.question_text), '[0-9]+', '#', 'g') AS template
    FROM questions q JOIN exams e ON e.id = q.exam_id
    WHERE e.slug = 'ssc-cgl-tier-1' AND q.verification_status = 'verified'
), counts AS (
    SELECT topic_id, count(*) AS verified_questions,
        count(*) FILTER (WHERE length(coalesce(explanation, '')) < 90) AS brief_solution_review,
        count(*) FILTER (WHERE nullif(trim(source_reference), '') IS NULL) AS source_reference_review,
        count(*) - count(DISTINCT template) AS template_repeat_candidates
    FROM base GROUP BY topic_id
)
SELECT s.slug AS subject, t.name AS topic,
    EXISTS (SELECT 1 FROM lessons l WHERE l.topic_id = t.id AND l.is_published) AS lesson_published,
    coalesce(c.verified_questions, 0) AS verified_questions,
    coalesce(c.brief_solution_review, 0) AS brief_solution_review,
    coalesce(c.source_reference_review, 0) AS source_reference_review,
    coalesce(c.template_repeat_candidates, 0) AS template_repeat_candidates
FROM topics t JOIN subjects s ON s.id = t.subject_id
JOIN exams e ON e.id = s.exam_id LEFT JOIN counts c ON c.topic_id = t.id
WHERE e.slug = 'ssc-cgl-tier-1' ORDER BY s.slug, t.name;
