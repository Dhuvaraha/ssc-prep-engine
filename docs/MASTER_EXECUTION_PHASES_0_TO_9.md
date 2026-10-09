# SSC Prep Engine — Unified Phase 0–9 Delivery Plan
**Canonical active execution plan | 2026-10-08**

This document unifies unfinished Phase 7A/7B/7C/7D and M0–M4 initiatives into **ten outcome-gated phases**. The historical `PHASE7_LEARNING_INTELLIGENCE_MASTER_PLAN.md`, `PHASE7_MULTI_EXAM_ARCHITECTURE_ROADMAP.md`, and older product completion plans remain detailed specifications, **not competing execution queues**.

## Existing verified baseline
- GitHub `main` at plan freeze: `719a56bc742bd7e8eb6850378f0b46ba46d80b66`, with Phase 7A-01 merged.
- Historical Phases 1–6 implemented; historical 4C learner telemetry and 6C full human release acceptance remain unclosed.
- CGL Tier I: four subjects, 74 top-level topics and ~10,043 question records. Count alone does not certify complete official subtopic coverage or question accuracy.
- M0-01 through M0-04 exam-stage chooser, focus and initial data isolation implemented; **full multi-stage separation is NOT complete**.
- Diagnostic 40Q/24m (10/subject, 3 easy + 5 medium + 2 hard), immutable first sampled baseline; 100Q/60m CGL Tier I simulation with four 15m sections is separate.
- Learning Path Foundation → Application → Challenge, Teacher V3 first verified interactive worked-example checkpoint, reviewed option-insight *foundation* are implemented. Full Teacher V3 and broad published option learning are **not** complete.
- PR #48 is open, CI green, unmerged; it changes mobile navigation, mock palette and responsive layout.
- Vercel canonical production last verified SHA `ae8611ac27f1e7b2901498a3f62bed2862ae2983` (behind main). Project-specific Vercel access recently recovered, but build-rate-limit GitHub status/release is not cleared.
- Security review: Supabase public `user_exam_focus` and `question_option_insights` have RLS disabled; review grants and approve migration before changes.

## Architecture is fixed
**Vercel React/Vite frontend** (`https://ssc-prep-engine.vercel.app`) → **Render FastAPI backend** (`https://ssc-prep-engine-api.onrender.com`) → **Supabase PostgreSQL**.

Existing `ssc-prep-engine-web.onrender.com` is only fallback: no extra Render frontend, no new teams, no cross-project change to TracliQ. Do not delete or disable fallback without owner approval. No subscription, AI API spend or database mutations without required approval.

## Strict phase state and closure protocol
States: `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, `COMPLETE`. No `PARTIAL_COMPLETE` or progress percentage replaces missing gates.

**A phase closes only after all of the following:**
1. Spec-to-feature traceability: all in-scope checklist items satisfied; unsupported/out-of-scope features stated explicitly and never advertised.
2. PRs reviewed, merged to `main` without overwriting other work; frontend and backend CI green, migration upgrade/rollback checks where relevant.
3. In-phase functional and integration regression tests, correct exam blueprint/scoring/state integrity, multi-user authorization and data preservation; zero known P0/P1 inside that phase.
4. Representative browser/device acceptance for the changed flows (including keyboard/focus and actual browser where UI applies), test evidence/log references.
5. Release confirmed on **Vercel production frontend** and Render backend with matching SHA/configuration where changed; auth/CORS smoke passed; fallback/rollback identified.
6. If a hard blocker exists, keep `BLOCKED` and do **not** start the next phase. Human approvals, paid/vendor options, official-source review and real learner testing remain honest external gates.
7. Final comprehensive whole-product integration and bug sweep **also** happens in Phase 9. Never defer unit/integration/security regressions to Phase 9.

A phase may contain multiple focused, serial PRs and content batches, but cannot be marked complete after only an initial slice. After merging each PR, rebase next changes and preserve historic learner attempts/questions. Use no mass re-seeds.

## One execution sequence

### Phase 0 — Release foundation and baseline
**State: IN_PROGRESS; blocked on Vercel build restriction and deployment proof.**
Scope: inventory current services/SHA/env public metadata; recover Vercel production at main; verify API base/CORS/login; finish/review/merge PR #48 (requires independent viewport/browser checks), preserve Render backend; decide redundant Render frontend auto-deploy *with owner approval only*; review #47 Supabase RLS/grants and apply reviewed migration only after explicit approval; baseline full content and learner backups, cold-vs-warm latency and smoke.
**Complete only if:** latest main Vercel production + Render API integration accessible, signed-in diagnostic and CGL full mock smoke, responsive changed-flow acceptance at 320/360/390/430/768/1024/1440+, access boundaries and RLS risk resolved or explicitly safe & documented with approved policy, CI and production rollback gate. TracliQ unchanged.
Refs: PR #48, issues #47, #49.

### Phase 1 — Multi-exam engine separation
**State: NOT_STARTED (M0-01–04 groundwork exists).**
Scope: stage/stream/year/blueprint registry and versioned official rules; stage-scoped enrollment/focus, question maps and content publishing gates; exam-specific planner, analytics, diagnostic, mock state, revision, caches and last route; prevent cross-stage history contamination. Backward-compatible migrations, recoverable active mocks, staged exam switch UI. User-facing unavailable courses remain explicitly unavailable.
**Complete only if:** two users × CGL Tier I/Tier II/JE Telecom Paper I/II isolated in synthetic fixtures; no cross-exam attempts/readiness/data leaks; existing CGL accounts and 100Q test stable; stage switching during active exam warns & resumes; schema rollback and authorization tests pass. *Infrastructure readiness does not imply new course content published.*

### Phase 2 — CGL Tier I official curriculum closure
**State: NOT_STARTED.**
Scope: official 2026 CGL syllabus/corrigenda mapped to all mandatory subunits and lessons, including audit candidates Partnership Business, radians/degrees, frequency polygon, reasoning indexing/address/date/city and English homonyms/shuffling; quality-review missing lessons, patterns, examples and difficulty; reproducible question answer/option/math/image/source audit. Preserve 74-topic IDs unless syllabus requires additive mapping.
**Complete only if:** mandatory official subunits have verified mapping, teaching and independent quality-audited question sets (Easy→Medium→Hard), no unreviewed critical holes; content tests, editorial audit and representative user lessons all pass. Number of questions ≠ evidence of correctness.

### Phase 3 — Diagnostics, Analytics V2 and adaptive starting plan
**State: NOT_STARTED (7A-01 foundation merged).**
Scope: genuine 40Q session acceptance; per-stage sampled/untested exposure and competence/confidence states; first-attempt, non-repeated medium/hard/timed evidence, retention and calibrated qualitative readiness; repeat assessment comparable by blueprint; explainable beginner starting plan and non-destructive planner updates confirmed by learner; zero-evidence paths.
**Complete only if:** learner can diagnose→understand which attempted topics need work→study→practice→review→reassess; 74-topic denominator truthful, first baseline immutable, no missing topic called weak, no invented exam readiness percent, CGL full mock separate; regression and production flow pass.
Ref: issue #46.

### Phase 4 — Deterministic Teacher V3 full teaching loop
**State: NOT_STARTED (first interactive examples merged).**
Scope: stage-based teach→predict→micro-check→feedback→simpler retry→independent check with verified misconception mapping; two-error difficulty rollback, legitimate easy→medium→hard progression; persistence/resume, English/Tamil/Tanglish controls, contextual voice and accessible keyboard; grounded context-aware tutor actions and unsupported-claim fallback. Optional paid AI is **out of baseline scope**, with separate future provider evaluation and owner/budget approval; never required for phase completion.
**Complete only if:** representative 74-topic beginner-to-hard journeys and cross-language teacher scenarios behave correctly; answer key withheld in assessments; no fabricated facts or false mastery; interrupted session resumes; API/voice optional path never blocks lessons.

### Phase 5 — Verified option explorer and retention tools
**State: NOT_STARTED (reviewed option schema/UI foundation merged).**
Scope: sourcing/editorial pipeline for four-choice explanations in GA/English/Quant/Reasoning; draft→review→published gating, dated time-sensitive facts and provenance; targeted audited high-yield bank and explicit unsupported state (no invented explanation for every numerical distractor). Mistake notebook, formula/rule notebook, due/retention flashcards, daily bounded Calculation Gym and short related verified micro-questions, integrated with Today.
**Complete only if:** published and reviewed option insights safe, representative four-subject coverage quality gate met, notebook persistence/scheduling and learn→revise→retest loop works; no unavailable insight falsely claimed complete. No unsourced mass-generation target.

### Phase 6 — Unified responsive UI/UX and performance
**State: NOT_STARTED (PR #48 first slice).**
Scope: one app shell and design tokens, compact hierarchy, dashboard states, Learn, lessons/Teacher, Practice, Tests, Analytics, Planner, Revision, Exams, Profile and auth; skeleton/error/empty/loading consistency, keyboard/screen reader/contrast and touch sizing; viewport 320/360/390/430/768/1024/1440/1920+, zoom, landscape, long text/images, persistent nav, deep-link. Measure warm and cold separately; prioritize stable UI and no major performance regressions.
**Complete only if:** scripted visual + human walkthrough per route/state and device, no significant overflow/clipped actions, keyboard and focus correctness, no 5s+ unexplained warm waits, stable saved answers/timers during reflows. Do not confuse Render free-plan sleep with frontend optimization.

### Phase 7 — SSC CGL Tier II complete stage
**State: NOT_STARTED.**
Scope: official-year blueprint including 150 Session-I MCQs (130 merit + 20 qualifying Computer Knowledge), +3/-1; section/time locks as reviewed against current notice, separate 15m true DEST typing simulator (NOT MCQs), stage-specific subjects/lessons/practice/mock/analytics/qualification. Include optional JSO Statistics and AAO Finance/Economics papers only for valid eligible tracks, with independent verified content/release gate.
**Complete only if:** mandatory common Paper I syllabus, computer qualifying, DEST and full timed simulator pass both content and user tests, stage-isolated histories and official 2026 verification. Optional post-specific tracks are separately gated and cannot be called published unless completed.

### Phase 8 — SSC JE Telecom Paper I and Paper II complete stages
**State: NOT_STARTED.**
Scope: official JE 2026 Part G Telecom syllabus, verified technical families with equations/units/diagrams/solutions, proper question source and difficulty, Paper I: 50 Reasoning + 50 GA + 100 Telecom, 120m, +1/-0.25; Paper II: 100 Telecom, 120m, +3/-1. Calculator and permitted aid rules stage-specific. Stage isolation, teacher, diagnostics, notebooks, planner, responsive mocks and quality controls. No substitution of SA IMD Part E ECE, other JE streams remain unpublished.
**Complete only if:** both Paper I and II complete official mapping, audited technical banks, exact timers/marking/qualifications, signed-in start→resume→submit→review, multi-exam switch safety; live delivery QA.

### Phase 9 — Final integrated launch and regression closure
**State: NOT_STARTED.**
Scope: all exam-stage end-to-end workflows and multi-user security, migrations, backups and rollback, official-source latest corrigenda, content/editorial spot audits, frontend Vercel/backend Render production provenance, cross-origin auth and cache, load/performance and cold start, device/keyboard/accessibility, user recordings and signed-in learner acceptance. Fix all P0/P1 and rerun full CI/regression, human sign-off and post-release monitoring plan.
**Complete only if:** all nine prior phases marked COMPLETE with evidence, all intended published courses truly course-ready, zero P0/P1, real browser and user acceptance, production smoke and monitored rollback. No "launch complete" purely from CI.

## Dependency and decision notes
- **Strict sequence 0→1→2→3→4→5→6→7→8→9**. Each phase's gate stops the next; individual PRs are allowed inside it.
- Cross-cutting security, accessibility, performance and exam fidelity must not wait for phases 6/9 if current code is affected.
- An unrequested AI subscription, optional non-Telecom JE tracks, and unsupported copyrighted content are **not silently required**; any genuinely mandatory syllabus portion or in-scope optional paper must be explicitly tracked, not quietly waived.
- For any blocker requiring owner interaction, record exactly what is blocked, evidence and next authorized action. Do not merge, deploy, delete services or alter sensitive production tables just to make a green badge.

## Progress ledger (update at each phase completion)
| Phase | State | Evidence of closure |
| --- | --- | --- |
| 0 Release foundation | IN_PROGRESS | PR #48 open; Vercel production behind main; issues #47/#49; gate not passed |
| 1 Multi-exam engine | NOT_STARTED | M0 groundwork exists; final isolation gate pending |
| 2 CGL Tier I quality | NOT_STARTED | content bank exists; official subtopic completeness unverified |
| 3 Diagnostic / Analytics V2 / planner | NOT_STARTED | diagnostic foundation merged; issue #46 open |
| 4 Teacher V3 | NOT_STARTED | interactive foundation merged; full pedagogy gate pending |
| 5 Option knowledge / revision tools | NOT_STARTED | reviewed insight foundation merged; full toolset pending |
| 6 Responsive UX / performance | NOT_STARTED | PR #48 groundwork |
| 7 CGL Tier II | NOT_STARTED | architecture roadmap only |
| 8 JE Telecom I & II | NOT_STARTED | architecture roadmap only |
| 9 Final integrated launch | NOT_STARTED | final go-live gate depends on phases 0–8 |
