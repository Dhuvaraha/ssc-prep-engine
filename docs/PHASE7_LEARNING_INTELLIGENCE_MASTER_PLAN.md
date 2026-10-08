> **Platform scope extension — 2026 CGL Tier I/II and JE Paper I/II:**
> Read [Phase 7 Multi-exam Architecture & Rollout](PHASE7_MULTI_EXAM_ARCHITECTURE_ROADMAP.md) before implementing any PR. This adds official 2026 syllabus-gap remediation, a true exam-stage selector, isolated analytics/planner/mocks, CGL Tier II including Computer Knowledge + DEST, and JE Telecom Part G Paper I/II. The original 40Q/24m diagnostic blueprint below applies to **CGL Tier I only**, not every stage. Multi-exam foundations are first, while the Teacher V3, 4-option learning and UI quality objectives below remain mandatory.
>
# Phase 7 — Learning Intelligence, Teacher V3, Option Knowledge & UI Quality
Status: PLANNED — implementation not started by this document.
Scope: SSC CGL Tier I; preserve existing FastAPI/React/Vite/PostgreSQL systems and all learner data.
This document supersedes older Phase 7 wording for this new enhancement cycle. Past roadmap phases remain historical.

## Product outcome
Turn the existing SSC preparation engine into a trustworthy personal tutor:
Onboard → diagnose a limited initial sample → teach → check understanding → practise → analyse the actual evidence → revise → retest → adjust the plan.

Never conflate "accuracy on attempted questions", "topic mastery", "syllabus coverage", "diagnostic baseline", "exam score", and "predicted exam readiness".

## Baseline findings and non-negotiable constraints
- Existing ~10,043 verified questions across 74 topics and 4 subjects; content volume is not the immediate priority.
- Readiness hotfix PR #33 prevents an unsupported percentage with only practice; this is not a scientifically calibrated final readiness model.
- A 40-question diagnostic cannot assess all 74 topics. One full 100-question mock cannot establish syllabus-wide mastery either.
- Current Teacher Coach is largely keyword-routed, not a grounded conversational tutor. Teacher V3 has NOT been implemented yet.
- Practice's current "distractor" review does not teach an independently verified fact or misconception for each alternative.
- Dashboard, lesson, analytics and practice suffer from inconsistent hierarchy, spacing and nested container styling. A large stylesheet uses many repeated hard-coded tokens. UI needs systematic, not cosmetic, cleanup.
- Vercel is the canonical frontend; Render hosts the API. Live smoke must check the actual Vercel origin, auth CORS, and representative authenticated learner journeys.
- Keep exact 100-question/60-minute SSC mock, server-authoritative 15-minute sections, +2/-0.5, autosave/resume and history intact. Diagnostic MUST be a different mode and must not alter full-mock behavior.
- Do not purchase an AI API, change hosting plans, mutate production learner data or expose credentials as a by-product of this plan.

## Workstream 7A — Trustworthy diagnostics, coverage and Analytics V2
### A1 — 40-question starting diagnostic
- 40 questions; 10 per Reasoning, Quant, English, General Awareness; 24-minute total target.
- v1 sampled difficulty blueprint per subject: 3 easy / 5 medium / 2 hard. This is a design hypothesis, not an empirically calibrated SSC distribution.
- Sample distinct archetypes and several high-yield topic families per subject. Avoid repetitive clones, current active revisions, and obvious answer leakage.
- Use verified items only; audit distribution, passage/image render, correct option, timed targets, and licensing/source metadata.
- Separate mode and server timing rules from full SSC simulation; +2/-0.5 may be used to show a familiar score but label it diagnostic, not an official full-exam score.
- Start/resume/autosave/expiry/double-submit/reconnection and cross-user isolation must be covered by state-machine tests.
- Show correct answers and verified explanations AFTER submission, never leak answer keys during a test.
- Provide an optional "Start later"; don't block learning behind a mandatory test.

### A2 — Evidence model and content-coverage states
Maintain separate dimensions per learner:
1. Syllabus exposure — Not seen / Studying / Practised / Assessed.
2. Topic competence — Unknown / Foundation / Developing / Consistent, each with its sample count and difficulty distribution.
3. Difficulty — easy, medium, hard performance reported separately; easy-only accuracy must not imply exam readiness.
4. Test pressure — timed accuracy, actual full-mock marks, pacing and section balance.
5. Retention — spaced-review and later re-test evidence; repeat exposure is not the same as independent proficiency.
6. Evidence confidence — insufficient / early / provisional / established; the threshold and sample size are transparent.

Keep denominator explicit: e.g. "6 of 74 topics sampled", not "92% syllabus mastered" if 68 topics are unseen.
No coverage or evidence is encoded as zero proficiency. Unknown stays unknown.

### A3 — Readiness policy (do not report a fake percentage)
- No valid whole-exam evidence: "Exam readiness — Not assessed".
- One 40Q diagnostic: "Starting profile — sampled, provisional"; report subject results without pretending to know all 74 topics.
- One 100Q full mock: show the ACTUAL mock score, accuracy and time/section profile; mark overall readiness as limited or provisional evidence, not proven syllabus mastery.
- After multiple representative full mocks PLUS meaningful subject/topic breadth and medium/hard/retention coverage: allow a qualitative evidence tier and score trend. Calibrate any numeric "readiness" claim against observed outcomes before release.
- Initial evaluation candidate (not yet a validated rule): >=2 time-separated full mocks, >=50% of topics sampled across the 74-topic syllabus, each subject meaningfully represented, and medium/hard attempts. Tune thresholds with test scenarios and learner outcomes; if unmet, keep "insufficient evidence".
- A practice-only 75% score is always "75% of attempted practice", not "75% exam readiness".
- Diagnostic questions must not be reused verbatim for comparable check-ups or baseline-vs-current gains; use matched blueprints/parallel forms.
- Trend shows sample size, question difficulty, distinct topics, confidence, weak patterns and evidence changes alongside percentage values.

### A4 — Analytics and planner integration
- Starting baseline versus subsequent comparable diagnostic/check-up scores, separate from non-comparable guided practice.
- Subject-level and topic-level breakdown with Not assessed state, exposure, confidence, medium/hard evidence and revision retention.
- Coach explains "why this topic", "why this evidence is provisional", and a single actionable next step.
- Initial diagnostic informs tomorrow's plan; course corrections after lesson quick checks, timed practice, spaced revision and mocks.
- Completing one easy lesson cannot jump a topic to "Exam ready".
- Existing analytics, previous attempts, old scores and revision histories remain queryable.

Expected modules:
Backend: models/migrations for diagnostic attempt and baseline snapshots as appropriate; separate diagnostic selector/service/router; analytics evidence service; planner integration.
Frontend: diagnostic route, start/resume/results, Analytics V2, new learner Dashboard; typed API.
Tests: 0 evidence; 20/75%-easy-only; 40Q balanced diagnostic; missing section; 1/full and multiple mocks; repeated question contamination; topic coverage denominators; no PII leakage; invalid/expired test.

### 7A definition of done
New learner can voluntarily take the diagnostic and see an honest sampled starting profile and personalised first study plan. A learner with 20 easy questions sees practice accuracy but NOT overall readiness. Topic states never call unseen skills weak. Comparable repeated assessments show real progress without conflating practice with exam marks.

## Workstream 7B — Teacher V3 (human-like structured teaching)
### B1 — Deterministic teacher, reliable without paid AI
- Replace long passive card dumps with a 1-concept-at-a-time loop:
  Teach → predict/recognise → solve a micro-check → explain feedback → retry or advance.
- Topic prerequisites and foundations before shortcuts; "why SSC asks this" and recognition cues.
- A worked example initially reveals steps gradually; ask learner "what is the first step?" before reveal.
- Correct answer + fast explanation → progress to next pattern or exam-level question.
- Incorrect answer → map to a supported misconception, teach simpler, demonstrate one variation, then re-check independently.
- Two consecutive misses → reduce difficulty; repeated correct, timely answers → optional faster method and harder variation.
- Lesson progress records Seen/Understood/Applied/Checked, NOT just opened stages.
- Respect learner's choice of English, Tamil or Tanglish. Voice is an opt-in accessibility path, not an always-on autoplay interruption.
- Keep lesson state across refresh, back/forward, browser resize and interrupted network access.

### B2 — Context-aware Teacher Coach
- Inputs: current lesson block, published archetype, correct method, verified worked example, selected learner answer, attempted step, confidence and recent supported misconception.
- Actions: explain simpler, why step, why this option is wrong (when verified), compare methods, give one safe hint, work through a different example, ask a follow-up.
- No guessing facts, fictional source citations, premature correct-answer disclosure during unsubmitted assessment, or misleading mathematical derivations.
- Respond in understandable, short chunks; avoid paragraphs covering an entire lesson at once.

### B3 — Optional grounded AI, gated after deterministic baseline
- Evaluate a provider using a fixed representative 100+ prompt set across the four subjects and English/Tamil/Tanglish, including adversarial and unsupported questions.
- Compare accuracy, groundedness, source fidelity, teacher usefulness, refusal quality, latency and estimated cost per answer. Choose API only after evidence and budget approval.
- Backend-only secret, authenticated calls, safe prompt/context templates, redacted logs, per-user quotas, timeouts, caching and reliable deterministic fallback.
- Verified source excerpts are the authority; explicitly say "I cannot verify that" when necessary.
- Roll out behind feature flag with cost guardrails; never make the core lesson dependent on a paid AI service.

### 7B definition of done
A beginner can ask an authentic follow-up and receive a grounded answer. Learning state reflects demonstrated understanding. Two wrong attempts prompt an easier explanation; one correct easy answer is not evidence of mastery. Teacher remains functional if the AI provider is off.

## Workstream 7C — Four-option Knowledge Explorer + Study Tools
### C1 — Expand MCQ answer review to all four choices, without hallucinations
After submission:
- Show correct answer, verified explanation, learner's selected-error context, and short standard/fast methods where applicable.
- Collapsed "Learn the other options" opens optional per-option insights; normal fast-practice flow stays compact.
- General Awareness: explain what alternative entities ARE, what fact is relevant, and an accurately phrased related exam-style question IF a source supports it.
- English: explain which grammar rule/meaning/context makes each option valid elsewhere or invalid here.
- Quant: show which mathematical misconception, calculation path, base/sign error or unit mistake can produce a wrong number, but only if derivable.
- Reasoning: show rule/pattern/elimination rationale; visual choices require image-aware review.
- Not every arbitrary numerical distractor has a useful independent "correct question". A truthful "no supported alternate fact" is better than inventing one.
- Answer contexts and related micro-questions are subject-specific, not one generic template.
- Never show these explanations while a timed test is running; full mock results review can opt in after submission.

### C2 — Verified option knowledge content pipeline
- Create structured per-option insight records keyed by question and position, not an AI text blob replacing existing question options.
- Fields: explanation type, short fact/rule, source URI/reference and source date where relevant, optional related question, topic links, verification status, reviewer/audit metadata and revision eligibility.
- Status pipeline: missing → draft → verified → published; only published and source-grounded content shows to learners.
- Seed with a source-audited pilot covering multiple question types across the four subjects, including the supplied 2026 Budget example; then progressively expand priority topics.
- Run automated correctness/consistency/duplicate checks and human spot audits by subject; no fabricated PYQ/source tags.
- Historical/time-sensitive GA facts must include a relevant year/event context to avoid contradictions after facts change.
- Use the verified published facts to generate optional micro-flashcards and a "Try one related question" follow-up, not mandatory four extra quizzes.

### C3 — Tools that actually improve retention
- Personal mistake notebook with corrected reasoning, learner-written explanation, retry date and outcome.
- Formula and rule notebook: topic-tagged safe shortcuts and active recall.
- Daily Calculation Gym: bounded 5–10 minute basic arithmetic/fractions/percentage skills, measured speed AND accuracy.
- English grammar/vocabulary and GA fact decks: spaced recall with dates and source for current affairs.
- A compact Today learning loop integrates these tools based on actual needs, not unrelated random tasks.
- Evidence from option cards/flashcards does not automatically mark entire topics mastered.

### 7C definition of done
Question review teaches something accurate beyond "Distractor" for every verified published option-insight, and never invents unsupported claims. User can save facts to a spaced-revision deck, revisit mistakes and improve on related questions.

## Workstream 7D — Professional UI/UX design-system and performance QA
7D is cross-cutting, not a "beautify at the end" phase. Start the shared shell/tokens in the FIRST PR, then improve the interface within each 7A–7C slice.

### Design audit findings
- Global CSS is large with numerous page-specific hard-coded navy/gray colours and repeated container variants.
- Dashboard has had redundant navigation, oversized hero type and dead space at desktop widths; new/returning/partial learners require distinct information hierarchy.
- Nested cards, borders, backgrounds and accent colours are inconsistent across Learn, Teacher, Practice and Analytics.
- Inconsistent text hierarchy between display heading, task heading, supporting metadata and buttons.
- Header/back control must be deterministic; no back arrow on Home, obvious location/breadcrumb on deep routes.
- Data-heavy Analytics must explain uncertainty prominently rather than making a ring/chart seem authoritative.

### Design specification
- Retain recognisable restrained navy + white/neutral foundation. Define semantic tokens for primary/secondary text, surfaces, borders, focus, selected, correct, warning and error. Do not decorate every card with a different tint.
- Define a restrained type scale (desktop display, page title, section heading, card title, body and metadata), consistent line-height/weight and 8-point spacing rhythm.
- Single app shell owns page width and main padding. Avoid card-inside-card unless there is a true semantic distinction; prefer whitespace, dividers and tabs over endless bordered containers.
- Maximum one dominant primary action per view, with clear hierarchy for secondary links.
- New-user Home: start a real diagnostic OR start learning; returning Home: continue exact step, Today plan and due revision. Remove technical marketing copy "content is ready" from primary hero.
- Learn: visible subject/topic path, steps remaining, short content sections, one teacher prompt at a time and simple next-action footer.
- Practice: question and options dominate screen; review is a clean expandable panel; no overloaded five-card answer screen.
- Test: calm and consistent timer/section palette, obvious saved/unsaved state and usable mobile answer controls.
- Analytics: evidence badge, sample sizes and Not assessed must be obvious; chart shows measured progress, not false readiness confidence.
- Design responsive sizes 360/390 mobile, 768 tablet, 1024 laptop, 1440/1920 desktop; handle long text, visual questions, sticky nav and browser zoom.
- Ensure keyboard support, explicit focus, accessible contrast (WCAG AA for relevant text), readable text minimums, 44px touch targets where feasible, reduced-motion preference, aria-live for loading and errors.
- UI components: AppShell, PageHeader/Breadcrumb, ContentSection, Metric, EmptyState, ErrorState, Skeleton, TeachingPanel, QuestionReview, EvidenceTag and action row.
- Visual reference/acceptance snapshots for each page at new-user, partial-data and established-user states. Fix visible spacing/hierarchy rather than blanket colour changes.

### Performance and reliability
- Instrument first-visit versus warm navigation separately (Render backend may sleep); do not claim cold start solved with skeletons.
- Lazy-load only what current route needs, preserve deduped requests, cache invalidation on writes/token changes, prefetch next study step.
- Target cached page transitions <500ms perceived; warm normal API P95 ideally <1.5s; 2s+ investigate, 5s+ release blocker. AI answer streaming uses a separately measured budget.
- Production smoke MUST use canonical Vercel origin and confirm API preflights/auth routes, not an obsolete Render web hostname.
- No answer leakage, stale cross-user cache, lost mock writes, broken deep link or silent request failure.

### 7D definition of done
Same visual grammar across Home, Learn, Practice, Tests, Revision, Analytics, Profile, including mobile. Visual regressions reviewed from screenshots/video and keyboard tested. Page-specific latency and functional E2E gates pass.

## Sequenced PR plan
PR 0: Freeze baseline, read production configuration, capture screenshots, design tokens and route-specific latency; zero learner data changes.
PR 1: Shared UI shell/headers/design tokens, navigation hierarchy, new-user/returning Dashboard and common loading/empty/error states.
PR 2: Diagnostic backend, question blueprint, persistence/migration and score/result snapshots; no full-mock behavior changes.
PR 3: Diagnostic frontend, resume/results and accessible mobile test UI.
PR 4: Evidence model/coverage/difficulty/retention analytics, honest states and baseline-vs-current. Planner integration with a single recommended next task.
PR 5: Teacher V3 deterministic lesson state machine, interactive checks and misconception mapping.
PR 6: Teacher contextual controls/English-Tamil-Tanglish/voice and supported explanation quality tests.
PR 7 (optional): Grounded AI teacher evaluation then gated implementation only after explicit API/budget decision.
PR 8: Option-insight schema, verification/editor workflow and source QA jobs.
PR 9: Verified cross-subject pilot, GA Budget example and option review UX with fallback for missing facts.
PR 10: Option learning to micro-revision/related questions; mistake/formula notebook and calculation gym with gradual scope.
PR 11: Cross-page responsive visual QA, accessibility, CORS/API integration, warm/cold latency, regression, production smoke and release sign-off.

If a PR is too large, split by end-to-end behavior without changing the phase gates. Every change remains on a branch and moves through review → tests → CI → merge → deployment → live checks.

## Test matrix / launch gates
- Backend unit, migration upgrade+rollback, API validation, idempotent submissions and cross-user auth.
- Deterministic evidence scenarios: no tests, only easy, one topic sampled, every subject partially sampled, 40Q diagnostic, one near-blank/full mock, two balanced full mocks, repeated known questions and retention drop.
- Diagnostic: 40Q exactly, 10 per subject, correct difficulty spread, unique questions, no correct answers leaked, timer/server lock, disconnect/reconnect and safe submit.
- Teacher: 74-topic lesson package completeness, verified step reasoning, misconceptions, hints, adaptive retry, resume, unsupported/ambiguous follow-ups, AI-off fallback.
- Option insights: source traceability, chronology, option identity/position, relation to correct answer, no invented fact, explicit unpublished state, review accessibility and correct save/revision behavior.
- UI visual tests: all major routes at 360/390/768/1024/1440+, empty/partial/full data, contrast, keyboard, mobile navigation, no unnecessary headers/nested cards.
- API/load: measured authenticated flows, cold/warm separation, Vercel↔Render CORS, latest commit provenance, 5s P0 threshold.
- P0 = 0, P1 = 0 before public release; no one labels a phase "100%" merely because code or CI exists.
- Human learner acceptance using real SSC questions is REQUIRED before final sign-off.

## Non-goals for this cycle
- Unverified mass-generated explanations for ~30K+ distractor options.
- Presenting a statistically unsupported "you are 80% ready" probability.
- Rewriting the entire existing practice/mock/lesson backend when incremental extensions suffice.
- Changing billing or migrating hosting without explicit approval.
- Building SSC JE curriculum before the current SSC CGL learning experience is verified.

## Decision gates
1. Start PR 0/1 without buying AI or changing infrastructure.
2. After deterministic Teacher V3 works, approve/decline optional AI provider and monthly budget based on evaluation, not a guess.
3. Release per-option explanations only when source-grounded and reviewed.
4. Phase 7A–7D final sign-off requires production checks AND human study-session acceptance.
