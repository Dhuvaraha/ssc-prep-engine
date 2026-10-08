# Phase 7 — Question Quality Release Gate

**Read-only QA tooling:** from `backend/` run
`python -m scripts.learning_quality_report --exam ssc-cgl-tier-1 --summary-only`.
Omit `--summary-only` for a complete topic-level JSON review. Always use a
read-only database credential or audited staging clone. The tool never writes.

## What constitutes quality — beyond the "verified" database flag
1. **Exam relevancy:** syllabus subtopic and archetype mapped to the *selected* official exam stage/version. No CGL/JE cross-contamination.
2. **Answer integrity:** exactly four distinct, nonempty response choices for MCQs, one correct position, no disputed/ambiguous answer, verified source when appropriate.
3. **Teaching integrity:** one beginner explanation, normal procedure, recognition cues and *why* it works; a genuine short safe method where appropriate. Merely saying "Correct answer: B" is not a worked explanation.
4. **Meaningful progression:** at least five distinct verified questions at each of Easy/Medium/Hard to unlock a level in the new learning path. A **course-ready** topic should exceed this minimum with genuinely distinct patterns, application questions and advanced variations. Repeated wording and simple number swaps don't count as fresh understanding.
5. **Fact verification:** dated and source-traceable static GK/current-affairs facts. Source quality and changing laws/budgets cannot be checked by answer length alone.
6. **Test integrity:** past questions, holdout diagnostic and full mocks have independent question pools. Past exposure and guided hints must not inflate exam-readiness evidence.
7. **Human review:** equations, diagrams, choices, ambiguity, complexity and the exam's latest official notice must pass editorial review before new content is published.

## Initial production metadata baseline (8 Oct 2026; database-only checks)
- SSC CGL Tier I has **74 topics**, four subjects and **10,043 questions tagged verified**, distributed over Easy/Medium/Hard.
- **Current Affairs** had 9 Easy / 10 Medium / **1 Hard**, and **Awards & Honours** had 9 Easy / 10 Medium / **4 Hard**. These fail the five-distinct-question advanced unlock floor.
- Brief solution heuristic: many items across subjects have explanations under 60 characters; a short explanation is a **review flag**, not automatic proof of wrong content. In particular, GA facts and simple arithmetic may need context/source checks rather than verbosity.
- M0-03 adjusted question candidate sampling to avoid hiding Medium/Hard under huge Easy sets; Phase 7 learning-path now holds learners at the last supported level when an advanced set is too thin.

## Editorial backlog and release decision
- P0: invalid answer/options, unverified/stale current-affairs fact, fabricated derivation, source mislabeled or wrong exam.
- P1: weak worked method, missing pattern/difficulty family, excessive question repetition, misleading "exam ready" claim.
- First curated review: Current Affairs and Awards & Honours advanced questions, then GA fact explanations, official syllabus gaps, then English/Quant/Reasoning trap diversity. Do NOT mass-publish AI text into the existing bank.
- For Tier II / JE: keep catalog `planned` until a verified stage-specific syllabus matrix, topic packages, MCQ options/explanations, real exam-timing/marking blueprint and a human-reviewed QA report all pass.
- Reports are a *candidate finding* queue. Automated checks alone never certify that 10k question facts and calculations are correct.
