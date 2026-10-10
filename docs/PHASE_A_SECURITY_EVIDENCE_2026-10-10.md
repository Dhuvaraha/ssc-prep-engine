# Phase A security and assessment integrity — review evidence

Date: 2026-10-10 (Asia/Calcutta). Branch: `feat/phase-a-security-integrity`.
Authoritative scope: [SSC teaching remediation specification](SSC_TEACHING_REMEDIATION_SPEC_2026-10-09.md), Phase A / P0-A and P0-B.

**Implementation is submitted for review; the production release gate is OPEN.** No production migration, grants, question exports, credential changes, merge, deployment, or LIVE-01 request was performed. Local tests and CI are not evidence that live production is safe. Phase B has not started.

## Implemented policy

- Registration creates an account only. Neither new nor existing accounts automatically receive private content access.
- A learner needs an active course grant for the selected exam. Every contributing private source must have explicit private-use approval and an active grant for that learner.
- Public question access still needs the selected course grant in Phase A, a public question classification, reviewed source bindings, and explicit source public-use approval. There is no new anonymous lesson preview.
- Licensing/publication approval and learner authorization are separate records. `official`, `verified`, `published`, client role flags, and source filenames grant nothing by themselves.
- Bindings cover questions, lessons (including their blocks), archetypes and flashcards. Missing, dangling, wrong-course or partially authorized dependencies deny access. Operators must review the complete contributing-source set; the migration does not infer it from `source_reference` strings.
- PostgreSQL learner row locks serialize assessment start/finalization, practice submission, assistance and operator grant changes. Protected request sessions apply SQLAlchemy loader criteria to candidate queries, joins, ranking subqueries, hydration and options **before LIMIT/serialization**. Raw SQL is prohibited in these request handlers; offline operator tools use separate sessions.
- All three lesson routes require authentication. Other protected surfaces include practice, revision, flashcards, bookmarks, analytics, diagnostics, backups, mock review and referenced private assets. Reviewer access remains an explicit separate operator allowlist; reviewers cannot use it to obtain answers during their own active assessment.
- Protected responses and denials use `private, no-store`; `Vary` retains existing values and includes Authorization. Public catalog responses disclose no private lesson inventory or source notes.

## Assessment behavior

All `in_progress` mock modes conservatively withhold new practice, teaching, solution review, revision, coaching and answer-bearing assets for that learner, across exams and IDs. They return `409 ASSESSMENT_IN_PROGRESS`. An expired clock does not unlock teaching until finalization commits. Generic navigation and assessment save/state/submit remain available.

Full mock start/resume returns question bodies only for the server's current section. Future/past sections cannot be unlocked using client state. Abandoned attempts cannot resume, save or submit. Identical concurrent submissions return the original result; abandoned attempts are not counted as submitted.

Practice requires a random server-issued delivery token bound to account, question and content digest. The token is the idempotency key. Unknown/foreign tokens, changed content and changed retry payloads reject without progress writes. Identical retries return the stored response. Browser retries retain the original payload, including elapsed time.

Every assistance action goes through a guarded server endpoint and records assistance before returning content. Client `used_hint=false` cannot override it. Solved-example/revision/review exposure, previous attempts and assessment exposure make later practice assisted. Exact normalized stem/option duplicates share exposure; this is not a semantic-equivalence classifier. The broad active-assessment lock also covers semantically related/aliased items without requiring such a classifier.

New mock deliveries retain a digest and answer key; changes to referenced question content prevent resuming/submitting changed material. This is a Phase A integrity guard, **not** Phase B immutable revision/history reconstruction. Old scores are never recomputed by this migration. Legacy active assessments must finish before cutover; no fabricated snapshots or automatic abandon/restart is performed.

Assessment images require an explicit reviewed answer-free crop record and matching file digest. Selection excludes unreviewed/external image references. The asset route additionally verifies course/source access, question reference, current assessment membership/section/time and bytes. Outside assessments, only authorized verified-question references may retrieve a private asset. Path traversal remains denied. Operators must review image coverage before rollout to avoid silently reducing an existing visual-question pool.

## Browser controls

Private packages have no persistent storage cache. Only known historical lesson/package keys are removed from localStorage/sessionStorage; unrelated preferences survive. Requests carry Authorization and `cache: no-store`.

Account changes, logout, expiry, cross-tab scope changes and page restoration invalidate RAM caches and remount sensitive views. Hidden/pagehide views are suspended; returning revalidates. Stale fetch/JSON/image completions are discarded; object URLs are revoked on cleanup. Starting a mock broadcasts invalidation to other tabs. These controls cannot erase content a learner already copied or memorized, or retroactively change a pre-release client that has not reloaded.

## Executed evidence

All records in these tests are original synthetic fixtures. Arithmetic keys are constructed as `i + 1`, option 1 is `i + 1`, and distractors differ. Multi-subject browser records are security/selection fixtures, not proposed curriculum. Fixture IDs, emails and passwords are synthetic; no production data is used.

| Check | Command/context | Observed result |
|---|---|---|
| Full backend regression | `python -m pytest -q --disable-warnings`, Python 3.12.3 / SQLite | **149 passed, 5 skipped**; skips are PostgreSQL-only cases |
| PostgreSQL security suite | `PHASE_A_TEST_DATABASE_URL` pointing to loopback-only `ssc_phase_a_test`; `python -m pytest tests/test_phase_a_security.py -q --disable-warnings` | **29 passed**, PostgreSQL 17.11 |
| Strengthened preservation assertion | Same PostgreSQL suite, `-k migration_manifest` | **1 passed, 28 deselected**; all legacy fixture table columns compared in memory |
| Python checks | `python -m pyflakes app tests`; `python -m compileall -q app` | Passed |
| Frontend build | `npm run build` | TypeScript and Vite production build passed |
| Frontend regression | `npm test`, Vitest 4.1.11 | **18 passed**, 3 files |
| Real browser/API flow | `npx playwright test`, headless Edge, local Vite/FastAPI, isolated synthetic SQLite | **3 passed** |
| Existing responsive smoke | `node scripts/phase0-browser-smoke.mjs`, local static server, Edge | **29 checks passed**, widths 320–1440 and anonymous mock redirect |
| Static server syntax | `node --check server.mjs` | Passed |
| Dependency audit | Install/audit after pinning Vitest 4.1.11 and Playwright 1.56.1 | **0 known npm vulnerabilities** at execution time |
| Diff whitespace | `git diff --check` | Passed |
| Deployed edge/Supabase/LIVE-01 | Not executed | **Pending approved rollout and bounded verification** |

The test-tool update fixes the audit findings in the prior Vitest dependency tree. Vitest workers explicitly disable Node's experimental host web-storage so jsdom owns browser storage. The PostgreSQL test fixture refuses non-loopback hosts and any database other than `ssc_phase_a_test`; each case creates and removes only its generated `phase_a_<uuid>` schema. Local portable binaries and logs are ignored by Git.

## SEC/INT traceability

| Gates | Automated evidence |
|---|---|
| SEC-01 | Anonymous lesson/package/list denials; invalid signed token without expiration rejected |
| SEC-02 | Explicitly ungranted account denied, uniform lesson missing/unavailable response, guessed IDs do not authorize |
| SEC-03/04 | Selection limited to bound sources; every contributing source required; grant revocation; public approval distinct from `public`/`official` flags; wrong-course binding rejected |
| SEC-05 | Referenced authorized asset succeeds; unreferenced/traversal denied; active assessment crop and digest enforced |
| SEC-06 | Unit tests for logout, switch, cross-tab, restore, expiry, delayed 401/JSON/image; real browser private page, actual logout/back, account B denial and delayed-response discard; no-store headers |
| SEC-07 | Public metadata omits private lesson inventory; package archetype source notes excluded |
| INT-01/02/03 | Broad server guard before practice/assistance/revision/flashcard/old review/lesson/backup delivery and exam switching; images protected; denied practice has no attempt writes |
| INT-04 | Only server-active section returned; forged future and stale previous section saves denied |
| INT-05 | Expiry remains locked; four concurrent practice retries create one attempt; four concurrent finalizations return one result; uncommitted finalization cannot release answers; rollback remains locked; concurrent starts yield one attempt |
| INT-06 | Abandon terminal for resume/save/submit; real-created mock exposure persists after abandon and later practice is assisted |
| INT-07 | Parameterized hint/explain/shortcut/compare/trap/example; server assistance wins over client false; solved-example exposure persists |
| INT-08 | Unknown token, changed content and conflicting retry rejected; identical retry stable |
| DB-01 (Phase A tables) | Repeatable additive DDL, RLS enabled, anon/authenticated effective table privileges absent, backend owner flow works |
| LIVE-01 | Sanitized verifier unit-tested; deployed execution pending |

The deployed cache-path portion of SEC-06 is not closed by the local browser tests. No test here proves the present Supabase backend role configuration or historical exposure duration. Existing production permission evidence remains a separate operator review input.

## Review and rollout requirements

See [operator transition runbook](PHASE_A_ENTITLEMENT_RUNBOOK.md). Required before any production release:

1. Review this code/specification and the actual operator manifest, complete source lineage and image coverage. No blanket existing-user grants.
2. Rehearse additive migration and approved grant application using restricted synthetic/staging data; review aggregate impact, including explicitly denied accounts and unmapped lessons.
3. Schedule transition, notify affected learners, finish pre-Phase-A active mocks, and approve production migration/grants/configuration. Existing history stays intact.
4. Approve deployment separately. Backend startup requires the reviewed manifest digest, secured Phase A tables and a non-default JWT secret; it never creates production grants.
5. Approve **one anonymous HTTPS GET to one operator-selected topic-package URL at the reviewed deployed SHA**, with a restricted private-ID manifest available only to the verifier. No enumeration, learner credentials, private body export or network archive. Run `python -m app.phase_a_live_check` under the runbook protocol. Review synthetic role tests through the deployed cache path separately.

Until these are satisfied, keep the PR unmerged and Phase A's release gate open. Do not start Phase B.

To prevent unreviewed automatic previews, this branch alone is disabled in Vercel Git configuration and the PR/commit use Render skip markers. No service topology, project, credentials, TracliQ configuration or production records are changed. See [Vercel branch deployment configuration](https://vercel.com/docs/project-configuration/git-configuration) and [Render preview skip behavior](https://render.com/docs/service-previews).

## Scope preserved and final local recheck

The eight-topic pilot is only a teaching-architecture validation step, never a permanent curriculum limit. The target remains comprehensive coverage of all 74 CGL Tier I topics and subtopics, followed by CGL Tier II and JE Telecom. Genuine distinct archetypes and meaningful PYQ variations replace fixed quotas. The existing 10,043-question bank, original IDs, learner history and source provenance remain preserved. No Phase B curriculum work is included here.

On 2026-10-10 the final local recheck again passed the full backend suite (149 passed, 5 PostgreSQL-only skips), PostgreSQL suite (29 passed), frontend unit suite (18 passed), Python static checks, frontend build, all 3 browser/API flows, and all 29 responsive checks. A bounded pattern scan of all 56 changed/new files found no private-key blocks, recognized secret-token prefixes or nonlocal credential-bearing PostgreSQL URLs; this is not a comprehensive secret-detection guarantee. Changed files contain synthetic fixture credentials only. Production gates remain open as described above.
