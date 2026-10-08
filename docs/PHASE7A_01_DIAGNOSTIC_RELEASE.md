# Phase 7A-01 — CGL Tier-I Starting Diagnostic

Status: Implementation slice; evidence-safe 40Q sample, **not** whole-exam readiness.
Scope: SSC CGL Tier I only. No changes to JE/Tier II availability, official full mock, original content, marks, learner attempts or topic mastery.

## Entry points
- Home → "Starting Diagnostic (40Q)" and Mock Lab → Starting Diagnostic.
- Deep link `/mocks?mode=diagnostic`, authenticated.
- 40 questions, 24-minute server-authoritative timer, 10 per subject.
- Inside every subject: 3 Easy / 5 Medium / 2 Hard verified questions, no unreviewed visual content, four unique options, diversified topic/pattern candidates.
- The selected questions remain frozen for the attempt. Answer keys are withheld until submission; an existing attempt resumes with saved answers.
- On submission, show actual sampled accuracy, subject breakdown, question review and "Exam readiness: Not assessed". No graded diagnostic content is included in Practice or full Mock Analytics.

## API contracts
- Reuse safe `/api/v1/mocks` endpoints with `mode=diagnostic`. Existing `full` still retains 100Q/60m and strict 15-minute sections. The diagnostic is **not** the full mock format.
- `GET /api/v1/diagnostics/baseline` returns the **first completed** diagnostic, latest follow-up if any, total syllabus topic count, which topics actually appeared and were attempted, and per-subject attempted/correct, E/M/H evidence.
- `readiness` is always `null` here. Empty or incomplete results are labelled limited; unseen topics stay unknown.
- Repeat assessments exclude questions from **previously submitted** diagnostics. The user may resume an in-progress test rather than start a parallel one.
- If verified bank breadth is too small to maintain strict 3/5/2 with four valid options, return a clear error **without creating a partial attempt**. Never substitute a simpler question silently.
- Official mock score rule +2/−0.5 is reported only as *sample marks*, not readiness or comparable full-exam marks.

## Quality gates
- Exactly 40, 10 per subject, 3/5/2; no duplicate IDs/answers pre-submission.
- Server time expiry blocks new answers and allows final submit; submitted attempts cannot be edited.
- Cross-account and exam-stage privacy; existing mock resumes without losing answer saves; double submit idempotent.
- Full mock behavior unchanged and History/Analytics mock totals exclude the diagnostic.
- First baseline immutable across repeat attempts; evidence denominator explicit.
- Regression tests in `backend/tests/test_phase7a_diagnostic.py`; frontend TypeScript build and end-to-end human mobile test are separate gates.

## Follow-up work
1. Diagnostic frontend human study-session acceptance on real production CGL account.
2. Analytics V2: explicit per-topic `unseen | studied | sampled | validated` states, independent first-try performance, retention, representative timed mocks, confidence calibration. A single 40Q sample can NEVER assess 74 topics.
3. Use sampled diagnostic strengths/needs to recommend a **non-punitive** starting plan; do not auto-mark unseen topics as weak.
4. Teacher V3 misconception repair and curated sources for all alternate-choice knowledge.
5. Fix Vercel production CI/GitHub integration (currently live commit trails main; attempted direct deploy returned 403). Keep "code merged" and "live verified" distinct.
