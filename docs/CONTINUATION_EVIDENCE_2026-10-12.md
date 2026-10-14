# Phase A and teaching continuation — 12 October 2026

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
