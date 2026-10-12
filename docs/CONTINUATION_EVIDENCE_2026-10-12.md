# Phase A and teaching continuation — 12 October 2026

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
