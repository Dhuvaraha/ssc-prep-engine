# Percentage journey — 23 October 2026

Continues PR #55 from `f63dfc3`, preserving the local pilot. Phase B engineering
remains closed. No production migration, grant, merge or deployment was performed.

## Learner-facing delivery

The existing Learn page discovers the pilot only for an authorized learner.
`/learn/percentage-pilot` teaches changing percentage bases, remaining fractions,
markup, fees and profit denominators. A worked example precedes diagnosis.
Post-answer teaching explains all four options, then directs an incorrect or
assisted response through prerequisite repair and a fresh numerical check.
The learner progresses to a multi-step discount/fee transfer question and saved
spaced revision. Reloads resume the current stage rather than resetting learning.

This is one original Percentage subtopic journey, not all Percentage objectives,
eight complete lessons, authentic PYQ content, empirical SSC calibration or
whole-topic mastery. Fresh numerical variants establish near-transfer evidence;
the UI explicitly does not claim exam readiness. The polity draft is preserved
and remains unpublished. No PDF inventory or source audit was repeated.

## Persistence and controls

- Additive `percentage_pilot_progress` table, scoped by learner and exam. Existing
  question, attempt, progress and mock tables are not rewritten.
- Server-owned version, stage, assistance, answer history and due dates. Keys and
  option explanations appear only after submission. Existing authenticated
  no-store/session handling and active-assessment teaching denial apply.
- Shared learner row lock plus optimistic revision comparison rejects stale or
  concurrent writes. Feature, review-reference, exam, course and explicit source
  grants must all allow access. Source metadata never establishes rights.
- Fresh option order rotates with the persisted variant; keys, explanations and
  repair mappings move together. Generated transfer quantities cannot duplicate
  the original item. Correct hinted responses are learning, not independent passes.
- Initial revision is due after one day; successful delayed checks schedule three
  then seven days. Failed/assisted revision followed by immediate repair does not
  earn retention: another delayed check is scheduled after one day.
- Version mismatch rejects both reading and updating until a reviewed migration
  exists. Any future change to item generation/content must bump the version;
  do not reinterpret saved variants or overwrite their history.

## Validation

- Full backend: **322 passed, 10 PostgreSQL-only skips**; compileall and pyflakes pass.
- Isolated PostgreSQL pilot API/migration suite: **8 passed**, including concurrent
  first actions (one winner), RLS/direct-client privileges, repeated migration
  preserving saved progress, access revocation, history preservation and due dates.
- Frontend: **21 tests passed**, production build passed.
- Full browser regression: **5 flows passed**. After the review fixes, the pilot
  was rerun successfully on desktop and at 390px mobile width, including saved
  repair, four explanations, fresh checks, advanced transfer, scheduled revision
  and no horizontal overflow. Delayed revisions use an injected clock in API
  tests; no production time override exists.
- Independent review checked mathematics, educational explanations, access,
  history/concurrency and state transitions. Its three findings (immediate repair
  counted as retention, repeated transfer quantities, fixed keys) were fixed and
  independently re-reviewed with no remaining scoped blockers. This is agent
  review and synthetic validation, not a human learner usability study.

## Release gates and rollback

Pilot defaults off: `PERCENTAGE_PILOT_ENABLED=false`. No production source or
learner grants have been invented. Before enabling, complete the separate Phase A
authorization/cutover gates, obtain approval for the exact original source and
intended learner scope, and record the exact content-version review reference.
Configure `PERCENTAGE_PILOT_SOURCE_ID` and `PERCENTAGE_PILOT_REVIEW_REFERENCE` only
against that evidence, never the synthetic browser fixture.

On the approved target, run the explicit additive
`app.percentage_pilot_migration.migrate(engine)` using the authorized migration
role; verify backend-role SELECT/INSERT/UPDATE compatibility and direct-client
denial. Rehearse backup/restore and the actual authorized account flow before
enabling. The migration is not automatically run on production startup.
Disable the feature to withdraw the pilot; retain its table and history for
resumption. Do not drop progress or downgrade to code that reinterprets variants.

The next milestone stays in the existing teaching roadmap, after this pilot's
CI gates. Do not reopen Phase B or claim 74-topic/Phases C–G completion.
