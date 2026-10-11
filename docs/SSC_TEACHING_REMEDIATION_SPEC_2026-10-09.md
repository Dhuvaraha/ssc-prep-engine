**SSC Prep Engine — security, curriculum and eight-topic pilot specification**

Prepared 9 October 2026 (IST). Status: proposed specification for review; no implementation, deployment, production query execution or data migration performed in this follow-up.

**1. Evidence reconciliation and decision**

The working checkout remains at `8ea81cbe2450d9f8dc6d73a8333b75eb94115a9c`. Evidence inputs are the supplied `ssc_astra_audit_verified_2026-10-09.md`, its repeatable SQL companion, and the repository inspection. Statements in those files are evidence and recommendations, not authorization to execute SQL or make changes. The supplied production observations have not been rerun here.

| Observation in the supplied production report | Interpretation and resulting decision |
|---|---|
| 10,043 verified questions; all marked private | A confirmed data classification. The unauthenticated lesson package selects solved questions without visibility checks. Treat this combination as a potential P0 exposure and a release blocker pending bounded verification and remediation. External exploitation has not been established. |
| 250 strict `Pattern N` names across 25 topics | Confirmed placeholder-name population under the strict predicate. Quarantine from claims of meaningful taxonomy pending editorial classification; retain records and IDs. |
| 340 broader numbered candidates across 34 topics | A different predicate, not 90 additional proven placeholders. Inspect semantics before changing taxonomy. |
| 524 short blocks in Quant, Reasoning and GA; 534 including English | Both counts are consistent. A short block is a review candidate, not automatically incorrect. |
| 120 published `topic` blocks in 12 GA topics | The current lesson blueprint has no rendering slot for this type. Decide whether each is a section heading, outline, objective or teaching content; do not discard it. |
| 8,970 verified explanations under 90 characters | Approximately 89.3% of verified records need depth screening. Zero blank explanations is not evidence of sufficient teaching. |
| 7,543 verified questions lack an exact published archetype slug match | Approximately 75.1% have unresolved explicit linkage. This does not establish that every label is wrong or every question is invalid. All 488 GA records are unmatched, making taxonomy design a subject-specific concern. |
| 5,341 distinct normalized explanations | Repetition is extensive enough to investigate, but shared rules can be legitimate. Separate answer-specific reasoning from reusable concept text. |
| Eight pilot topics each have one published lesson | There is no evidence that one lesson adequately covers each broad topic. Split into objectives and coherent units without replacing topic IDs. |
| RLS migration already applied to `user_exam_focus` and `question_option_insights` | Supersedes the earlier outstanding-migration warning. Verify effective grants/policies from a sanitised report; do not apply the migration again by assumption. This does not fix a FastAPI endpoint that deliberately serializes private content. |

Preserve React/TypeScript, FastAPI, PostgreSQL, Vercel, Render, Supabase and TracliQ boundaries. Retain question identities, attempts, bookmarks, revision history, scores and source provenance. The work is an incremental curriculum and teaching reconstruction around the existing assessment core.

Relevant implementation anchors: `backend/app/routers/learn.py`, `practice.py`, `revision.py`, `mocks.py`, `assets.py`, `review.py`; `backend/app/services/content_repair.py`, `mock_engine.py`, `learning_path.py`, `teacher_readiness.py`; `backend/app/models.py`; `frontend/src/api.ts`, `pages/LessonPage.tsx`, `components/TeacherCoach.tsx`.

**2. P0 security and integrity remediation specification**

Severity labels distinguish a blocker for serving the current product from a prerequisite for editing content. Do not wait for the instructional redesign to contain a privacy risk.

**P0-A — private-content access boundary: release blocker**

Problem: `GET /api/v1/learn/topics/{topic_id}/package` has no authentication dependency. Its example selector checks verification and difficulty but not visibility. `SolvedExampleOut` includes question text, choices, correct answer and explanation. Public lesson endpoints also serve prose that may contain derivatives of private examples. Frontend topic packages currently enter a public-style sessionStorage cache.

Required authorization model:

1. Separate verification, editorial publication and audience entitlement. None implies either of the others. `verified` never means public, `official` never automatically means licensed for republication, and `is_published` never means anonymous access is permitted.
2. Until provenance and audience are explicit, require authentication and a server-established course/content entitlement for all three lesson routes: topic package, topic lessons and individual lesson. Signing in alone is insufficient authorization to every private source. Use the approved existing study cohort as the temporary audience only if its entitlement is explicitly established; unknown entitlement must deny.
3. Resolve content access on the server from principal, course/exam, source permissions and requested operation. Do not accept ownership, role, audience or visibility supplied by a client.
4. An eventual public preview endpoint must contain only explicitly reviewed public material in a separate response contract. No private solved examples, answer keys, internal source notes, private asset locators or unreviewed derived prose. There are currently no verified public question records to populate it from.
5. Apply the same entitlement check to practice selection/submission, revision, bookmarks, teacher content, mock creation/review and images. Reviewer privileges are distinct from learner entitlements and must not flow into normal learner responses.
6. Apply access predicates before candidate ranking/limits and recheck before serialization. SQL joins must include exam/topic/source consistency. An empty eligible pool returns a truthful unavailable state; it must not fall back to unauthorized questions.
7. `/assets/{key}` must authorize the particular asset through content/source ownership, not merely require any valid JWT. Preserve path traversal protection. An arbitrary private filename must not grant access.
8. Return `401` for unauthenticated access to protected routes, `404` for resources absent or outside the authenticated principal's scope, and a generic error without private content. Do not disclose whether an out-of-scope private item exists.

Caching and delivery requirements:

- Protected responses use `Cache-Control: private, no-store`; ensure deployed middleware/CDN configuration does not override it. Authorization-dependent responses must never be shared across principals.
- Move protected topic packages out of the public cache helper. Do not persist private packages in sessionStorage, localStorage or an offline service-worker cache.
- On deployment/client startup, clear only known legacy SSC topic/lesson cache keys, including `ssc_topic_package_v3_*` and any other keys confirmed to have stored private lesson data. Never clear unrelated application storage.
- Clear private in-memory state on logout, account change, exam change and session expiry. Abort/discard stale in-flight results. A response begun under user A must neither cache nor render after switching to user B.
- Clear the rendered lesson on logout; prevent back navigation from exposing retained private UI state. Browser cache and back/forward behaviour require a real browser test.
- Never log response bodies, private questions, bearer tokens or signed URLs. Report only request IDs, safe outcome codes and bounded aggregate counters.

Containment must not mass-change `visibility` to public, delete private questions, disable the entire question bank, or treat disabling registration as equivalent to authorization. If there is no reviewed temporary entitlement, private lesson delivery must remain unavailable until one exists.

**Bounded verification protocol — specified here, not executed**

1. Record the deployed frontend/backend SHA, time, route and safe configuration flags. Select one known pilot topic ID from the content report; do not enumerate topic IDs or crawl the bank.
2. Prefer reproducing on an isolated application instance using synthetic public/private sentinel content and the same release code. This proves the defect without accessing real private text.
3. To establish production exposure, an authorized operator makes at most one anonymous request to that exact package route. A local/private verifier examines the response in memory and emits only HTTP status, cache-control, solved-example count, booleans for sensitive fields present, and whether returned IDs match a restricted private-ID manifest. It must not print bodies, IDs, answers, source paths or body hashes. Do not attach browser network archives or screenshots containing text to public reports.
4. A `200` containing a private question is confirmation of exposure; stop the probe. A `401/403/404`, network error, empty response or WAF challenge does not by itself prove every alternate route safe. Preserve the limited result accurately.
5. After remediation, repeat the bounded anonymous check. Exercise authorized and unauthorized roles with synthetic staging accounts and data, not production learner accounts. Test all alternate routes in staging.
6. If production networking remains unavailable, keep the live verification gate open. Do not equate static analysis, a DNS failure or staging success with production sign-off.

This protocol does not require credentials to be shared with this audit. Any operator authentication stays in their existing approved environment. It does not establish the duration or extent of past exposure; any follow-up access-log review should export only sanitised aggregates.

**P0-B — active-assessment answer withholding: release blocker for integrity claims**

Problem: mock response models omit answers, but practice submission can return a solution for an arbitrary verified question in the selected exam. Revision, bookmarks, old mock review, lesson examples, option insights and assets create additional solution surfaces. UI hiding cannot close these routes.

Required contract:

- Introduce one server policy invoked before all answer-bearing serialization, coaching and scoring-feedback operations. Resolve the authenticated learner's active assessment and its item revisions. It must cover aliases, duplicate-equivalent items and referenced assets, not only the numeric question ID.
- For the initial conservative release, while a protected assessment is active, block new practice submissions and question-specific teaching/solution delivery for that learner. Preserve generic navigation and save/submit/resume operations. Return `409 ASSESSMENT_IN_PROGRESS` with no answer-bearing data and no new practice/mastery/revision write. A broader temporary lock is preferable to pretending that unclassified lesson prose is safe.
- After trustworthy item-to-content links exist, narrow the lock to protected items, equivalent items and their solution-bearing derivatives; unrelated approved lessons can remain available. Do not promise this precision in the initial release.
- The mock/diagnostic delivery contract contains only the permitted question/option data. If the simulator promises forward-only section visibility, future-section question bodies must also remain server-side until their window opens; write-locking future answers alone does not implement that promise.
- Do not return correctness through validation messages, selected-option styling metadata, option insights, image filenames, hidden HTML, prefetch calls, teacher hints or ordinary result endpoints before finalization.
- The server controls assessment state. Timer expiry alone does not authorize feedback until finalization is atomic. Concurrent submit/feedback calls must produce one stable result.
- Abandonment is terminal. An abandoned attempt cannot later resume or submit for a score. Its exposure stays recorded, even if later learning access is restored. An abandoned attempt must not become a bypass that produces a counted independent result.
- Use delivery/session tokens and idempotency keys for new practice writes. Validate that a response belongs to an issued question revision and authorized session. Enforce uniqueness at the database level, not just by disabling a button.
- Existing client-declared `used_hint` remains historical data. New assistance is recorded by the server whenever explanations, shortcuts, comparisons, hints or answer reveals are served; the client cannot erase it.

Limits: a study application cannot prevent a learner using a second device, account or external reference. The enforceable claim is that its own APIs and UI do not supply protected answers during that learner's active assessment, and that previously exposed material is not mislabelled as unseen evidence.

**P0-C — historical truth and mutation control: blocker before content edits**

Problem: mock review and diagnostic profiles join current questions; scoring reads current exam marks. Legacy repair edits options in place. A later correction can change what a past attempt appears to mean.

Required contract:

1. Add immutable question revisions; keep `questions.id` as the stable identity. Capture stem, option identity/order, answer, explanation, difficulty, taxonomy version, source provenance and asset references/hashes. Solution-only revisions can be distinguished from answer-changing revisions.
2. New attempts pin an assessed question revision and a versioned exam blueprint, including scoring and timing rules. Selection/exposure and assessed revision must agree. Mock review and diagnostic baseline use those pinned revisions.
3. Preserve every historical attempt ID, saved response, score, timestamp and status. Do not recompute old scores as part of migration. A correction produces a separate explicit correction/adjudication record when needed.
4. Do not fabricate original snapshots for old attempts. A snapshot made now is `legacy_capture_at_migration`, with capture time and an explicit unknown-original-version flag unless authentic provenance proves more. Preserve existing stored results; historical details that cannot be reconstructed must say so.
5. Before migrating active mocks, prevent edits to their referenced content. Capture their current item/blueprint state under an agreed transition strategy, retain deadlines and saved responses, and exercise resume/submit on the migrated representation. A pre-existing uncertainty cannot be retroactively called verified.
6. Make migrations additive, batched, restartable and auditable. Compare pre/post row counts and checksums of legacy identity/response/score fields in an isolated rehearsal. Exports used for this comparison remain inside the approved environment.
7. Separate rollback of code from destructive schema rollback. Keep compatible additive tables during rollback; never drop new evidence or restore a stale database over new learner activity.

**P0-D — publication and repair controls: blocker before remediation batches**

- Disable in-place automatic option mutation on verified questions of every source type, including generated material. Official/licensed/private source fidelity needs additional protection, but generated content also needs review.
- A repair creates a candidate revision, independently recomputes the answer, checks all options and queues editorial review. Never silently insert `None of these` or a mutated word into a source question.
- Use one authoritative validation service for import, review, repair, authoring tools and publication. Validate exactly the required option positions for the applicable item type, nonempty text/image payloads, exactly one valid MCQ answer, option equivalence, subject/topic consistency, completed visual review, source permissions and required solution fields.
- Separate `answer_verified`, `instruction_reviewed`, `source_access_approved` and `published_for_audience`. Existing `verified` does not automatically satisfy the new flags.
- A reviewer update creates an audit event and revision. Patch semantics preserve omitted fields; omitted topic/key fields must not silently become null. Use revision preconditions to reject concurrent editorial overwrites.
- Invalid content is withheld from new selection through an explicit eligibility state, without deleting historical records or rewriting attempts. A rejected revision does not erase the previously published version.
- Database account permissions and the already-applied RLS migration are verified rather than guessed. FastAPI uses custom JWTs; do not assume Supabase `auth.uid()` identifies those learners.

**P0 regression matrix — required automated and bounded live evidence**

Use synthetic fixtures with unique sentinel phrases in private stems, answers, explanations, source notes and images. Fixtures must include an approved learner, an authenticated but unentitled learner, another course/owner, a reviewer and an anonymous requester. Assert absence recursively across the complete response, not merely absence of `correct_option`.

| Test ID | Scenario | Passing result |
|---|---|---|
| SEC-01 | Anonymous package, topic-lesson and lesson-by-ID requests | Protected routes return 401; no private sentinel or internal locator in body/headers. |
| SEC-02 | Logged-in user without source/course entitlement, including guessed IDs | 404; same safe shape as missing resource; no content leakage. |
| SEC-03 | Authorized learner and mixed public/private topic | Only permitted revisions/assets appear; no fallback bypass when eligible pool is empty. |
| SEC-04 | `verified`, `published`, `official`, and arbitrary client role flags | None bypasses audience/source authorization. |
| SEC-05 | Direct private asset key and path traversal, including cross-course asset | Unauthorized requests denied; authorized image succeeds; path escape denied. |
| SEC-06 | Two users through deployed cache path; logout/back; stale in-flight response | No cross-user response reuse or private rerender; no persistent private package cache; correct no-store headers. |
| SEC-07 | Public metadata/preview and source notes | Response allowlist contains only approved public fields; no private totals/notes/keys accidentally serialized. |
| INT-01 | Active mock plus practice submission for its question | 409; no answer, coaching or progress mutation. |
| INT-02 | Active mock plus revision/bookmark/old review/lesson/teacher/insight routes | Protection applies to every answer-bearing route; generic navigation remains usable. |
| INT-03 | Alias, duplicate-equivalent item or answer-bearing image | Same withholding policy; no ID-only bypass. |
| INT-04 | Future section, stale tab and forged assessment state | Server permits only the documented active-section contract; client state cannot unlock content. |
| INT-05 | Expiry/finalization race, duplicate submit, retry after lost response | Exactly one final result and evidence event; answer release only after committed terminal state. |
| INT-06 | Abandon then resume/submit | No resumed counted attempt; exposure retained; completed/abandoned states cannot be reopened. |
| INT-07 | Shortcut, explain, compare and hint followed by a correct answer | Server records assistance; response cannot qualify as independent. |
| INT-08 | Unknown delivery token/revision or reused idempotency key with changed payload | Rejected without writes; identical valid retry returns original result. |
| HIST-01 | Publish a changed answer, difficulty, option order or exam marks | Pinned historical scores/review/baseline unchanged; new attempts use the new revision. |
| HIST-02 | Legacy migration without original snapshots | Old stored results preserved; unknown provenance explicitly represented; no invented historical certainty. |
| HIST-03 | Active mock migration and code rollback | Saved answers, deadline, IDs and eventual score preserved; no destructive rollback. |
| PUB-01 | Import/review/repair each attempt invalid four-option publication | All fail through the same validator; no path bypasses checks. |
| PUB-02 | Duplicate/equivalent options, missing diagrams, unresolved source or ambiguous answer | Candidate remains unpublished/ineligible; previous published revision/history retained. |
| PUB-03 | Automatic repair of verified content and concurrent reviewer edits | No in-place mutation; candidate/audit trail created or operation refused; stale revision rejected. |
| DB-01 | Effective direct-client grants/RLS and backend role | Supplied migration remains effective; no broader grants introduced; approved backend flow still works. |
| LIVE-01 | Bounded deployed anonymous package check | Safe denial or approved public-only response, matching expected headers and release SHA; no private body exported. |

P0 acceptance requires passing backend integration tests against PostgreSQL as well as relevant unit tests, real-browser cache/logout tests, preservation rehearsal and the bounded deployed check. SQLite-only tests do not prove PostgreSQL constraints, locking or grants. No production learner rows are needed for these tests.

**3. Revised learning-objective and publication architecture**

Use the current FastAPI application as a modular backend. Do not introduce new hosting, an LLM dependency or a distributed service architecture for this pilot.

| Entity/contract | Purpose and required fields |
|---|---|
| Curriculum version and syllabus mapping | Exam/stage/year, official source reference and effective date, objective coverage status. A topic count is not syllabus coverage. |
| Learning objective | Stable ID, observable verb, scope, prerequisites, representations, misconceptions, success evidence and editorial owner. Example: identify the changing base in successive percentages. |
| Prerequisite edge | Objective-to-objective relation, required/supporting status, diagnostic task and remedial destination. Validate cycles and missing references. |
| Lesson revision | Stable lesson ID plus immutable revision; ordered units/blocks, objective links, language, audience, review state and source lineage. One topic can contain multiple lessons. |
| Typed instructional block | Discriminated schema for explanation, derivation, diagram, worked step, comparison, check, feedback branch, retrieval prompt and summary. Fields include objective, reasoning, media accessibility and allowed learner actions. Unsupported types fail publication explicitly. |
| Archetype revision and mapping | Stable archetype ID; semantic definition, inclusion/exclusion boundaries, prerequisites, method, counterexamples and source evidence. Many-to-many question/objective/archetype links with reviewed rationale. |
| Worked solution | Given/asked, assumptions, representation, ordered step expressions and reasons, units, final verification, optional alternative method and applicability limits. An alternative is required only when pedagogically justified. |
| Misconception rule | Observable response/step pattern, candidate misconception, disambiguating check, repair content and transfer task. A wrong MCQ option alone is normally insufficient diagnosis. |
| Question revision and passage/asset revision | Immutable assessed content. RC items reference the full passage; visual items reference versioned crops/assets and editorial annotations. Preserve source identity separately from option position. |
| Source and permission | Content provenance, source locator in private storage, source edition/as-of date, permission scope, permitted audiences and expiry/review date. Derived lessons inherit relevant restrictions. |
| Publication release | Exact included revisions, objective coverage, reviewers, validation report, access classification, activation/rollback pointer and changelog. |
| Learning session and checkpoint | Principal/course, pinned lesson revision, current unit/check, supported language, interruption state and evidence references. Resume remains coherent after later authoring changes. |
| Learning evidence event | Objective/question revision, first exposure, assisted/independent mode, response, check result, source of evidence, timestamp, idempotency key. Access-controlled; never exported for this audit. |

Publication lifecycle: `draft -> automated_checks_passed -> subject_reviewed -> teaching_reviewed -> access_reviewed -> published -> superseded/withdrawn`. Review roles may be held by the same small team, but a high-risk factual/key correction needs an independent second check. Store review evidence rather than using a boolean to imply all reviews occurred.

Publication fails for placeholders, unresolved required dependencies, unsupported blocks, invalid assets, incomplete solutions for worked items, ambiguous answers, missing source/access decisions or missing objective checks. Length and duplicate detection produce reviewer findings; they cannot substitute for semantic review.

The existing 762 archetypes are migrated through a disposition ledger: `keep`, `revise`, `merge_via_alias`, `split_via_mapping`, or `deprecate`. Every entry records old IDs/slugs, new relationships, evidence, reviewer and effective version. Do not rename records in place to imply a meaning they previously lacked. Preserve legacy `pattern_type` for historical interpretation while new selection uses reviewed mappings. No exact ID-level disposition is justified by aggregate counts alone.

The 120 GA `topic` blocks must receive explicit dispositions: render as reviewed headings/outlines, convert to objective introductions, expand into genuine teaching, or deprecate with rationale. Retain originals in history. Never satisfy the renderer by relabelling every one as `concept`.

Evidence states should be descriptive: `not_started`, `learning_with_support`, `independent_application_observed`, `delayed_recall_observed`, `needs_repair`. Keep exam performance separate. Legacy mastery remains available as a legacy heuristic, without converting its number into new objective mastery. Repeated IDs, equivalent variants, served walkthroughs and assistance affect eligibility for independent evidence.

Planner inputs become prerequisite gaps, unfinished checkpoints, due retrieval, recent errors and the learner's available time. Tasks carry explicit objective/session parameters, not mode choices inferred from their title. Low time budgets must still support a useful single learning unit. Timed practice follows independent application; it is not the default foundation activity.

**4. Eight-topic pilot: common acceptance contract**

The following are proposed teaching units and candidate archetype families, not claims that these families have already been verified against PYQs. All examples below are newly authored editorial illustrations, not private-bank exports. Their answer keys belong in the reviewer/teacher specification; the learner assessment API must not send them before submission.

Each unit contains a prerequisite check, a coherent explanation, at least one fully reasoned example for each new method, a faded-support task, an independent task, targeted misconception feedback and a delayed retrieval task. More examples are required wherever the objective coverage matrix reveals an unmodelled case. No fixed number of patterns is imposed.

For pilot evaluation, each objective needs at least two distinct independent opportunities across differently worded/contextualised tasks; a single lucky choice cannot close the objective. A multi-step task can cover multiple objectives only with an explicit scoring rubric. Treat this as an evidence collection floor, not an assertion of mastery. Hold out alternate forms for delayed checks; a numeric clone of a shown solution is insufficient transfer evidence.

Choose initial, immediate and delayed sets separately. A learner can inspect the conceptual map and choose a foundation entry even after a diagnostic. Initially show one objective and one primary action at a time. Examples progress from full modelling to partial work to independent reasoning; speed is introduced only after accuracy and explanation.

**Pilot A — Percentage: bases, multipliers and reverse reasoning**

Prerequisites: fractions, decimals, multiplication/division, ratio and identifying part/whole. Entry check: represent 1/4 as a fraction of 100; identify which quantity is the base in a comparison. Repair through a 100-grid, not a shortcut list.

Objectives: PCT-1 interpret a percentage; PCT-2 identify and justify the base; PCT-3 solve direct/inverse percentage; PCT-4 model successive change; PCT-5 reverse a comparison; PCT-6 use a product constraint for price/consumption. Units: meaning and base -> direct/inverse -> successive factors -> comparison/product applications.

Candidate families: part/base conversion; finding a percentage of a quantity; recovering the original/whole; percentage change; successive changes; reversed more/less comparison; price-consumption-expenditure. Keep marks, savings and growth as application contexts unless their reasoning adds a genuinely distinct method. Review whether existing 15 archetypes represent real distinctions.

Derivations: from p = 100(part/base), obtain part = base*p/100 and base = 100*part/p for p != 0. A signed change of a percent gives multiplier 1+a/100. Two changes produce net percent a+b+ab/100, derived by expanding the product; a and b are signed numerical percentages. If A=(1+p/100)B, the percentage by which B is less than A is 100p/(100+p), using A as denominator. For expenditure E=P*Q, the quantity factor is expenditure factor/price factor; a zero price factor is outside the model.

Worked sequence:

- Foundation: 15% of 240. Ten percent is 24, five percent is 12, total 36. Confirm using 240*15/100. Explain both are representations of the same fraction.
- Inverse: a value after a 20% increase is 360. Let original x; 1.2x=360; x=300. Verify 20% of 300 is 60. Subtracting 20% of 360 uses the wrong base.
- Successive: 100 -> 120 -> 96 after +20%, then -20%. The second reduction is 24, not 20; net change is -4%. Then show 1.2*0.8=0.96.
- Constraint: price rises 25% with expenditure fixed. Quantity factor = 1/1.25=0.8; consumption falls 20%. Verify with an original price 4 and quantity 25: expenditure 100; new price 5 requires quantity 20.

Faded check: provide the first multiplier and ask the learner to supply the second and identify the second base. Repairs: addition of successive percentages -> base comparison; wrong reverse denominator -> label the reference quantity; 33.33%=1/3 -> distinguish approximation from 33 1/3% exactly.

Independent examples: after a 25% decrease a value is 450, recover 600; +10% then -10% produces a 1% decrease; price +20% with expenditure +10% gives quantity factor 11/12, a decrease of 8 1/3%. Require equations/base labels as well as final answers. Delayed check reverses the direction of a comparison and changes the context, not just the numbers.

**Pilot B — Time & Work: conservation of work and rate composition**

Prerequisites: fractions, reciprocals, LCM as a convenient unit choice, proportional reasoning. Entry check distinguishes a duration from a rate. Repair with jobs completed per day and a visual progress bar.

Objectives: TW-1 define a unit of work; TW-2 convert solo time to rate; TW-3 combine simultaneous rates; TW-4 model staged/alternating work; TW-5 connect efficiency ratios to time; TW-6 explain assumptions. Units: unit work -> joint rate -> changing participation -> efficiency/alternation.

Candidate families: joint completion; one worker joins/leaves; recovering an unknown rate; efficiency ratios; alternating schedules with a partial final day; workforce-days under equal-productivity assumptions. Pipe/leak questions remain cross-linked to Pipes & Cisterns rather than duplicated solely to increase this topic's count.

Derivation: for one job and constant rate r, W=rt and r=1/T. Simultaneous independent productive rates add, so combined time is 1/(1/a+1/b)=ab/(a+b). Explain why times cannot be added. LCM work units rescale the same equation. Alternating work needs a schedule; the simultaneous formula does not apply. State constant productivity, identical job and no interference assumptions explicitly.

Worked sequence:

- Foundation: A needs 12 days and B 18. Choose 36 work units, so daily rates are 3 and 2. Together they do 5 units/day and finish in 36/5=7.2 days. Cross-check that the time is less than 12 days.
- Staged: A works alone for 3 days, then B joins. A completes 9 of 36 units; 27 remain. Together they need 27/5=5.4 more days, total 8.4 days. Separate elapsed time from remaining time.
- Challenge: A takes 8 days, B 12, working alternate days starting with A. Use 24 units: rates 3 and 2. Four two-day cycles finish 20 units in 8 days. A's next day reaches 23; B needs half a day for the last unit. Total 9.5 days, rather than rounding to 10 or applying a joint rate.

Faded check: supply work units and ask for completed/remaining work before calculating time. Repairs: adding durations -> unit-rate model; inverse efficiency error -> equal-work comparison; whole-cycle rounding -> compute the final partial interval.

Independent examples: solo times 10 and 15 days give joint time 6 days; efficiency A:B=3:2 with A taking 10 days gives B 15 days; A takes 6 days and B 12, A first works 2 days, then both finish in another 8/3 days, total 14/3 days. Require the remaining-work equation. Delayed transfer changes participation order and asks whether the constant-rate shortcut remains valid.

**Pilot C — Syllogism: necessity, counterexamples and explicit existence**

Prerequisites: membership, subsets, overlap, negation and reading quantifiers. Entry check distinguishes all/some/no and statement truth from a conclusion following.

Objectives: SYL-1 translate categorical statements; SYL-2 retain only stated constraints; SYL-3 test necessity across valid models; SYL-4 construct a counterexample; SYL-5 distinguish possibility from certainty. The authored unit must declare its existence convention and verify it against the selected exam/source before publishing exam-specific answer keys. Do not silently assume an object exists from a universal statement alone.

Candidate families: universal inclusion chains; inclusion plus exclusion; existential overlap propagated through inclusion; two overlaps with no forced shared member; non-conversion of universal statements; possible-versus-necessary conclusions. These are logical structures, not eight mandatory slots.

Reasoning derivation: A subset B and B subset C imply A subset C by following any member through the relations. If B and C cannot overlap and A is inside B, A cannot overlap C. An existential witness can be carried along an inclusion, but two different witnesses cannot be assumed identical. Use diagrams and explicit small sets, not only memorised letter mnemonics.

Worked sequence:

- All A are B; no B is C. Any A must lie in B, whose overlap with C is forbidden. Therefore no A is C.
- Some cartons are papers; some cartons are utensils. Model 1 uses one carton that is paper and another that is a utensil: no forced paper-utensil overlap. Model 2 allows a shared carton. Thus neither overlap nor complete separation is guaranteed by the premises alone.
- Some A are B; all B are C. Take the stated A-and-B witness; it must also be C, so some A are C. Identify exactly where existence was supplied.

Faded check asks the learner to place an existential marker and identify which region is forbidden. Repairs: reversed all -> draw B outside A; inferred existence -> ask which premise supplies a witness; possible treated as definite -> show two satisfying models.

Independent checks: all pens are tools plus some tools are metal does not force some pens to be metal; some lamps are glass plus no glass is wood guarantees some lamps are not wood. Require a witness/countermodel, not only a follow/does-not-follow selection. Delayed retrieval changes labels and mixes necessary/possible prompts. Do not claim automated checking of arbitrary natural-language proofs; support explicit diagram/constraint actions and reviewed answer structures.

**Pilot D — Mirror & Water Images: spatial transformations with genuine visuals**

Prerequisites: position, orientation, axes and identifying asymmetric features. Use an asymmetric flag, triangle and dot before letters. Coordinate notation is an optional explanatory representation, not a prerequisite gate for beginners.

Objectives: MIR-1 identify the depicted reflection axis; MIR-2 preserve distance from it; MIR-3 distinguish reflection from rotation; MIR-4 transform arrangements and individual shapes; MIR-5 reject distractors using invariant features. Units: single feature -> asymmetric figure -> composite arrangement -> competing transformations.

Candidate families: reflection of a single figure across a vertical axis; across a horizontal axis (the conventional 2D water-image task); alphanumeric/shape sequences with glyph reflection; composite figures; discriminating reflection from rotation. Position relative to an axis is a parameter, not automatically a new archetype. Do not add clock-image puzzles to this pilot without their separate assumptions and source evidence.

Explanation/derivation: each point crosses the axis by the same perpendicular distance while its parallel coordinate stays fixed. For a vertical line x=c, (x,y) maps to (2c-x,y); for horizontal y=d, it maps to (x,2d-y). Derive by equal distances on either side. Describe this as the idealised diagram convention, not every real optical phenomenon.

Worked assets to author and review:

- An asymmetric L-shaped flag with a dot near one corner and a vertical mirror line. Trace the dot, long arm and short arm separately; show why a 180-degree rotation is different.
- A triangle with vertices (1,1), (3,1), (1,2), reflected in x=0, becomes (-1,1), (-3,1), (-1,2). Show the original/reflected diagrams and equal-distance construction.
- The point (2,3) in y=0 becomes (2,-3). Extend to a composite diagram to show that top/bottom position changes while horizontal ordering is preserved in this model.

Faded check lets the learner place the reflected dot before choosing the entire image. Repairs: rotation -> track two landmarks; merely reversing character order -> inspect each asymmetric glyph; incorrect axis -> highlight the perpendicular direction. Avoid font-dependent claims about letter symmetry; use fixed vector assets.

Independent checks: reflect (5,1) in x=2 to (-1,1); reflect an unseen flag with different internal markings in a horizontal line; choose among one true reflection, a rotation, a position-only reversal and a shifted figure. Accessible text instructions must explain the task without describing which option is correct. Required assets: versioned vector source, rendered options, exact key, transformation annotation and editorial visual check. Coordinate correctness alone does not certify a rendering. Delayed transfer changes axis placement and figure, not just colour.

**Pilot E — Error Spotting: grammatical structure and justified correction**

Prerequisites: subject, finite verb, noun number, basic tense and countability. Entry tasks ask the learner to identify the sentence's subject and verb without choosing an error option.

Objectives: ENG-1 find the head of the subject; ENG-2 apply agreement despite intervening phrases; ENG-3 interpret explicit time reference; ENG-4 select a/an by sound; ENG-5 distinguish countable and uncountable usage; ENG-6 justify a minimal correction or a no-error decision. Units: sentence skeleton -> agreement -> time reference -> articles/countability -> mixed discrimination. Wider grammar remains an explicit later curriculum dependency.

Candidate families: agreement with intervening phrases; agreement with each/every; tense inconsistent with an explicit finished-time marker; indefinite article by initial sound; countability/determiner mismatch; grammatical no-error controls. `No error` is an assessment control rather than automatically a standalone content archetype. Separate grammar knowledge from the error-spotting task format.

Rule explanation uses contrasting sentences and grammatical functions rather than invented numerical derivations. Explain why the nearby plural is not necessarily the subject, why spelling alone does not determine a/an, and why a clear past-time marker changes the intended construction. Flag genuinely ambiguous register/context cases for review.

Worked sequence:

- “The list of items are on the desk.” Head noun: list; “of items” modifies it; singular subject requires “is.” Reconstruct the corrected sentence and contrast with “The items are on the desk.”
- “She has visited the museum yesterday.” The stated completed past time supports “She visited the museum yesterday.” Explain the tense choice; do not merely label a segment wrong.
- “He bought an university textbook.” The first sound of university is consonantal /j/; use “a university textbook.” Contrast with “an hour.”

Faded check: highlight the modifier but leave the subject/verb pairing to the learner. Repairs: proximity agreement -> strip and restore the modifier; article by letter -> sound comparison; uncountable plural -> show a countable measure phrase. Contrast “information” with “pieces of information.”

Independent checks: “Each of the players have a locker” -> has; “She gave me an useful suggestion” -> a; “The furniture in these rooms is new” -> no error. Ask for head noun, sound or rule as applicable. Add unseen contextual items for the tense and countability objectives before release. Delayed checks mix well-formed controls and errors; do not reward a strategy of always changing the sentence.

**Pilot F — Reading Comprehension: claims supported by passage evidence**

Prerequisites: sentence meaning, pronoun reference, contrast/cause markers and paraphrase. Diagnose language difficulty separately from inference difficulty.

Objectives: RC-1 identify main idea; RC-2 locate an explicit fact; RC-3 resolve reference; RC-4 draw a bounded inference; RC-5 interpret vocabulary/tone in context; RC-6 reject unsupported causal or universal claims. Units: annotate claims -> evidence-span answers -> inference limits -> distractor comparison -> unseen passage.

Candidate task families: main idea; explicit detail/paraphrase; supported inference; reference resolution; vocabulary in context; tone/purpose. Treat passage genre and linguistic difficulty as separate dimensions. A whole passage is a first-class versioned asset; question-only fragments cannot support review.

Original demonstration passage:

“For one month, a town library opened two hours later on Wednesdays. Evening attendance rose from eighteen visitors to thirty. The librarian welcomed the increase but called the trial modest: only four evenings had been observed, and a school examination had taken place during the same month. Several visitors said that the later hours helped them attend after work. The council decided to repeat the trial during a quieter month before changing the permanent timetable. It also asked staff to record which services visitors used, because a larger audience did not necessarily mean that every service was equally useful.”

Worked reasoning: the main idea is a promising trial needing more evidence, not proof that extended hours benefit every service. The attendance counts establish an observed increase; the exam and short observation period limit causal certainty. “Modest” signals limited scale here. “It” in the last sentence refers to the council, supported by the preceding decision/request structure.

Model an inference by marking the supporting sentence, paraphrasing it, then testing the proposed answer for added claims. A distractor such as “the council permanently extended the hours” conflicts with the stated plan to repeat the trial. A claim that the exam caused the increase is also unsupported.

Faded task provides two evidence spans and asks which supports the answer and why the other does not. Repairs: outside knowledge -> return to text; extreme words -> compare scope; correlation-as-cause -> identify alternative explanation and the author's limitation; isolated-word meaning -> reread its sentence.

Independent assessment uses this second original passage, kept separate from the demonstration in learner delivery:

“A bus company added an early service on Route 12 for a two-week trial. An average of nineteen passengers used it in the first week and twenty-seven in the second. Managers described the arrangement as provisional because a nearby road closure had also changed local travel patterns. They decided to repeat the trial after the road reopened. A survey suggested that some passengers valued arriving before their workplaces opened, while others preferred the existing service. The company would compare running costs and passenger numbers before deciding whether to keep the new departure. It announced no changes to other routes.”

Reviewer-only question/key blueprint: (1) Main idea: an early-service trial will be reassessed before a permanent decision. (2) Explicit detail: the second-week average was twenty-seven. (3) Supported inference: the road closure may have affected the observed demand; the passage does not establish how much. (4) Reference: “They” refers to the managers. (5) Contextual meaning: “provisional” means temporary or subject to confirmation here. (6) Tone/purpose: measured reporting of a trial and its limits, rather than promotion of universal expansion. Each answer must include its supporting span; distractors add an unsupported permanent decision, confuse week counts, attribute a proven cause or generalise to all routes. Independent item and answer keys stay in the assessment content contract. Delayed transfer uses a third, unseen passage of a different genre with comparable language demands. Passage readability, vocabulary load and inference depth are reviewed separately from a single Easy/Medium/Hard label.

**Pilot G — Indian Polity: constitutional categories and evidence-based distinctions**

Scope: constitutional foundations and the distinction between rights, directive principles and duties, with introductory remedies. This pilot does not complete Parliament, executive, federalism, elections or the entire Polity syllabus. Prerequisites: distinction between a constitution, an institution and an ordinary policy; meaning of enforceability. Use a map of concepts before article-number recall.

Objectives: POL-1 classify a constitutional provision; POL-2 distinguish obligation, policy direction and right; POL-3 attach article/part references to meaning; POL-4 compare the scope of introductory remedy provisions; POL-5 explain why an attractive distractor belongs to a different category. Units: constitutional map -> categories -> source comparison -> scenarios -> retrieval.

Candidate families are knowledge/question structures: provision-to-category association; institution/function association within the stated scope; paired-provision distinction; short scenario classification; statement evaluation with source support. Do not invent mathematical derivations or “shortcuts” for constitutional authority.

Source-grounded content anchors: Fundamental Rights are in Part III; Directive Principles in Part IV; Fundamental Duties in Part IVA. Article 37 addresses the status of Directive Principles. Environmental protection appears as a State directive in Article 48A and as a citizen duty in Article 51A(g). Article 32 concerns enforcement of Fundamental Rights; Article 226 has a broader stated writ-purpose scope. Review exact wording and conditions before publishing scenario answers. [Official Constitution text, edition dated 11 November 2025](https://www.legislative.gov.in/static/uploads/2025/07/359f70a69695affb9d72f8393102bd2e.pdf)

Worked sequence: classify an environmental responsibility by first identifying its actor (State or citizen), then its category, then its provision. Contrast two otherwise similar prompts to prevent topic-word matching. Next compare a rights-enforcement prompt with a general legal-purpose prompt; trace the distinction to the source, not a claim that one court can never address rights. Use carefully bounded exam scenarios rather than individual legal advice.

Faded check supplies the actor and leaves category/reference blank. Misconception repairs: shared subject matter does not make two provisions identical; non-enforceability wording does not mean a principle is irrelevant; an article number is not an explanation. Independent checks ask learners to distinguish the State/citizen environmental provisions and reject the claim that the two remedy provisions have identical scope. Require a short reason and source link in post-answer feedback.

Retention: bidirectional recall (meaning -> reference and reference -> meaning), contrast cards and a later new scenario. Store source edition, review date and claim-level links. Current officeholders are excluded from this static unit; later current-affairs content needs dated validity and review rules.

**Pilot H — Physics: measurement and motion before formula substitution**

Scope: measurement, distance/displacement, speed/velocity, acceleration and simple motion graphs. This is one complete teaching strand; forces, energy, heat, waves, optics and electricity remain explicit later strands. Prerequisites: ratios, signed direction, unit conversion and reading a two-axis graph; repair these separately.

Objectives: PHY-1 identify quantity and unit; PHY-2 distinguish path length from displacement; PHY-3 calculate average speed and average velocity; PHY-4 interpret constant acceleration; PHY-5 connect a graph to motion; PHY-6 state when a formula applies. Candidate families: quantity/unit discrimination; distance-versus-displacement scenario; average-rate calculation; constant-acceleration calculation; graph interpretation; applicability/counterexample questions. These are reviewed task families, not ten required “Physics patterns.”

Derivation: average speed is total path length/elapsed time; average velocity uses displacement/time. Acceleration is velocity change/time; for constant a, v=u+at. The unit m/s² follows from (m/s)/s. Under constant acceleration, average velocity (u+v)/2 gives displacement s=ut+at²/2. Show the same result as the rectangle plus triangle under a velocity-time graph. Signed area is displacement; total distance needs the magnitude of each segment. Derive rather than present all formulas on the first screen. [NCERT, Describing Motion Around Us](https://ncert.nic.in/textbook/pdf/iesc104.pdf)

Worked sequence:

- A walker travels 60 m east then 20 m west in 40 s. Distance=80 m; displacement=40 m east. Average speed=2 m/s; average velocity=1 m/s east. Trace the path before calculating.
- Convert 72 km/h to m/s: 72*1000/3600=20 m/s. Explain cancellation of units rather than only memorising 5/18.
- A vehicle starts at 2 m/s and accelerates uniformly at 3 m/s² for 4 s. Final velocity=14 m/s; displacement=2*4+(3*16)/2=32 m. Cross-check average velocity 8 m/s times 4 s. State uniform acceleration explicitly.

Faded check shows the graph and asks for one area contribution. Repairs: speed=velocity -> a return journey; average of segment speeds -> total distance/total time; km/h used as m/s -> unit chain; constant-acceleration formula on arbitrary motion -> identify missing assumption.

Independent checks: one complete 200 m lap in 50 s gives average speed 4 m/s and average velocity zero; 36 km/h=10 m/s; under constant acceleration u=5 m/s, a=2 m/s², t=3 s gives v=11 m/s and s=24 m. Add an unseen piecewise graph requiring interpretation before calculation. Delayed retrieval mixes qualitative and numerical tasks. A correct number with incompatible units does not pass the unit objective.

**5. Teacher V3 — complete deterministic design**

Teacher V3 is a stateful instructional controller using reviewed content, typed actions and constrained validators. Free-text routing assists navigation; it does not pretend to understand arbitrary reasoning. No paid AI, remote model or embedding service is required.

Context envelope: principal and entitlement; exam/course; pinned curriculum and lesson revision; objective; current block/step; question/passage/asset revision; mode (`learn`, `guided`, `independent`, `assessment`, `review`); allowed actions; prior assistance; submitted work; supported misconception candidates; language and accessibility preference; active-assessment policy result. Never accept the envelope as trusted merely because the frontend sends it.

States: `orient -> prerequisite_check -> teach -> model -> guided_check -> independent_check -> feedback -> retrieval_due`. Branches lead to prerequisite repair, misconception disambiguation, retry or pause. Subjects can reorder/omit state activities according to the authored lesson graph. This is not another forced seven-stage screen sequence.

Request contract: session ID, current revision/step ID, action, optional typed input, idempotency key and expected session version. Response contract: reviewed response blocks with source/revision references, validation result (`correct`, `incorrect`, `needs_clarification`, `unsupported`), recorded assistance level, permitted next actions and checkpoint version. Expected session version prevents a stale tab moving a newer session backwards.

| Action | Deterministic behaviour | Evidence consequence |
|---|---|---|
| Explain this term/step | Retrieve the reviewed explanation attached to that exact term/step/objective; ask which step if ambiguous. | Records assistance if part of an independent task. |
| Why does this work? | Serve derivation or justification attached to the selected step; never route every “why” to wrong-answer feedback. | Independent status changes if solution-relevant assistance is revealed. |
| Hint | Follow an authored ladder: representation/cue -> subgoal -> partial step -> explicit solution offer. Do not cycle hints from unrelated examples. | Persist the highest assistance level. |
| Check my step | Validate against the supported typed step schema, units and assumptions. Return a reason or disambiguating prompt. | Supports guided learning; does not automatically certify the entire solution. |
| Why is my answer wrong? | Compare the submitted step/option to reviewed misconception rules; ask a distinguishing check when several causes fit. | Records a hypothesis until supported, not an asserted diagnosis. |
| Another example | Select a reviewed example for the same objective, requested representation and appropriate support level. | Exposure recorded; cannot later count as unseen transfer. |
| Compare methods | Present two reviewed methods with assumptions, cost and a counterexample to an invalid shortcut. | No fabricated alternate method if none is authored. |
| I do not understand | Offer a concrete representation or prerequisite repair tied to the current objective. | Move to support; do not loop the same sentence. |
| Unsupported free-text question | Say the exact question is not covered; offer relevant reviewed choices or clarify the referent. | No invented explanation or correctness judgement. |
| Read/repeat/stop | Voice renders the same reviewed text and can be stopped; text remains the complete interaction path. | Voice availability never blocks progress. |

Validators: decimal/fraction/numeric expression parser with explicit unit handling and authored tolerance; constrained equation-step equivalence where implemented; syllogism set/region constraints under the declared convention; coordinate/feature checks for reflections; reviewed grammar transformations; passage evidence-span choices; sourced GA classification. Never use arbitrary `eval`, unsandboxed symbolic input or keyword presence as proof of understanding. Arbitrary written proofs and unrestricted essay grading remain unsupported until separately validated.

Concrete dialogue acceptance cases:

- Percentage: learner asks “Why divide by 1.2?” The teacher identifies the inverse-percentage step, shows original*1.2=current, explains undoing multiplication, and asks which amount is the original base. It must not simply repeat the final answer.
- Time & Work: learner adds 12+18. Teacher asks what “days” versus “jobs per day” measures, reconstructs rates and checks one rate before returning to the joint problem.
- Syllogism: learner connects two overlaps. Teacher requests a shared witness or shows two distinct witnesses; it does not claim a definite overlap from visual proximity.
- Mirror: learner chooses rotation. Teacher highlights two landmark positions and asks which coordinate should stay unchanged.
- English: learner selects “items” as subject. Teacher asks which noun the phrase “of items” modifies, then checks agreement on a fresh sentence.
- RC: learner gives an outside fact. Teacher asks for the passage sentence supporting it; absence leads to unsupported inference feedback.
- Polity: learner matches only “environment.” Teacher asks whether the actor is the State or citizen before suggesting a category.
- Physics: learner gives a speed value as velocity. Teacher asks for start/end position, then checks direction and units.

English is the initial reviewed content language unless a translated pack is explicitly authored. Tanglish prompt labels alone do not constitute Tanglish teaching. Translations need consistent terminology, source fidelity and their own review; browser speech support is optional and can fail gracefully.

Teacher acceptance suite: at least five reviewed scenarios per pilot topic covering explanation, derivation/justification, wrong-step repair, alternate example and unsupported follow-up; plus ambiguous referent, missing content, invalid numeric input, disconnected voice, stale revision, interrupted session and active-assessment denial. The release gate is all critical cases passing with zero unsupported factual assertions or protected-answer leaks in the benchmark. This is a finite benchmark claim, not proof of universal accuracy.

Optional V4 is a later separately evaluated adapter. It receives only entitled published evidence, returns attributable claims, cannot publish or award mastery, and must fall back to V3. No budget, provider choice or paid service is assumed here.

**6. Phased implementation and strict completion criteria**

| Phase | Deliverables and dependency | Exit criteria |
|---|---|---|
| A: contain and verify | P0-A/B boundary changes and cache handling; synthetic test environment; bounded production verification plan. Can proceed before pilot authoring. | All SEC and INT release-critical tests pass; deployed anonymous check safe; authorized synthetic learning and mock flows work; no changed question classifications or lost history. Networking failure leaves the live gate pending. |
| B: preserve and govern | P0-C/D revisions, immutable assessment contract, common publication validator and additive migration rehearsal. Content edits depend on this. | HIST/PUB/DB matrix passes; old IDs/responses/scores unchanged; active mock resumes; legacy uncertainty represented; dry-run/restart/rollback rehearsed in isolated PostgreSQL. |
| C: establish curriculum | Read restricted pilot packages; objective/prerequisite matrix; source registry; existing-archetype disposition ledger; reviewed public/private status. | Every pilot objective has scope, prerequisites, authored teaching plan and assessment evidence; all existing pilot IDs have an explained disposition; zero unexplained placeholder/unsupported blocks in released pilot content. |
| D: author and validate pilot | Eight teaching units, typed worked solutions, diagrams, checks and misconception repair; subject and teaching review. | Each objective is actually taught/modelled/checked; all numeric keys independently recomputed; all logical claims counterexample-tested where applicable; all visuals checked; passage claims supported; GA claims sourced; publication/access checks pass. |
| E: deliver Teacher V3 | Authenticated versioned lesson API, teacher controller, validators, assistance/exposure events and resume UI. | Teacher benchmark passes; AI-off and voice-off paths complete; assistance cannot count as independent; checkpoint resumes after refresh/network interruption without changing pinned content. |
| F: connect learning journey | Objective-based planner, evidence views and delayed retrieval; shared design system across the pilot flows. | Tasks launch the stated objective and mode; unavailable content is explicit; no unsupported readiness claim; keyboard/focus/contrast/reflow and device tests pass; due retrieval and failed-objective repair exercised end-to-end. |
| G: evaluate and expand | Consenting beginner study, alternate immediate/delayed forms, revision of failed units, batch expansion plan. | Preregistered learner criteria met and failures reported; no unresolved critical issue; expansion approved per objective coverage, never per bank-size target. |

Proposed learner-study acceptance: at least 12 consenting beginners overall, with at least six evaluated learner-unit journeys per topic (participants may study more than one unit). Record baseline familiarity using new synthetic-study data only. A provisional topic gate is at least five of six journeys achieving 80% on the immediate independent form and 70% on a seven-day alternate form, with no unresolved critical misconception on the objective rubric. Missing delayed follow-up is reported and cannot count as a pass. These are pilot thresholds to agree before testing, not statistically generalisable effectiveness claims. If a topic fails, revise that unit and re-evaluate; do not average away a failure with another subject's scores.

Accessibility target: WCAG 2.2 AA for the implemented flows, verified with automated checks plus keyboard/screen-reader/manual inspection. Test 320, 360, 390, 430, 768, 1024 and 1440 CSS-pixel widths, 200% zoom, long equations/text, image alternatives, slow/error states and landscape. A common semantic colour/type/spacing system should replace incremental CSS exceptions. [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/)

Each deployment must pin frontend/backend/content-release versions, pass required CI, preserve in-progress sessions, and have a tested compatible rollback. Measure cold and warm latency separately against the recorded baseline. No phase is complete merely because its first PR, a shape test or a record-count audit passes.

Risks and ownership: content SME/editor owns correctness and scope; learning designer owns scaffolding and misconception repair; backend owner owns authorization/versioning/evidence; frontend owner owns accessible interactions and state; QA owns independent regression and acceptance evidence. In a small team one person can hold several roles, but critical content/security changes still need a separate review. Principal risks are unknown source entitlements, unverifiable historical revisions, misleading difficulty labels, missing diagrams/passages, sparse independent-item coverage, migration concurrency and insufficient editorial capacity. Sequence work by these dependencies rather than estimating completion from the number of questions.

**7. Essential restricted evidence for the next audit stage**

No full question-bank export, credentials, learner rows, learner recordings with identity, signed URLs or unrestricted database connection is needed. The attached SQL should not be executed automatically. Use the existing private editorial environment; an operator can return the limited extracts or review summaries.

**Batch 1 — needed to make exact pilot dispositions**

1. Run Q5a/Q5b/Q5c for the eight stated topics only, adding the verified exam/stage scope to avoid same-slug collisions. Expected report totals are eight published lessons, 121 published blocks and 92 published archetypes. Reconcile differences rather than silently filtering them away. Include IDs, ordering, content fields, publication status and source lineage/review metadata where it exists. Remove identifying filenames and private paths; use stable source aliases.
2. Provide a mapping-only manifest for the pilot's verified questions: question ID or stable audit alias, topic, difficulty, `pattern_type`, matching archetype ID if any, source alias/type, verification/visibility, passage ID and visual-review flag. No stems, options or answers. This makes it possible to distinguish slug-format problems from semantic classification problems without exporting all questions.
3. Supply up to 48 restricted question records in the approved private review channel: two per topic per difficulty. Use the supplied Q5d as a starting shape, but select coverage deliberately rather than taking the two oldest IDs. Where possible choose one source-backed PYQ and one original/generated item with a different reasoning structure; if either class is unavailable, report that absence. Include some unmatched archetype cases and the shortest explanations, avoiding two numeric clones. Preserve a manifest of selection rationale so this purposive sample is not presented as a random estimate of bank-wide quality.
4. For these selected records only: full stem, complete ordered options, key, explanation, fast method, topic/difficulty/pattern, source alias/year/shift/page, question/option source IDs where needed for key reconciliation, review status and relevant source crop. Scrub candidate identity and chosen-response information. Answer keys must come from the source/editorial record, not a candidate's selected response.
5. RC items require their complete associated passages, including all necessary formatting. Aim to select the six RC items from no more than two coherent passages; if the corpus cannot support that, provide the actual linked passages and report the limitation. Do not force a three-level sample by assigning fictitious difficulty labels to a passage.
6. The six mirror/water-image items require the stem figure and every option image, plus clean source crops and key mapping. No signed URLs; use securely shared files or operator-reviewed visual evidence. Text-only samples cannot certify this topic. Include diagrams/graphs for any selected Physics item that needs them.

Only this bounded sample needs private question text. If text cannot leave the editorial environment, the reviewer can run the supplied rubric locally and return per-alias findings, with newly authored equivalents for joint discussion. Do not infer unobserved solutions from aggregates.

**Batch 2 — necessary integrity and source evidence, still bounded**

- Up to three sanitized repair cases if available: one duplicate-option repair, one answer/key correction and one taxonomy change. Provide before/after content for those items only and the change method/review status; no attempt rows. If no originals exist, explicitly report that history cannot be reconstructed.
- Schema-only migration/constraint/index information for the affected content/attempt tables, and the applied migration name/hash plus effective grants/RLS report. No SQL connection strings or user data.
- The bounded security verification output described in P0-A: deployed SHAs, status, headers, safe booleans and counts. No private response body or credentials. This is needed for live sign-off, not a prerequisite for writing the patch.
- A signed-in synthetic-account recording of one lesson/teacher/check/resume flow and one mock boundary test in staging, with no real learner data. Record mobile and desktop; do not request a production learner recording.
- For the selected PYQs, only the necessary question/answer-key pages initially, with exam/year/shift/source provenance. Full papers are optional later for frequency and syllabus-coverage analysis. A selected-page sample cannot justify corpus-wide “high frequency” labels.

**What this evidence still cannot establish:** full factual correctness of 10,043 records, representative bank-wide teaching quality, historical content as seen by every learner, licensing for public republication, or measured learner outcomes. Those require their respective editorial, provenance or evaluation work; they must remain explicit rather than being inferred from counts.

**8. Current delivery status**

This file is a planning artifact only. The supplied aggregate report was reviewed against the same repository commit, relevant security/assessment/cache contracts were reread, and authoritative sources were consulted for the illustrative Polity/Physics content and accessibility target. No optional restricted SQL, live private endpoint probe, migration, content edit or deployment was executed in this follow-up. Existing code and production data remain unchanged. The previous audit's limited generator/syntax checks are not new test results for the proposed design.
