# Phase A and teaching continuation — 12 October 2026

## 22 October — frozen Phase B closure milestone

Continued from `d332d4a`, preserving the 19 pending files. The frozen acceptance
matrix and coordinated operator procedure are in [Phase B closure](PHASE_B_CLOSURE.md).
Implemented the remaining revision-aware practice analytics/learning-path views,
immutable attempt receipts, explicit current-study queue/bookmark labels and
provenance-only export. Legacy uncertainty is visible in Analytics and exported
migration-time captures retain their unknown-original flag.

Reviewed supplements now have immutable payloads and independent attestations,
exact question fingerprints and all declared contributor sources. They are pinned
at delivery, rendered in the existing practice UI after submission and reauthorized
on assistance/replay; changed contributor bindings fail closed. No legacy lesson
or option note was automatically approved, imported or published.

Active-mock transition is bounded, exam-scoped and guarded by coordinated admission
freeze, backend-role verification and database locks. Dry-run, restart, compatible
publication-off rollback, unchanged legacy checksums and eventual score are tested,
including two courses with equal durations but different marks. All instances must
be drained before migration; no pre-Phase-B binary rollback is supported.
Publication uses one structural/source/asset gate; direct verified import and
in-place repair are refused. Reviewed option reordering preserves stable IDs and
old deliveries. Unsupported text/asset replacements remain refused.

Final local validation: **299 backend passed, 8 PostgreSQL-only skipped; 80
PostgreSQL passed; 21 frontend passed; 4 real browser flows passed**; build,
pyflakes and compileall passed. Independent review found and resolved contributor
rebinding, verified-import bypass, export uncertainty and cross-course blueprint
findings, then reported no remaining scoped code blockers. Final commit CI is
recorded in PR #54 and the private closure checkpoint.

Learner-facing delivery: history-consistent analytics and reviewed versioned
practice supplements in the existing interface, with honest historical cautions.
Backend delivery: coordinated transition, additive immutable supplement governance,
history receipts and publication guards. This is Phase B engineering closure,
subject to final commit CI; it is not a full teaching journey or production release.
Do not extend Phase B with C–G work. Next is the existing PR #55/PYQ-based teaching
dependency. Phase A rights, exact access, actual deployed-role/final-manifest checks
and production cutover authorization remain separate. No production was changed.

## 22 October continuation — diagnostic and timing version pinning

Follow-on rollback safeguard: startup refuses capture-disabled operation when
delivery/publication evidence exists. PostgreSQL must prove history visibility
before an empty result is accepted; independent review caught and resolved the
RLS-hidden-history case. Local integration **31 passed, 2 PostgreSQL-only skips**;
pyflakes passed. A PostgreSQL regression exercises a SELECT-authorized role whose
rows are hidden by RLS. Final CI validates it. This is a startup guard, not a
coordinated rollback protocol: **mixed capture-enabled/disabled instances are
prohibited during rollout**. A revision-compatible rollback and coordinated
transition rehearsal remain required. No evidence is deleted or rewritten.

Diagnostic commit `a6f01fc` remote backend passed **285 tests, 7 skips**, PostgreSQL
passed **65 tests**, and frontend/build and separate Browser QA passed. Its combined
CI browser job was still running when this checkpoint was updated.

Continued from `34e8464`, preserving all six uncommitted files. Diagnostic profiles
now read authorized delivered revisions for keys, difficulty and topic identity.
New mock blueprints also capture the curriculum topic count so later curriculum
growth does not rewrite baseline coverage. Historical missing versions/counts are
explicitly marked unknown; the Analytics page displays the applicable caution.
Revoked historical sources deny access rather than silently changing the sample.

Mock timing, section transitions and active asset access now use the complete
captured timing blueprint. Inconsistent or partial pins fail closed. Legacy
attempts are not backfilled with invented historical timing. Regression tests
cover changed runtime timing, partial pins, legacy fallback and a submitted
diagnostic whose key, topic, difficulty and curriculum subsequently change.

Validation: full backend before the final curriculum/UI refinement: **285 passed,
7 PostgreSQL-only skips**. After that refinement, focused Phase B integration and
Phase A security: **58 passed, 7 skips**; pyflakes passed. Independent read-only
review found no blockers, including follow-up review of the curriculum count and
learner caution. Frontend: **21 tests passed**, TypeScript/Vite build passed
(esbuild required the permitted subprocess rerun). Remote CI is tracked in PR #54.

Learner-facing delivery: stable diagnostic evidence and honest legacy-history
cautions in the local gated implementation; no new lesson or production release.
Backend delivery: captured timing and diagnostic integration. Phase B still needs
transition/rollback validation, broader history adapters and versioned teaching
supplements. PR #55 and the first complete teach → diagnose → repair → retry →
revise journey remain next educational dependencies. Phase A source/image rights,
intended access, actual deployed-role compatibility and final release rehearsal
remain gates. No production writes, merges or deployments were performed.

## 16 October continuation — editorial UI and reviewer images

Resumed from `6dbda19` with nine uncommitted files; preceding practice/publication
changes were already committed. Preserved all current edits. Added the editorial
browser flow: candidate authoring instead of in-place changes under the capture
gate, complete before/after inspection, explicit independent checkboxes and review
reference, separate publication action and release-gate/conflict messages.

Reviewer images use a candidate-specific authenticated endpoint, not learner
asset permissions. It permits only captured before/after references with a known
consistent hash, enforces path containment and byte matching, and returns no-store.
Unknown or changed bytes fail closed. HTTP regression verifies reviewer access
without learner grants, removed current locators, unauthorized users, unrelated
assets and changed bytes. Independent follow-up review found no remaining blocker
in this fix. This does not approve image rights or broaden learner access.

The interrupted browser failure was a fixture-only login validation issue:
reserved `.invalid` emails were replaced with synthetic `example.com` addresses.
The isolated browser server explicitly migrates its temporary database and enables
the test gates; normal app defaults and production remain unchanged.

Validation: **4 real browser flows passed**, including independent editor review
and publication, account isolation, stale-response protection and learner practice/
mock use. Focused backend integration: **25 passed, 1 PostgreSQL-only skip**;
pyflakes passed. Frontend: **21 tests passed** and TypeScript/Vite build passed.
A test-only unsupported `exact` selector option was corrected to an anchored
accessible-name match. Final commit CI is tracked in PR #54.
Earlier publication commit `6dbda19` passed CI `38596264415` and browser QA
`38596265017`; no old tests or inventories were rerun to rebuild their evidence.

Learner-facing delivery: no new educational material or production release in this
milestone. Editor-facing delivery: usable independent-review flow and exact
candidate visuals. Backend delivery: narrowly authorized image access and verified
publication integration. Remaining Phase B gates include pinned timing/complete
transition, contributor-bound supplementary material and broader history routes.
PR #55 remains the additive Four-Option readiness/teaching acceptance dependency;
its draft is not a completed beginner-to-advanced journey. Finish one such reviewed
teach/repair/retry/retention journey before scaling to all 74 topics. The full A–G
roadmap and unresolved Phase A permissions/access/cutover gates remain unchanged.
No production data writes, migrations, merges or deployments were performed.

## 14 October continuation — gated reviewed publication

Practice milestone `b0c8b88` passed remote CI `38595493739` and browser QA
`38595493832`. The next implementation adds an immutable publication event and a
separate `phase_b_publication_enabled=false` gate. The authenticated endpoint
requires an independently reviewed, verified candidate and an unchanged parent.
It updates the current question projection, captures the new revision and records
publication in one transaction; rollback leaves both history and current content
unchanged. Existing IDs and delivered snapshots remain intact. Option/image
correction publication is explicitly unsupported rather than implicitly trusted.

Publication refuses unpinned active mocks and live practice deliveries. Practice,
mock creation, candidate creation and publication share question locking and
refresh loaded state after locking. Independent review found opposite-order
practice batches could deadlock; all selected questions now lock in sorted order
before issuing tokens. The concurrent two-editor test produces exactly one
publication and one stale conflict. Opposite-order learner batches both complete.
Follow-up independent review found no remaining blocker in this scoped milestone.

Validation: focused integration **24 passed, 1 PostgreSQL-only skip**; full backend
before the final batch regression **279 passed, 7 skipped**; pyflakes passed.
Final PostgreSQL and full-suite CI results will be recorded against the commit.
The expanded evidence schema needs explicit migration even in staging; startup
verification rejects a prior schema missing publication guards. Production is
untouched and both rollout flags remain disabled.

Learner-facing deliverable remains revision-safe practice/mock feedback, not new
teaching content. Still unfinished: editorial browser flow, pinned timing/complete
transition validation, contributor-bound supplements and broader history routes.
Phase B is not declared complete; Phase A release and full A–G gates remain.

## 14 October continuation — practice revision consumers

Mock milestone `5247ce1` passed remote CI run `38533148170`: **273 backend
tests, 7 skips; 53 PostgreSQL tests**, frontend and Phase A browser checks.
Browser QA `38533148093` also passed.

Practice submissions, assistance and idempotent result replay now use authorized
captured answers/explanations. Source/course/owner checks run before replay;
expiry and single-attempt behavior remain intact. Learner-facing development
behavior: later question corrections do not change a delivered practice answer.

Independent review found cached supplementary coaching could outlive contributor
permissions. Pinned responses now omit unversioned coaching/option insights,
including read-only filtering of older cached payloads. Saved results are not
rewritten. Original explanations/fast methods remain. Contributor-bound supplement
delivery is still a required teaching release gate, not a completed Explorer.
Follow-up independent review found no remaining blocker in this milestone.
Practice/security/integration regressions: **52 passed, 7 PostgreSQL-only skips**.

PR #55 (`6bc490d`) is stacked on #54 and adds five new/additive files: offline
Four-Option readiness, original unpublished polity draft, tests and acceptance
criteria in the existing master roadmap. Preserve its branch rather than copying
or replacing it. Its structural tests do not certify facts or a working lesson.
First complete one reviewed beginner-to-advanced teach/repair/retry/retention
journey; full 74-topic expansion remains required afterward. No production changes.

## 14 October continuation — mock revision consumers

Continues `2d41052`; no completed work or private audits repeated.

Learner-facing development deliverable: gated mock resume, submission and review
now use captured stems/options/keys/explanations and captured positive/negative
marks after subsequent question or exam edits. Old attempts without a capture
show a clear original-version-unknown notice; saved scores are not rewritten.
This is implemented in the existing mock flow, not deployed to learners yet.

Backend: detached snapshot views cannot mutate legacy rows. Both current access
and every historical source dependency are checked, including course and owner.
Independent review caught the active image endpoint still relying on current
references; it now uses authorized pinned references and current-section windows,
and retains immutable byte-hash checks. Regression proves old images survive a
locator correction, changed bytes fail, and historical source revocation after
current rebinding denies direct asset access. Follow-up review found no blocker.

Validation: focused integration **17 passed, 1 PostgreSQL-only skip**; full backend
before the final image regression **272 passed, 7 skipped**. Pyflakes passed.
Frontend TypeScript/build passed (esbuild required normal sandbox escalation).
Final remote PostgreSQL/full/backend/browser results belong to this milestone's
commit and will be recorded in PR #54.

Remaining Phase B: practice consumers, publication/activation, pinned timing and
complete active-mock transition, editorial UI and broader history integration.
No Phase B completion claim. Capture remains off; no production writes, migration,
merge or deployment. Phase A operator/rights/coverage/role gates below persist.
Phases C–G, eight full teaching pilots and all 74 topics remain active; this
milestone does not claim new lessons, calibrated mocks or curriculum completion.

## 14 October continuation — gated application capture

Preserved and completed the twelve uncommitted files after `4c46f43` on draft
PR #54. Added explicit PostgreSQL/SQLite evidence migration, immutable delivery
snapshots and answer-key digests, practice/mock delivery pins with source bindings
and blueprint evidence, and authenticated unpublished editorial candidates with
independent review and inspectable before/after payloads. Capture defaults off.
Existing question IDs, attempts and scores are not rewritten. Omitted fields in
the legacy review endpoint are now preserved.

Database guards reject evidence updates/deletes/replacement and PostgreSQL
truncate; startup checks schema, trigger shape, backend access, RLS and denied
client privileges. Migration requires the existing legacy/Phase A schema and is
never invoked automatically. In-place repair is rejected when capture is enabled.
Review requires strict boolean attestations, a distinct reviewer and an immutable
decision; stale candidates and duplicate decisions return conflicts.

Independent review found and verified fixes for mutable asset hashes and missing
candidate inspection. The migration also freezes the existing asset registry:
this persists when capture is disabled. Changed bytes require a new asset locator
and review record, retaining old bytes. The gated asset gateway checks served
bytes against the immutable hash. Metadata binding does not establish rights.

Validation: full backend **269 passed, 7 skipped**; focused SQLite integration
**13 passed, 1 PostgreSQL-only skip**; PostgreSQL integration **14 passed** before
the final missing-schema guard (subsequently exercised by the SQLite suite).
Pyflakes passed. Final independent read-only review found no blockers in this
limited capture/editorial scope. Pushed implementation commit `3ff610b` to PR #54.
Remote [CI run 38528297676](https://github.com/Dhuvaraha/ssc-prep-engine/actions/runs/38528297676)
passed: **269 backend tests, 7 skips; 49 PostgreSQL tests** (including all 14
new integration tests on the final code), frontend build/tests and Phase A browser
flows. [Browser QA run 38528297854](https://github.com/Dhuvaraha/ssc-prep-engine/actions/runs/38528297854)
also passed. These supersede the local pre-final PostgreSQL qualification above.

Exact remaining Phase B work: publication/activation, transactional transition
for active mocks, scoring and authorized history consumers using pinned versions,
and learner/editor UI integration. Current pins are capture evidence, not a claim
that existing grading or history has switched to revisions. No phase is complete.
Continue these consumers before activation; preserve unknown historical versions.

Phase A release gates remain: reviewed source/contributor and image permissions,
intended account/course/source coverage, deployed backend-role verification, and
final reviewed-manifest HTTP/access/rollback validation. Reuse the existing
96-group proposal, 704 asset mappings and prior rehearsal; none was regenerated.
No production migration, data write, merge or deployment occurred. The existing
A–G roadmap and complete curriculum/teaching scope remain authoritative.

## 13 October continuation

The working tree was clean at `b78fc20`; the previously reported six local edits
had already been committed, not lost. The interrupted push succeeded through the
normal approval path. [Draft PR #54](https://github.com/Dhuvaraha/ssc-prep-engine/pull/54)
targets PR #53's recovery branch and keeps Phase B isolated from `main`.

Continued Phase B with a lossless legacy snapshot adapter and a separate immutable
capture table. It preserves every mapped question/option scalar, including nulls,
original option IDs/order, source fields, solution fields and asset references.
It rejects unloaded columns/relationships, partial option sets and cross-question
options rather than issuing hidden database reads. Independent review found that
loaded relationships can still be filtered; capture now requires independently
extracted expected option IDs from the same authorized database snapshot and checks
them explicitly. Inline asset bytes are hashed;
external image bytes remain explicitly unverified. Captures are idempotent evidence,
not publication-valid revisions or reconstructed historical delivery versions.
Existing learner rows, scores and production data are untouched.

Snapshot/ledger regression suite: **42 passed**; pyflakes passed. Initial fixture
failures exposed unloaded ORM attributes; fixtures now explicitly load their rows
and relation, matching the adapter's deliberate no-implicit-query contract.

For `b78fc20`, remote backend, frontend and browser jobs passed. PostgreSQL failed
at container startup because fixed runner port 55432 was occupied; no PostgreSQL
test ran in that failed job. CI now uses the service's allocated host port for both
role setup and tests, following GitHub's documented service-container mapping.
Final-commit CI status is recorded in PR #54. Production release gates below remain
unchanged. The completed PDF inventory and 96-group rehearsal were not repeated.

Phase B remains in progress: next implement the PostgreSQL evidence schema and
restricted permissions, then authenticated editorial/delivery adapters, active-mock
transition and pinned blueprint/history integration. The local ledger and capture
adapter alone do not satisfy these production acceptance gates.

---

## Subsequent isolated Phase B milestone

Continues `6d90b28` on `feat/phase-b-immutable-history`; the six existing local
edits were preserved. PR #53 remains the blocked Phase A parent. No production
write, migration, merge or deployment occurred.

Implemented a local SQLite editorial ledger with immutable question snapshots,
stable option identities, asset-aware answer-key versions, independent-review
evidence, append-only publication history, optimistic publication preconditions
and version-pinned history. Corrections preserve omitted fields and old pins/results.
Historical pins explicitly retain unknown original versions rather than borrowing
a present-day snapshot. This is an isolated development foundation, not a migrated
production database, authenticated review API or live assessment adapter.

Independent review's three findings are fixed:

- Primary-key replacement, unique-index replacement, UPDATE/DELETE and rowid
  replacement paths cannot replace ledger evidence. New tables use WITHOUT ROWID;
  older incompatible schemas are rejected without rewriting their evidence.
- Changed asset bytes change the key-version digest even if asset identity is reused.
- Pin validation/insertion and editorial publication use immediate transactions.
  Two concurrent editors produce one publication and one stale-precondition failure.

Focused validation: **67 passed** across ledger, coverage, existing proposal and
mock-quality tests. Pyflakes/compileall passed for the
ledger/coverage/rehearsal changes. Independent follow-up review confirmed the three
blockers resolved; old-schema rejection addresses its compatibility observation.
Earlier successful unrelated tests were not rerun locally; remote CI is recorded
in the linked PR after push.

The interrupted 96-group rehearsal completed. The subsequent
[96-group plus image-map rehearsal](evidence/entitlement_rehearsal_96_groups_assets_2026-10-12.json)
reuses the exact existing proposal, checks all 704 image-reference mappings and
their source links, and preserves all synthetic legacy columns. Repeat migration,
dry-run rollback, ORM coverage/denial and revocation rollback passed for 10,043
questions, 40,172 options, 1,881 resources and 1,007 blocks. Proposal and mapping
digests identify the inputs. Follow-up review added byte-bound asset cache validation;
[offline verification](evidence/asset_mapping_byte_validation_2026-10-12.json) passed
for the same 704 mappings after the database rehearsal, without repeating that
successful database run. Changed asset bytes now invalidate cached screening.
The current private mapping is `coverage-and-asset-map-byte-bound-2026-10-12.json`.
This still uses hypothetical synthetic permissions:
it is not final production validation, an HTTP/image-delivery test or rights approval.

Private coverage: 104 of 704 data-URI SVG groups pass the deliberately conservative
static screen; the other 600 need inspection and are not automatically classified
as malicious. Zero visual or rights approvals were inferred. All 74 lessons, 806
archetypes and 1,001 flashcards still lack complete contributor evidence in the
cached inventory. Topic/difficulty pools and observed course candidates are mapped;
the draft has zero active grants. The proposal was not regenerated.

Render service identity was reconfirmed in My Workspace, on `main`. Available
database session metadata does not attribute a role to the deployed backend;
compatibility remains unverified rather than inferred from the management role.

Continued mock-quality engineering with an offline evaluator that requires reviewed
section counts and family-variation targets, reasoning and distractor evidence,
answer/source consistency and visual checks. Difficulty labels cannot pass this
screen. Even a successful analytic screen does not claim empirical calibration or
exam equivalence. No live selector was silently changed.

Exact next gates: complete contributor and visual evidence; establish intended
account/source permissions; obtain actual backend-role verification; rehearse the
reviewed production manifest and HTTP/assets. Phase B next requires PostgreSQL
schema/permission migration, full legacy-field snapshot adapters and authenticated
review/delivery integration, active-mock transition, blueprint/history pinning and
rollback rehearsal. Eight original questions remain drafts, not complete lessons;
their learner integration and accessibility/teaching evaluation remain required.
All 74 Tier I topics, CGL Tier II, JE Telecom and Phases B–G remain in scope.

---

Continues PR #53, including #51/#52. No production writes, merge or deployment.
The existing master and teaching roadmaps remain authoritative.

## Implemented

- Read-only inventory SQL and offline proposal generator preserve exact question
  IDs and recorded source references. Draft proposals cannot execute; unresolved
  assets, incomplete contributors and unreviewed courses also fail import.
- Private proposal covers 10,043 question IDs in 96 proposed source groups. Exact
  repository generation comparisons matched stem, explanation, fast method, key,
  options and images for 1,200 Quant and 1,200 Reasoning records. These are
  repository-generated content matches, not a historical ownership certificate,
  authenticated PYQ designation or quality approval. Remaining 7,643 records
  retain uncertainty. No blanket grants or inferred lesson bindings were created.
- Loopback-only staging runner rejects connection query overrides and pins the
  isolated database. [Rehearsal](evidence/entitlement_rehearsal_reviewed_2026-10-12.json)
  preserved every legacy column for 10,043 synthetic questions, 40,172 options,
  1,881 resources, 1,007 blocks and representative attempts/mock history. Repeated
  migration, dry-run rollback, scoped ORM coverage/denial and revocation rollback
  passed. It tested the 95-group unsplit inventory, hypothetical synthetic rights,
  one learner/course and one denied account. It did not test HTTP, production
  credentials, asset delivery, actual permissions or the final 96-group manifest.
- PDF audits can reuse cached extraction by SHA-256, including renamed copies;
  changed bytes invalidate cache. All PDFs, excerpts, images, internal IDs and
  proposed grants stay in ignored `backend/data/private/phase-a-review/`.

## Actual educational findings

Targeted review of the 2024 reference's Quant pages 19–28, with visual checks of
pages 22 and 26, covered eight anchors: weighted interest, degenerate geometry,
successive discount comparison, switched pipe rates, unequal-size graph averages,
cone volume-to-surface conversion, algebraic feasibility and circular relative
speed. These are purposive examples, not measured topic frequencies or timings.
The 2025 paper received only preliminary page inspection, not a completed audit.

The algebra anchor on page 26 has inconsistent real-number givens: sum 18 and
sum of squares 36 violate the minimum 108. Its printed answer must not establish
a calibration target. Reference keys require validation, even when an algebraic
identity mechanically yields an option. Private anchors retain page/question IDs;
no third-party stems, options or diagrams are published here.

The repository's repeated procedural seed templates and cyclic difficulty labels
do not establish reasoning depth. Fixed full-mock difficulty quotas remain
independent of learner level; numeric labels alone cannot repair the quality gap.

`backend/data/original_reasoning_depth_pilot.json` contains eight independently
authored drafts across arithmetic, algebra, geometry, logic, coding and data
interpretation. Each includes prerequisite foundations, linked reasoning,
distractor diagnosis, beginner scaffolding, shortcut limitations and an independent
mastery prompt. Arithmetic/logic checks and independent review validated all eight
answers. They are not imported into production, authenticated PYQs, complete
eight-topic lessons or empirically calibrated mocks. Timing and learner testing
remain pending; daily learning pace is unchanged.

## Validation and exact continuation

Backend: 191 passed, six PostgreSQL-only skips; pyflakes and compileall passed.
Independent review found no blocking defects; the tangent boundary wording was
clarified. Earlier frontend/build/browser results remain in EXECUTION_TRACKER.

Private current proposal: `proposed-manifest-authorship-2026-10-12.json`.
Private inventory/topology and authorship evidence are dated 2026-10-12 alongside
it. Reuse them; do not repeat the inventory or ask for an approved manifest.

Next release work: complete contributor and image mappings; establish intended
learner/course/source access; verify deployed DB-role compatibility; rehearse the
reviewed final manifest and production-sized access pools; consolidate genuinely
unresolved operator decisions and cutover approval. Original authoring needs no
publisher approval. Uncertain copied content still needs a valid rights basis.
Phase A remains blocked from production until those conditions are satisfied.
Continue immutable history (B), complete curriculum/subtopics (C), complete pilot
lessons (D) and subsequent E–G acceptance; no phase is declared complete here.
