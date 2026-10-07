# Phase 4A — Real-Use & Content Quality Audit

Status: **HARDENING COMPLETE — CONTENT DEPTH REMEDIATION REQUIRED**

Audit date: 2026-10-07

## Production data verified

- 1 active learner account.
- 7,243 verified question rows.
- Every verified question has exactly 4 options.
- No verified question is missing a correct option, topic or question text.
- 74/74 curriculum topics have published lesson coverage.
- Dynamic GA freshness gates for Current Affairs, Sports and Awards remain current for 2026.

## P0 production privacy finding

All verified question rows are marked `visibility=private`, while production self-registration was open.

Resolution:
- production registration is now feature-gated;
- Render production defaults registration to disabled;
- the frontend hides the registration affordance when disabled;
- existing users can continue to log in normally.

## P0 learner-quality finding

Raw verified-row counts overstated real question variety because generated banks contain repeated exact content.

Resolution:
- practice pools now canonicalize and remove exact duplicates;
- mock pools now require unique question content;
- visual questions remain distinct when their question/option images differ;
- Dashboard/Learn question counts now report unique learner-facing content instead of raw database rows;
- automated tests prevent duplicate-content regressions.

## Remaining content-depth gap

After visual-safe canonical deduplication, 28 topics fall below the original Phase-1 unique-depth threshold.

Affected areas are concentrated in:
- Quant: Boats & Streams, Coordinate Geometry, Data Interpretation, Elementary Statistics, Heights & Distances, LCM & HCF, Mensuration, Mixture & Alligation, Pipes & Cisterns, Simple Interest, Trains, Trigonometry.
- Reasoning: Blood Relations, Clock & Calendar, Counting Figures, Dice & Cubes, Dictionary Order, Direction Sense, Embedded Figures, Figure Series, Letter Series, Mirror & Water Images, Paper Folding & Cutting, Puzzle, Seating Arrangement, Syllogism, Venn Diagrams, Word Building.

This is now treated as a content-remediation backlog rather than being hidden behind inflated raw counts.

## Database platform checks

Supabase project is healthy.

Security advisor result:
- RLS is enabled on application tables with no Data API policies. This is acceptable for the current backend-only database access model and keeps direct Data API access denied by default.

Performance advisor result:
- only informational unused-index findings were reported; no release-blocking database performance issue was identified.

## Exit criteria for Phase 4 content remediation

A topic may be considered deep-bank ready only when its **unique learner-facing content** meets its threshold, not merely its raw row count.

Until those 28 topics are expanded with genuinely distinct questions, the application remains safe and usable, but the old “all topics have 100+ unique questions” interpretation must not be used.
