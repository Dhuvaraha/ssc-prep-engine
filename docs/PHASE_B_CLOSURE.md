# Phase B engineering closure

Scope is frozen to P0-C/P0-D and HIST-01–03, PUB-01–03, DB-01 in
[the approved teaching specification](SSC_TEACHING_REMEDIATION_SPEC_2026-10-09.md).
This closes historical integrity and its existing integration obligations. It
does not certify teaching quality, all 74 topics, or Phase A production authority.

Local closure validation: **299 backend passed, 8 PostgreSQL-only skips; 80
PostgreSQL passed; 21 frontend passed; 4 real browser flows passed**. Build,
pyflakes and compileall passed. Independent review found no remaining scoped
code blockers after fixes for contributor rebinding, import bypass, export
uncertainty and cross-course transition rules. The runbook sequencing finding
was also corrected. Final commit CI is the remaining engineering verification;
its definitive result is recorded against PR #54, without reopening scope.

## Acceptance evidence

| Criterion | Implemented engineering behavior |
|---|---|
| HIST-01 | Immutable question/option identities, answer-key versions, source dependencies and scoring/timing blueprints. Practice, mock review, diagnostic baseline and practice analytics use delivered revisions. New practice attempts have immutable receipts. Reviewed option reordering preserves IDs and old deliveries; current keys/taxonomy/marks cannot regrade saved results. |
| HIST-02 | Legacy results are not reconstructed or rescored. Missing evidence remains unknown. Migration-time captures remain explicitly unknown in review, diagnostics and metadata-only export. Revision queues/bookmarks are labelled current study views. |
| HIST-03 | Coordinated API admission freeze; bounded, transactional active-mock capture under PostgreSQL table locks; unchanged legacy checksums; dry-run rollback, idempotent restart, saved-answer/deadline preservation and subsequent submission. Compatible rollback keeps revision readers/capture enabled and publication disabled. |
| PUB-01 | Reviewed publication uses the common structural/source/asset validator. Direct verified imports, in-place reviewer mutations and automatic repairs are refused under Phase B; imports must stage review-required content. |
| PUB-02 | Duplicate/numerically equivalent options, missing solutions, unresolved rights and unreviewed/changed assets cannot publish. Rejected candidates do not replace current content or alter history. Unsupported option-text/asset replacements are explicitly refused. |
| PUB-03 | Independent immutable review evidence, parent preconditions, ordered delivery/publication locks, atomic publication and concurrent-editor regression coverage. |
| DB-01 | Additive, restartable PostgreSQL/SQLite schema with immutable evidence guards and backend-only privileges. New supplement tables use the same protections. Previous-schema upgrade preserves delivery evidence. Actual production role verification remains a Phase A cutover gate. |
| Supplement integration | Explicit teaching payloads bind to a complete question fingerprint and declared sources plus all lesson/archetype/flashcard contributors. Separate independent review is required. Delivery pins one immutable reviewed payload; assistance, submission and replay reauthorize its sources and contributor bindings. Changed dependencies fail closed. Existing learner UI renders the reviewed method; no answers/supplements appear in assessment delivery. |

The automated tests are synthetic. They establish these engineering behaviors,
not factual certification of legacy content or production permissions.
Final commit CI and independent-review results are recorded in PR #54 and the
continuation checkpoint. No new curriculum or learner pacing changes are included.

## Coordinated transition procedure

This procedure is reviewable engineering, **not production authorization**.

1. Resolve the separate Phase A cutover gates. Retain the exact approved manifests,
   content/image rights evidence, account/course grants and existing inventory.
   Do not regenerate them or infer permissions from labels.
2. Save the current release artifact/configuration and reviewed historical
   blueprints. The rollback artifact must contain the Phase B revision readers,
   unknown-history handling and additive schema support in this closure commit.
   A pre-Phase-B binary is not a supported rollback target.
3. Drain and stop **all** application instances and offline content writers;
   keep ingress closed. Never overlap enabled and disabled capture instances;
   the flag does not magically stop an older binary.
4. Explicitly run `app.phase_b_migration.migrate(engine)` and `verify(engine)` in
   the approved operator environment. These are not startup migrations. Preserve
   all additive tables during any rollback. Do not change learner grants here.
   Only after migration/verification, start the compatible artifact with
   `PHASE_B_TRANSITION_MODE=true`, `PHASE_B_CAPTURE_ENABLED=true`,
   `PHASE_B_PUBLICATION_ENABLED=false` and startup content repair disabled.
   Verify every routed instance returns 503/no-store for API reads and writes.
   Health remains available. Starting the capture-enabled artifact before its
   additive migration is intentionally rejected by startup verification.
5. In a fresh unscoped backend session, call
   `transition_active_mocks(db, reviewed_blueprints, exam_id=reviewed_exam_id, admission_frozen=True, limit=100)`
   from `app.services.phase_b_transition`. First roll back the transaction and
   inspect its count/checksum report. Repeat with the same reviewed inputs and
   explicitly commit. Repeat bounded batches until no new attempts are captured.
   Each batch is explicitly scoped to one exam. Other courses are untouched;
   repeat with each course's separately reviewed blueprint, never shared rules
   inferred from equal mode names or durations. Each mode's reviewed blueprint
   must provide its original `duration_minutes`,
   `positive_marks`, `negative_marks`, `section_order` and `full_section_seconds`.
   Do not substitute today's marks/timing for unreviewed historical settings.
6. The transition preserves started-at/deadline, saved answers, timestamps, IDs,
   scores and statuses. A disagreement with existing assessment evidence, missing
   source bindings or partial pins stops the transaction. Resolve that exact case
   through explicit adjudication; never overwrite the saved response or claim an
   authenticated original version. Missing historical curriculum counts stay
   unknown rather than being backfilled.
7. Restart the compatible artifact, verify the guards, and test approved/denied
   accounts, active resume/submit, old review, diagnostics, analytics, export,
   image delivery and cached supplement revocation. Release admission only after
   those checks. Enable publication separately after its acceptance checks.

### Compatible rollback

Freeze/drain admission again; disable publication and retain capture/readers.
Restore only a reader-compatible artifact/configuration, verify schema guards,
then resume. Do not drop evidence tables, restore a stale database, disable
capture after history exists, or rewrite scores. The automated rehearsal proves
data/configuration compatibility and restart behavior; it is not a claim that
a deployed production binary rollback has occurred. Deployment smoke and the
actual role/manifest checks remain part of the authorized cutover.

## Separate external release gates

- Phase A source/image rights and complete contributor bindings; independently
  authored original material needs no third-party publisher approval.
- Operator-approved exact learner/course/source entitlements and preserved access.
- Effective deployed backend role and final reviewed-manifest HTTP/asset/pool
  coverage and rollback verification in the approved deployment environment.
- Authorization of the coordinated production cutover and live verification.

These gates do not reopen Phase B engineering or block independent PYQ-based
teaching/Four-Option work. After the scoped engineering suite and review pass,
continue the existing PR #55 dependency and teaching roadmap. No additional
Phase C–G feature is a condition of this engineering closure.
