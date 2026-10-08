# Phase 7 Platform Extension — Multi-exam SSC CGL + SSC JE (2026)
**Status: APPROVED PLANNING SCOPE — not implemented.** This is an extension of [the canonical Phase 7 learning-intelligence plan](PHASE7_LEARNING_INTELLIGENCE_MASTER_PLAN.md), not a replacement for Teacher V3, diagnostics, Option Knowledge Explorer, or the UI/UX design system.

## 1. Goal, learner promise and rollout order
One login, one responsive learner platform, multiple independently valid exam plans.
- Initial four learner choices: **SSC CGL → Tier I**, **SSC CGL → Tier II**, **SSC JE (Telecom) → Paper I**, **SSC JE (Telecom) → Paper II**.
- UI must use CGL "Tier" and JE "Paper" consistently, not falsely label JE "Tier 1/2".
- The JE exam family will support other 2026 streams (Civil, Electrical, Mechanical; optional SA IMD CS/IT, ECE, Physics as separate branch choice), but **do not display an unfinished curriculum as ready**.
- Prioritize CGL Tier I completeness and CGL Tier II after the common platform foundation. Start JE Telecom content after the learner's exam next week, subject to ready-to-publish quality gates.
- Preserve CGL Tier I's existing 74-topic records, verified questions, lessons, study attempts, bookmarks, revision and historical mock submissions. No destructive re-seeding or mass migration.
- Selected exam should change the learner's Home, syllabus, diagnostic, lessons, tests, official rules, dates, revision, analytics, planner, performance benchmarks and feedback. It must not leak results from another exam as exam-specific readiness.
- Shared core concepts may be reusable across stages, but reuse needs explicit curriculum mapping and level/quality approval.

## 2. Official 2026 exam blueprints — authoritative source URLs
CGL: https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/Notice_of_adv_cgl_2025.pdf
(This file is named *cgl_2025.pdf* at SSC, but its front page explicitly says "Combined Graduate Level Examination, 2026", 21 May 2026. Check the document CONTENT, not its filename.)
JE: https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/Notice_of_adv_je_2026.pdf
Both blueprints must be stored with notification year, URL, effective date, version and verification date. Re-check official corrigenda before content publication.

### CGL Tier I
- 100 MCQ / 60m; four separately timed 15m subjects.
- Reasoning 25, GA 25, Quant 25, English 25. +2 / -0.50.
- Current production engine already supports this stage: preserve exact server-side locks/autosave and improve rather than rewrite.

### CGL Tier II — Paper I for all relevant applicants
Session I:
- Section I: Mathematical Abilities 30 questions / 30m; Reasoning 30 / 30m.
- Section II: English 45 / 40m; GA 25 / 20m.
- Section III: Computer Knowledge Test 20 / 15m; qualifying.
- Above multiple-choice subjects +3 / -1.
Session II: DEST, a 15-minute **typing/data-entry task**, qualifying; **NOT an MCQ**. Need a separate text-entry speed/accuracy assessment, passage provenance, keyboard and zoom tests, scoring/qualifying display. No fake "typing MCQs".
- Session I total 135m; Session II is a separate 15m session with break/re-registration behavior reflected in training.
- Paper II (Statistics: 100Q / 200 marks / 2h; -0.5) and Paper III (General Studies Finance & Economics: 100Q / 200 marks / 2h; -0.5) apply only to eligible shortlisted posts, **not universal CGL Tier II**. Support as optional specializations with eligibility/post selection and their own content-ready gate.
- Tier II requires separate computer knowledge teaching, qualifying skills and deeper pattern distribution; copying Tier I lessons/questions verbatim is not adequate.
- Note: +3/-1 for Paper I MCQ; actual CGL official notice details in paras 13.8–13.9.

### JE 2026 (focus: JE Telecom Part G)
Paper I:
- 200 MCQ / 120m: Reasoning 50, GA 50, selected technical Part G (Telecommunication) 100; +1 / -0.25.
Paper II:
- 100 technical Part G (Telecommunication) MCQ / 120m; +3 / -1.
- Both papers require branch locked to learner's chosen 2026 stream; **Paper II is NOT a general reasoning/GA exam**.
- JE Telecom Part G is explicitly separate from Scientific Assistant IMD Part E Electronics & Telecom, though subject matter overlaps. Never silently substitute one branch's examination with the other.
- Part G major official subject families: Engineering Mathematics; Network Analysis; Signals & Systems; Electronic Devices; Analog Circuits; Digital Circuits; Control Systems; Analog Communications; Digital Communications; Electromagnetics. Paper II delves into detailed subunits.
- On-screen scientific calculator and supported reference tables (IS 456 / steam table where relevant), language configuration and time/answer rules need exam-specific testing. Do not enable unsupported aids in CGL.
- JE variant choices reserved in configuration: Civil (A), Electrical (B), Mechanical (C), Telecom (G); SA IMD choices D/E/F under separate recruitment path. Do not claim these are fully implemented until audited.
- All technical details must match current SSC notices and later official corrigenda.

## 3. Product navigation and UX
Authenticated entry:
1. If only one active exam-stage enrollment, open "Continue" immediately, no annoying repeated chooser.
2. If the learner has multiple enrolled stages, Home displays a compact **Current Exam** switcher and separate "All Exams" management entry.
3. On choosing an exam, optionally select JE stream/post, add exam date, schedule, prior prep status and daily time budget.
4. Stage-context badge visible on every study page: "SSC CGL · Tier II" or "SSC JE · Telecom · Paper I".
5. Preserve separate last-visited page, teacher lesson step, daily plan and mock in progress for each exam-stage.
6. On switching during an active test, warn and require confirmation; do not discard or corrupt it. Resume it after switching back.
7. Never show mixed "74 topics" from CGL Tier I as a universal platform syllabus total; show numerator/denominator per selected curriculum. Label incomplete curriculum "Coming soon" or "Coverage in progress".
8. Continue the Phase 7D design system: compact shell, consistent page title, focus hierarchy, toned-down card nesting, 360px+ responsive switcher, accessible keyboard/voice UI.

## 4. Data architecture: additive and exam-scoped
The existing backend already has an \`exams\` table with exam_id references for questions, subjects, targets and mocks, but the current mock engine, analytics and frontend API still hardcode \`ssc-cgl-tier-1\`; \`topic_mastery\` is keyed by topic_id. Simply adding two extra entries to a dropdown would be unsafe.

Recommended data model (exact implementation subject to migration audit):
- \`exam_families\`: CGL, JE. \`exam_tracks\`: JE Telecom, JE Civil, JE Electrical etc.; CGL optional target posts.
- Existing \`exams\` retains its stable CGL Tier I slug/id. Add stage metadata or an \`exam_stage\` child keyed by family + tier/paper + stream + notification year. Preserve existing APIs during migration with a compatibility resolver.
- Versioned \`exam_blueprints\` + ordered \`blueprint_sections\` with section count, correct/incorrect marks, timing, lock/transition, qualifying and type (MCQ vs DEST), calculator/language/accessibility rules.
- \`syllabus_units\` with official notification paragraph references and version; \`curriculum_mappings\` to one or more existing lesson/topic/archetype entities. Nodes carry \`verified | partial | missing | pending_review\` status.
- \`question_exam_stage_map\` many-to-many: reuse a question only after a stage-specific approval of relevance, difficulty, correct answer, verified explanation, passage/image, licensing and date; maintain immutable source provenance. Avoid copying question text into duplicate bank rows simply to re-use a concept.
- \`user_exam_enrollments\` (user, family, stage, variant, year, target date, last route, active focus). Separate per-stage planner, benchmark and analytics snapshots; one *current focus* is okay, multiple enrollments should remain.
- Existing \`question_attempts\` and \`topic_mastery\` remain as historical evidence. New exam-stage evidence is scoped through join to approved stage mappings and blueprint, or through an additive explicit enrollment/stage key after backward-compatible migration.
- \`revision_items\` and \`flashcard_progress\` may preserve personal learning history, but schedules/views and exam-specific readiness are separate per stage. Shared rule knowledge can carry "previously practised" indicator without automatic exam readiness credit.
- Include content readiness flags per syllabus stage; do not expose as teacher-ready or mock-ready before verified lessons/examples/options and blueprint depth pass.

## 5. Content development and coverage audit
### CGL Tier I gap closure
- Map each officially named syllabus subunit to lesson block, question archetype, distinct verified questions and difficulty.
- Focus initial audit: Partnership Business, radian/degree units, frequency polygon, reasoning indexing/address/date/city and intelligence variants, English homonyms/sentence shuffling. Zero explicit keyword match indicates **requires audit**, not absolute absence.
- Add missing subunits under appropriate existing topics when possible; add a new top-level topic only when syllabus structure warrants it. Never inflate count just to market more topics.
- Re-run 74-topic lesson/teacher and mock readiness; publish exact covered / partial / missing count tied to official syllabus requirements.

### CGL Tier II
- Reuse Tier I fundamentals only when appropriate; build higher-depth lessons/examples/traps and official-level practice.
- Add Computer Knowledge and real DEST simulator before marking common Paper I complete.
- Treat JSO statistics, AAO finance/economics as opt-in additional papers with their own readiness.
- Adapt diagnostic/question balance and analytics by subject and qualifying-vs-merit rule.

### JE Telecom
- Use the official 2026 Part-G detailed syllabus (Paper I and Paper II) as source of truth. Technical units and examples need ECE/telecom-specific worked derivations and diagrams.
- General Reasoning/GA can borrow common concept content, but must meet JE Paper I timing, counts and 2026 syllabus. JE Telecom Paper II must only test telecom technical topics.
- Create a *separate* technical question bank quality gate: solved numerical accuracy, units, diagrams, per-topic difficulty, correct source and distinct pattern coverage.
- JE Civil/Electrical/Mechanical + SA IMD not published prematurely. Build import-ready blueprint templates and content pipelines until verified.

## 6. Intelligence, Teacher V3 and Option Explorer stay in Phase 7
- Baseline/diagnostic selection comes from the currently selected exam-stage. 40Q/24m **applies to CGL Tier I v1 diagnostic only**; JE technical diagnostic must have its own approved representative blueprint.
- No universal "You are 50% ready" score. Display subject/question/difficulty/stage-specific evidence; unseen subtopics are \`Not assessed\`. Actual mock performance is not proof of 100% syllabus coverage.
- Teacher V3 is exam-context aware: CGL Tier II deeper timed methods, JE Telecom equations/circuits/derivations. Ground AI replies only on verified content and exam rules; choose/pay for AI separately.
- Option Knowledge Explorer has subject-specific treatment: GA alternative factual answers, English meanings/grammar, Quant mistake derivations, JE technical distractors with correct units/conditions. Publish only sourced and verified option insights.
- Initial and ongoing plans remain scoped. Switching from CGL Tier I to JE must not silently move the user's weaker CGL topics to JE's syllabus.

## 7. PR rollout — strictly sequential quality gates
### M0: Multi-exam architecture before adding any course data
1. Baseline DB + code/API dependency graph; back up schema and verify rollback.
2. Add additive family/stage/track/enrollment and blueprint definitions. Migrate existing CGL Tier I records without ID changes.
3. Refactor all hardcoded CGL Tier I paths in frontend and backend (mock engine, planner, analytics, content tree, caching, navigation and benchmarks). Introduce an active exam-stage context with auth scoping and sane defaults for existing learners.
4. UI chooser, per-exam Home and stable deep-link handling. Separate mock state safely.
5. Test two users × multiple stages × multiple mocks, stale cache isolation, old account data and zero-loss migration.

### M1: Finish CGL Tier I official coverage audit
- Official 2026 syllabus-to-lesson/question audit with human review and missing subtopic remediation.
- Continue Phase 7A diagnostic, 7B Teacher V3, 7C option insights and 7D design consistency; multi-exam foundation must not delay already planned CGL quality fixes unnecessarily.

### M2: CGL Tier II
- Release Paper I MCQ Session I after its syllabus, blueprint, content and scoring/timer tests pass.
- Add Computer Knowledge section and separate DEST typing UI; only then label **Common Paper I Complete**.
- Optional Statistics / Finance & Economics paper tracks later by valid candidate/post selection.
- Per-stage analytics and full mock smoke; ensure Tier I mock engine unchanged.

### M3: JE Telecom Paper I/II (after next week's learner exam)
- Confirm JE Telecom Part G versus SA IMD ECE Part E and intended use, then audit full official syllabus.
- Technical lessons and verified questions at correct paper depth, reuse only eligible GA/Reasoning content.
- Release JE Paper I on passing 50/50/100, 120m, +1/-0.25 tests.
- Release JE Paper II on passing 100 technical, 120m, +3/-1 tests; add calculator and telecom equation/diagram QA.
- JE variants other than Telecom remain unavailable until complete.

### M4: Shared polish + launch
- Integration with Stage-aware Analytics V2, Teacher V3, four-option explorer, planner, notes/revision and UI design system.
- Snapshot/E2E test matrix desktop/mobile, CGL I/II and JE I/II, auth, deep links, exam switch during active mock, no evidence leakage.
- Live Vercel→Render CORS/auth smoke, no active learner progress regression, P0/P1=0 and reliable warm route latency evidence. Human acceptance required.

## 8. Definition of done for each released stage
A stage is *ready* only if:
- Official notice/year and exam blueprint documented and reviewed.
- All mandatory subjects, subunits and question patterns mapped; content readiness audit has zero critical missing items.
- Published lessons teach accurately; question bank passes uniqueness/answer verification, difficulty spread, image/passage/source checks.
- Section timing, marking, locking, submission, resume and qualifying status match that stage exactly, including special typing where applicable.
- Stage-specific diagnostic is clearly labelled sampled, progress is evidence-backed, old learner data intact.
- Responsive, accessible UI and route loads verified on Vercel. CI + production smoke + user test passed.

## 9. Suggested implementation priority
**Now:** architecture and CGL Tier I completeness + existing Phase 7 teacher/analytics/UI improvements.
**Next:** CGL Tier II common Paper I including Computer Knowledge/DEST.
**After next week's exam:** JE Telecom Paper I and Paper II content in bounded, reviewed slices.
**Later:** optional CGL post-specific papers; other JE engineering/IMD tracks if verified demand.

No hosting or AI API purchase is required to write this plan or build the initial multi-exam foundation; costs are separate explicit decisions.
