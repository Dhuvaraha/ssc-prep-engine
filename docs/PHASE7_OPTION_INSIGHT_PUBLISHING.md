# Phase 7C — Verified Four-Option Knowledge Explorer

Status: **foundation implemented, editorial content not yet populated**.
This feature supplements, rather than changes, the official answer key.

## What is shipped in this slice

- Additive `question_option_insights` table. Original 10k+ questions, four choices, attempts, mastery, lessons, and mock data are unchanged.
- For each alternative **incorrect** choice, a reviewer may curate a supported fact, rule, misconception, or comparison, and optionally a **different** question where that alternative genuinely applies.
- Practice submission returns only source-referenced insights with `review_status = published` and non-null `reviewed_at`. Nothing is returned by the initial question fetch, so active MCQ practice cannot use this API to reveal the answer.
- Frontend shows a collapsed “Learn this option” note after answer grading; missing insights remain explicit rather than fabricated.
- Human-reviewed publication is a required gate. No AI-generated drafts get auto-published.

## Minimum requirements before an insight is published

1. Check its existing question ID, option position and verified correct answer. An insight only belongs to an incorrect option, **not** the correct choice.
2. Identify the option's true meaning or the particular mathematical mistake it represents. Not all arbitrary numbers can be answers to another legitimate question.
3. Provide `knowledge_text` with an accurate, concise explanation. For GA provide a trustworthy original source and a date/year where relevant.
4. If `related_question` is present, `related_answer` must also be present and independently correct, **not** guessed from word overlap.
5. Mark as `draft` during preparation. Reviewer must verify chronology and primary source and record `reviewed_at` before `published`.
6. For English, explain usage; for Quant, demonstrate a valid alternative calculation trap; for Reasoning, show pattern logic; for JE, show engineering units and assumptions.
7. Verify no exact question leakage into current timed/mock tests and no non-public/private source is exposed in `source_reference`.

## Backlog

- Pilot 3–5 questions each from GA, English, Quant and Reasoning, including the Budget question. Review all 3 incorrect options on each, with source, content type and at least one related quiz where scientifically valid.
- Audit the pilot with a subject reviewer, then expand in small batches; log corrections, review changes, and rollback path.
- Add backend-approved “Save this fact to revision” feature after published insights and source provenance pass QA.
- Extend to mock review only after submission and exam-stage safeguards, never during an active timed section.
- Add a reviewed-content authoring interface and independent audit of all published insights.

**Do not claim** that any of the existing answer options has a published alternate fact until data has actually been curated and reviewed.
