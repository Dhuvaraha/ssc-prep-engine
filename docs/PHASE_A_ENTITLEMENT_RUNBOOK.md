# Phase A — operator-controlled transition

**This is a reviewable procedure, not authorization to run it in production.** The user selected explicit operator-maintained account/course/source grants. Nothing below grants existing accounts automatically or converts private questions to public.

## Records and access decisions

`content_sources` records course ownership and separately approved private/public use. Its review reference must point to the operator's rights evidence. `course_grants` and `source_grants` decide an individual learner's authorization. `content_bindings` records every contributing source for a question, lesson (and blocks), archetype or flashcard. Unmapped material stays unavailable.

The administrator workflow is an offline module, not a web endpoint. Learner JWT roles or registration cannot call it. The operator uses their existing approved database environment; do not send credentials to an auditor or put them in a manifest. Keep real manifests outside this public repository and outside PR attachments. Report only aggregate impact and the reviewed manifest digest.

## Rehearsal before production approval

1. Review original synthetic fixtures in `backend/tests/test_phase_a_security.py` and `backend/tests/phase_a_browser_app.py`. Run the SQLite, PostgreSQL and browser suites in the evidence report. The PostgreSQL suite requires loopback host and database `ssc_phase_a_test` and never accepts a Supabase URL.
2. Prepare an operator-reviewed manifest. Resolve source lineage from rights evidence, not inferred filename matching. Review every lesson's contributing sources, including copied examples and blocks; bind all contributors. Confirm question subject/topic/exam consistency. Source grants do not imply permission to publish source material.
3. Review the intended allowed/denied account set within the operator environment. Do not export learner data. Add courses and sources only for explicitly permitted users. Test one approved and one unapproved synthetic user per source/course combination, including a mixed-source lesson and a revoked grant.
4. Review approved answer-free assessment images. Unknown/full-page/external images are excluded from new assessment selection until an explicit crop review and matching byte digest exist. Verify mini/topic/sectional/full/diagnostic pool sufficiency before cutover; do not silently remove visual-question coverage in a rollout.
5. Compare legacy IDs, responses, timestamps, progress and scores before/after rehearsal. The automated fixture test compares all legacy table columns in memory. Keep any real-environment comparison within that environment; export only equality booleans/counts.

## Explicit commands (operator executes only after relevant approval)

Use the backend working directory and set `PHASE_A_ADMIN_DATABASE_URL` in the operator's approved environment. There is intentionally no fallback to application `DATABASE_URL` for these CLI commands.

```text
python -m app.phase_a_migration
python -m app.phase_a_admin <restricted-manifest.json>
python -m app.phase_a_admin <restricted-manifest.json> --apply-reviewed-sha <exact-dry-run-digest>
```

The migration installs only additive Phase A tables. On PostgreSQL it enables RLS and revokes PUBLIC/anon/authenticated access on those tables and associated sequences. It does not alter old question/account/history records and creates no grants. It is restartable. The existing backend role must be the appropriately approved owner/service role; custom FastAPI integer IDs are not Supabase `auth.uid()`.

The administrator command defaults to a rolled-back savepoint dry run. Its aggregate report includes active assessments, active grants, accounts without grants and unmapped resource counts. Applying requires the exact reviewed SHA-256 manifest digest and records operator/reason/digest in `entitlement_audit`. Changes use the same user lock order as learner requests. A changed manifest requires new review. Never paste a credential-bearing URL into a CLI argument or output log.

Illustrative **synthetic** manifest structure (IDs below are fixture IDs, never production instructions):

```json
{
  "operator": "synthetic-reviewer",
  "reason": "approved original fixture rehearsal",
  "sources": [
    {"id": "synthetic-original", "exam_id": 1, "rights_basis": "original",
     "private_use_approved": true, "public_use_approved": false,
     "approval_reference": "restricted-review-ticket"}
  ],
  "bindings": [
    {"resource_kind": "question", "resource_id": 1, "source_id": "synthetic-original"},
    {"resource_kind": "lesson", "resource_id": 1, "source_id": "synthetic-original"}
  ],
  "courses": [{"user_id": 1, "exam_id": 1, "active": true}],
  "grants": [{"user_id": 1, "source_id": "synthetic-original", "active": true}],
  "assessment_assets": []
}
```

Permitted rights bases are `original`, `licensed` and `private_permission`; private permission cannot approve public publication. These values record a reviewed decision, not proof of ownership. `assessment_assets` entries require `asset_key`, `content_sha256` and `review_reference`; the file must be inside the configured private asset root and match the reviewed hash. A source may contribute to multiple resources; every contributing source must be represented. Bindings are additive, not a destructive replacement of provenance.

To revoke access, submit a newly reviewed manifest with `active:false` for the exact course/source grant. To withdraw a source permission, submit its source record with the permission false and a new reason. Revocation can interrupt access to an existing assessment; coordinate normal changes outside active sessions. An urgent rights/security revocation intentionally fails closed and needs support handling, not automatic score recomputation.

## Controlled cutover

- Review aggregate impact and permitted users before rollout. Unapproved users retain their accounts/history but will not gain private lessons. Communicate the change and the operator access-request route; the lesson UI explicitly says access is unavailable and progress is retained.
- Finish existing pre-Phase-A active assessments on the old release before the transition window. Startup blocks legacy active mocks lacking delivery bindings. Do not fabricate a starting snapshot, reset deadlines or auto-abandon records to satisfy the gate.
- After approval, apply migration and the reviewed manifest, then configure `PHASE_A_REVIEWED_MANIFEST_SHA` to that applied digest and `RELEASE_SHA` to the actual deployment commit. Check the existing JWT secret is non-default and at least 32 characters without disclosing it. This change does not rotate it.
- Deploy backend and frontend only under the user's separate release approval. Old clients must reload because practice submission now requires a delivery token. Old frontend submissions reject without progress writes; retry on a fresh client, not a legacy request.
- Verify an approved synthetic learner can open mapped lessons, obtain scoped questions/assets and complete practice and mocks. Verify an ungranted synthetic account receives denial. Confirm no private persistent cache and no shared authenticated edge cache.
- The feature branch disables its own Vercel automatic deployments. Render previews are skipped by the PR title. Leave these guards in place during review; enabling any preview/release requires approval and synthetic/staging data configuration first.

## LIVE-01 approval boundary

Required inputs: exact operator-selected HTTPS topic-package URL, expected deployed commit SHA, and a restricted JSON array of private question IDs for that one topic. No question texts, learner records, credentials or full question exports are needed.

After explicit authorization for that exact request:

```text
python -m app.phase_a_live_check --url <exact-https-package-url> --expected-sha <deployed-sha> --private-id-manifest <restricted-local-json> --operator-approved
```

The verifier makes at most one request, does not follow redirects, bounds the body to 1 MiB, analyzes it in memory, and emits only status, cache-control, counts and booleans. It never prints bodies, IDs, source locators, answer text or body hashes. A private-ID match confirms exposure and ends the probe. A denial proves only that bounded request's behavior. A network error, unknown SHA or oversized/unparseable body leaves verification unresolved. Do not run the old repeated anonymous private-package latency probe; it has been removed from the production smoke workflow.

## Rollback and stop conditions

Do not drop additive tables or restore a stale database over learner activity. Preserve new deliveries, exposures, audit events and legacy history. Code rollback must be reviewed: reverting to the pre-Phase-A release reopens known authorization/integrity gaps and is not a safe automatic fallback. If the new startup gate fails, investigate the manifest/schema/active-assessment condition before routing traffic; do not weaken default-deny or grant every account.

Stop rollout if any authorized synthetic user loses an intended mapped lesson, a pool loses required visual coverage, any legacy equality check fails, a direct-client role can access Phase A tables, any active assessment can obtain answers, or any release-critical test fails. Keep the live gate open until bounded verification and deployed synthetic-role/cache checks have been reviewed. Phase B remains out of scope.
