# SSC recovery execution tracker

Authoritative execution status, updated 16 October 2026 IST. Requirements remain in
[master phases 0–9](MASTER_EXECUTION_PHASES_0_TO_9.md) and
[teaching phases A–G](SSC_TEACHING_REMEDIATION_SPEC_2026-10-09.md).
Historical evidence documents are checkpoints, not competing task queues.
No phase is complete, and no launch or exam-equivalence claim is justified.

Latest isolated milestone: PR #54 includes revision-based practice/mock consumers,
gated atomic publication and an editorial browser flow with candidate-specific
image access. Local validation: 25 integration tests passed, one PostgreSQL skip;
21 frontend tests and four real browser flows passed. Capture/publication remain
disabled outside synthetic tests. Production is untouched.
See the [16 October checkpoint](CONTINUATION_EVIDENCE_2026-10-12.md) for exact scope,
asset immutability implications, remaining integration and unchanged release gates.

## Reconciled state

- Clean starting checkout: `bb0d903`; recovered integrated PR #53 head `6500e719`.
  PR #51 head `80840ce6` and #52 head `be4299d8` remain draft/unmerged; their
  current CI and responsive workflows are successful. #53 already contains both.
- Render **My Workspace** `tea-db1r3ccs728c73dpvtu0`, SSC API
  `srv-db1s0dcs728c73dt65qg`: latest live deployment `dep-db3pbhu0tbcc738elgr0`,
  commit `719a56bc742bd7e8eb6850378f0b46ba46d80b66` (8 October).
- Vercel SSC project `prj_kUgZyIaJeINfRlEBOd0VVzlbvd7E`: latest production READY
  deployment `dpl_3SvqP1uyJL5oq3hAjnRNg1RCWp6w`, commit `8ea81cbe`.
  No TracliQ project was inspected beyond the project-name inventory or modified.
- Supabase `zkrxnhevwzvmdfvzfzll`: four recorded migrations, latest
  `20261009101112`; nine Phase A tables still absent. All existing public tables
  have RLS enabled; no public policies are present. Most legacy tables retain
  client table privileges, so denial depends on RLS. This catalog check does not
  prove which database role the deployed FastAPI process uses.
- All production operations this session were read-only. No migration, grants,
  bank correction, merge or deployment occurred. Existing IDs/history preserved.

## Current milestone implemented

1. Corrected misleading **seed** Syllogism example using a concrete countermodel
   and a valid contrasting chain. Live lesson inspection showed it already warns
   against merging separate witnesses; the seed defect is not attributed to that
   live lesson. Seed script skips existing rows; no live lesson was overwritten.
2. Added finite Venn-region validation for all/no/some/some-not, explicit existence
   assumptions, inconsistent premises, and counterexamples. This checks categorical
   logic, not natural-language extraction or every exam's existential convention.
3. Mock selection randomizes within exposure groups, preferring unseen content
   within the existing difficulty mix. Includes abandoned mocks, prior practice,
   solved lessons/assistance and content-equivalent duplicate IDs. When insufficient
   unseen inventory exists, repeats remain possible; test size is preserved.
   SQL authorization remains before selection. No difficulty calibration claim.
4. Removed false high-fidelity/PYQ readiness claims from source labels/year fields.
   Legacy quality counts are null (unknown); metadata completeness is separately
   named. `ready` explicitly describes inventory only.
5. Added offline curriculum priorities: defect-first editorial queue, separate
   learner queue, transitive prerequisites, independent-mastery inputs, retention,
   errors and speed. Invalid/cyclic graphs and unsupported frequency claims fail.
   It does not alter daily minutes, infer mastery from lesson opens, or change mocks
   according to beginner status. No learner endpoint consumes this draft engine yet.
6. Added 25 rationale-bearing draft dependency edges and all-74-topic reports.
   Structural validation passes; editorial mapping is incomplete. No topic is
   marked prerequisite-reviewed and learner routing stays gated. Subtopic mapping,
   deadline-aware ranking, actual learner-evidence adapter and UI remain open.

## Question-quality evidence

[Aggregate audit](evidence/curriculum_audit_2026-10-12.json): 74 topics, 10,043
verified-labelled questions, 8,970 explanations under 90 characters, 7,392
numeric-normalized stem-repeat candidates. Similar forms may be legitimate
variations; these numbers justify review, not deletion or automatic relabelling.
Question counts do not measure authentic PYQ frequency.

Reproduce the read-only SQL in `backend/scripts/curriculum_audit.sql`, then wrap
its rows as `topic_reports` with `exam_slug`. Generate the offline queue:

```text
cd backend
python -m app.scripts.prioritize_curriculum ../docs/evidence/curriculum_audit_2026-10-12.json --manifest data/curriculum_dependencies_draft.json --output <new-report.json>
```

[Dependency-aware queue](evidence/curriculum_priority_with_dependencies_2026-10-12.json)
retains unknown frequency and mapping uncertainty. Number System and Simplification
have prerequisite reach; that is pedagogical dependency evidence, not claimed SSC
frequency. Syllogism seed correction is recorded separately from live-bank flags.

Prior PDF recovery evidence remains in [11 October checkpoint](RECOVERY_EVIDENCE_2026-10-11.md):
27 files / 20 unique documents / 9,617 pages. The latest 16 references resolve to
15 files under the private PYQS directory (eight obsolete root paths resolved by
filename there). SHA-256 values are recorded privately. The earlier aggregate
checkpoint contains no reusable hash manifest, so equality to its 20 documents is
not asserted. No full metadata extraction was repeated. Targeted page analysis
and the new content-hash audit cache are recorded in the continuation evidence.
The official CGL 2026 notice was reopened successfully; full syllabus, corrigenda,
accommodations and expanded-stage validation remain required.

## Verification

- Backend: **191 passed, 6 PostgreSQL-only skipped**; pyflakes and compileall pass.
- Existing isolated loopback PostgreSQL security/migration/concurrency suite:
  **35 passed**, with synthetic `phase_a_test` role/database. First connection
  attempt used nonexistent `postgres` role; corrected without altering roles.
- Frontend: **18 passed**, TypeScript/Vite production build passed. Sandbox
  subprocess restriction required the approved test rerun outside that restriction.
- Independent review found and corrected digest-only exposure, non-Boolean mastery,
  whitespace-only evidence and iterator-consumption defects; regressions added.
- Browser/API flows: **3 passed** (scoped access, logout/back/account switch,
  stale response rejection, authorized practice and diagnostic).
- Follow-up review found legacy duplicate IDs lacking exposure rows; fixed by
  deriving current authorized content digests for legacy attempts in batches.
  Historical pre-edit stems still require Phase B immutable revisions.
- Final diff check passed. New-commit remote CI is recorded below when finished.

## Phase acceptance and exact next work

| Teaching / master phases | State | Next acceptance requirement |
|---|---|---|
| A / 0 release foundation | Engineering validated locally; release blocked | Reviewed rights/bindings/grants, actual-role compatibility, pool/asset coverage and representative migration rehearsal, then coordinated release and live verification |
| B / 0–2 historical integrity | Isolated local ledger implemented; not production-integrated | PostgreSQL migration/permissions, complete legacy snapshot adapters, authenticated editorial and assessment integration, active-mock transition and rollback |
| C / 1–2 curriculum | Aggregate audit and draft graph only | All 74 topic/subtopic objectives, reviewed dependencies, authentic paper mappings, misconception/variation coverage |
| D / 2 teaching pilot | Seed correction and logic validator only | Eight representative complete lessons with independent educational/usability evaluation |
| E / 3–5 Teacher V3 | Not complete | Guided reasoning and wrong-option diagnosis, prerequisite remediation, unseen mastery and retention, active-mock confidentiality |
| F / 6 UX | Existing responsive groundwork | Integrated learner roadmap/navigation, mobile accessibility and real learner flows |
| G / 7–9 expansion/launch | Not implemented | Full Tier I expansion, independently correct Tier II and JE Telecom blueprints, learner/paper benchmarking and live release acceptance |

The user confirmed no approved manifest exists. Do not ask for its location again.
The private exact-ID proposal now separates 2,400 repository-code-matched originals
from 7,643 unresolved legacy items, without granting access or certifying PYQ status.
Independent authorship does not require third-party republication permission.
Existing question IDs, uncertain lineage, image review, contributor completeness
and learner/course decisions remain distinct. Resolve technical mappings first;
present remaining operator decisions and production cutover together once ready.
No production migration is authorized by the draft. Do not loosen authorization.

## Latest continuation

22 October: continued PR #54 from `34e8464`, preserving six pending files.
Captured mock timing and diagnostic key/difficulty/topic/curriculum coverage now
survive later changes; Analytics displays explicit historical uncertainty.
Focused backend/security **58 passed, 7 skipped**, pyflakes passed; independent
review found no blockers. Full backend before the last curriculum/UI refinement
was **285 passed, 7 skipped**. Final frontend/CI evidence is tracked in PR #54.
This is historical-integrity delivery, not a completed educational journey.
Production and the existing A–G release gates remain unchanged.

See [12 October continuation](CONTINUATION_EVIDENCE_2026-10-12.md) for implemented
manifest guards, actual-sized synthetic rehearsal, targeted paper analysis and
eight independently reviewed original draft items. These are not eight complete
pilot lessons or empirical exam calibration. All 74 topics and Phases B–G remain
in scope, with the existing dependency order and learner pace unchanged.
Commit `05adde3fe347d27bb74a2fbf132d41ae585a741b` passed both remote CI workflows.
