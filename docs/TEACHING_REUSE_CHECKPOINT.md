# Teaching reuse and educational review — 23 October 2026

Continues PR #55 after the development-validated Percentage journey (`bc15582`).
Phase B remains closed; Phase A production authorization is separate. No new
inventory, source proposal, learner grant or production write was performed.

## Educational review of the working pilot

The pilot teaches changing bases and successive factors, with a markup/fee bridge,
four explicit option explanations, mistake-specific prompts, fresh numerical
checks and persisted delayed recall. These are useful parts of PCT-2/PCT-4 in the
approved specification, not full Percentage coverage. Its variants mostly change
quantities within one family. Correct unassisted responses support near transfer,
not broad mastery or calibrated exam readiness.

Remaining Percentage acceptance includes graded fraction/base entry checks,
inverse reasoning, reverse comparisons, price/consumption constraints, faded
worked steps, equations/base labels and delayed context transfer. A hint flag
captures in-app assistance, not guessing or outside help. Do not infer those from
a correct option. These gaps are recorded, not silently certified by generalization.

## Implemented reusable boundary

| Shared implementation | Topic-specific content or adapter |
| --- | --- |
| Pure stage transitions, feedback, repair, fresh checks and delayed-repair rules | Versioned lesson foundations, worked examples, shortcuts and their limits |
| Aligned rotation of options, keys, explanations and repairs | Original question families, calculations, hints and misconception explanations |
| Server-owned due dates and independent/assisted evidence | Subject-specific validation and factual/source review |
| Content validation before a state can be persisted | Authorized route, source/course gates and existing persistence schema |
| React teaching/answer/repair/revision presentation | Route title and authenticated API loader |

`teaching_journey.py` is used by the existing Percentage route; `TeachingJourney`
is used by the existing page. No second state machine or copied learner UI was
created. The Percentage table, route, content version, keys and saved state shape
remain compatible. A baseline fingerprint fixes 96 question variants to bc15582.
The shared core copies input state and rejects mismatched versions or malformed
four-option packs before persistence. It establishes structural validity, not
editorial approval. No generic public route or blanket topic/source grant exists.

## Second approved pilot pack: Time & Work

An original development pack validates the same engine across joint rates,
staged work, an unknown switching time and alternating days with a partial final
day. It includes rate/unit foundations, joint and staged worked examples,
assumptions, all four option explanations and targeted repairs. Exact Fraction
checks independently verify all four families across 16 variants; alternating
answers are checked by day-by-day simulation rather than the author's formula.

The existing cached 2024 rate-switch anchor was visually reviewed and its printed
answer independently verified by conservation of work. This supports the linked
reasoning required by the new transfer family; it does not measure frequencies,
solving time or empirical difficulty. The private page/question/hash evidence
stays in the ignored review directory. No third-party stems or diagrams are copied.

Time & Work is **not registered for learner delivery**. Before integration, finish
the duration-versus-rate entry check, worked alternating example and faded steps,
explanation evidence and delayed contextual transfer. Then add a topic-scoped
persistence/access adapter with explicit reviewed source binding, and API/browser
validation. The current Percentage-only key cannot safely hold another topic's
progress. Do not reuse that row for a second course unit.

## Approved eight-topic scope retained

Percentage and Time & Work are the current bounded slices. Syllogism still needs
explicit existence and countermodels; Mirror & Water Images needs genuine reviewed
visual transformations; Error Spotting needs rule-based correction/no-error
controls; Reading Comprehension needs original passages and evidence-bound
inference; Indian Polity retains its unpublished draft and official-source review
gate; Physics needs measurement/units and motion foundations. The existing
specification, not this checkpoint, defines full acceptance. No topic or Phase C–G
is declared complete. Tier II, JE Telecom and full 74-topic expansion remain intact.

## Validation and continuation

Full backend before the final malformed-input cases: 328 passed / 10 PostgreSQL
skips. Final focused shared-engine suite: 15 passed. Frontend 21 passed; build and
pyflakes passed; all five real browser regression flows passed through the shared
component. PostgreSQL and final review/CI results are recorded in PR #55.
Independent review confirmed the new mathematics and preserved Percentage behavior;
its malformed-content validation finding was fixed with nine regression cases.

Production remains unchanged and the pilot defaults off. Next teaching work is
the remaining Time & Work lesson acceptance and topic-safe learner integration,
using these shared components rather than copying the Percentage implementation.
