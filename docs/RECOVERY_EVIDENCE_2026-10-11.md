# SSC recovery evidence — 11 October 2026

Status: Phase A engineering in progress; production cutover blocked. No phase is declared complete.
This checkpoint reconciles PR #51 (80840ce6) and PR #52 (be4299d8) with main 8ea81cbe.
The recovery branch integrates both existing heads without rewriting either branch.

## Critical provenance finding

The 53 records labelled `official` are NOT an authenticated SSC PYQ pool.
Read-only inspection of all 53 source references found factual/news sources from PIB,
ICC, IPL, Australian Open, Roland Garros, Wimbledon, US Open, Padma Awards and Nobel.
Their year fields contain 2025/2026; all 53 lack source page, source question ID and shift.
Thus `official + year + reference` does not establish even exam-paper lineage.
This corrects the earlier interpretation in PR #52. No records have been relabelled.

The recovery patch requires explicit page, shift and source-item metadata before a
legacy item can enter the **candidate** pool. It still does not assert authenticity,
key correctness or publication permission. Papers without source IDs require the
future reviewed provenance registry; they are not silently filled with practice.
The question badge now says **Source year**, never **PYQ** solely because year exists.
With current metadata this candidate pool is empty, deliberately and truthfully.

## Production baseline (read-only)

- Supabase project: `zkrxnhevwzvmdfvzfzll`, PostgreSQL 17.11.
- 10,043 questions: 7,190 original, 2,800 generated, 53 official-labelled.
- All 10,043 verified-labelled and private; zero populated shifts.
- 8,970 explanations shorter than 90 characters. Length is a screening flag, not proof of incorrectness.
- 74 CGL Tier I topics: 23 Quant, 23 Reasoning, 13 English, 15 GA.
- One account; zero in-progress mocks at observation. Recheck before any cutover.
- All nine Phase A tables absent. Existing questions/options have RLS enabled.
- Ordered question-ID aggregate digest: `c2ad4d422a2f7a481537b8ce18c0a5de` (MD5 comparison only, not security proof).
- Vercel production READY at `8ea81cbe2450d9f8dc6d73a8333b75eb94115a9c`.
- Render backend SHA not yet verified: connector requires user selection of workspace
  `My Workspace` / `tea-db1r3ccs728c73dpvtu0`. No workspace was silently selected.
- No production mutation, migration, grants, publishing, merge or deployment performed.

## PDF evidence recovered

Library title inventory located 27 PDFs, downloaded without modifying originals.
Byte hashes identify 20 unique documents and 7 duplicate copies; 9,617 unique-document pages.
The read-only scanner traversed every page for text/metadata. This is **not** full
question extraction, answer verification, difficulty calibration or expert review.

Located: eight 2014 papers; 2015, 2016, 2017, 2019, 2020, 2021, two 2022 compilations,
2023, 2024, plus two 2010 papers outside the requested year range.
No 2018-titled CGL PDF was located in targeted searches. That is an inventory gap,
not proof that a question from that exam cycle is absent from other compilations.

The 2024 document has 1,581 pages, 3,597 distinct printed source question IDs and
4,295 candidate-choice markers. Candidate choices are **never** accepted as keys.
Explicit date markers cover twelve September 2024 dates. Dates are page-local
evidence; neither extraction order nor nearby headings automatically binds them
to every question on the page.
Nineteen other unique documents contain Cracku branding. Their publication rights
and official answer-key provenance remain unreviewed.
54 pages have fewer than 40 extracted text characters and require visual/OCR review.
The 2023 compilation has no keys matching the conservative printed-key detector;
this means the detector found none, not that the document has no answer keys.

Reproduce privately:
```text
cd backend
python -m app.scripts.audit_pyq_sources <approved-pdf-directory> --output <new-private-report.json>
```
The report includes file hashes and page-local metadata, not stems, answers, chosen
responses or candidate identities. Do not attach the original PDFs or private mapping
reports to public Git. No database connection is made by this command.

## Engineering corrections

- Startup now rejects course/source grants on different users or courses and
  unapproved sources, even if independent grant counts are nonzero.
  This is a minimum effective-access gate, **not** proof every authorized learner
  retains all intended resources. Full operator compatibility review remains required.
- Added PostgreSQL concurrency regression: a queued old-section save waits behind
  the learner lock and is rejected after the next section becomes active; concurrent
  state refresh exposes only the active section. No accepted response is overwritten.
- Kept the existing historical practice-result replay fix and active-section
  confidentiality changes from PR #51.
- Tightened PYQ candidate metadata checks and corrected the event-year badge.
- Added read-only, deduplicating PDF audit and synthetic evidence/privacy tests.
- Updated the stale 2025 CGL source link to the official 2026 notice.
- Disabled Vercel automatic deployment for this recovery branch.

## Official blueprint verification

Checked official CGL 2026 notice, section 13.8 (page 25): 100 questions, four
25-question subjects, 60 minutes with 15 minutes per subject, +2/-0.5; eligible
scribe timing is 20 minutes per subject. Current simulator does not yet implement
an independently reviewed accommodation profile.
CGL Tier II includes common Paper I and role-dependent Papers II/III. The existing
planned catalog is explicitly common Paper I only; it must not claim all Tier II scope.
The table specifies 30/30 and 40/20-minute subject windows; prose also describes the
enclosing one-hour sections. Preserve this distinction in a versioned blueprint.
JE 2026 section 13 explicitly includes **Part G Telecommunication**, separate from
Scientific Assistant Part E. Paper I: 50 Reasoning + 50 GA + 100 technical, 120m,
+1/-0.25. Paper II: 100 technical, 120m, +3/-1. Expansion remains unavailable.

Sources:
- https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/Notice_of_adv_cgl_2026.pdf
- https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/Notice_of_adv_je_2026.pdf

## Required external gates and continuation

Do not merge this integrated branch until the following are resolved:
1. Operator-reviewed source rights and complete per-resource contributor bindings,
   including lessons/archetypes/flashcards and reviewed assessment crops.
2. Exact intended account/course/source entitlements and allow/deny coverage;
   preserve existing accounts/history. No automatic private grants.
3. Representative PostgreSQL rehearsal with the actual reviewed manifest, effective
   backend privileges, pool/visual sufficiency and restoration/compatible rollback.
4. Confirm Render workspace, deployed backend SHA, coordinated cutover configuration,
   old-client reload and absence of legacy active mocks.
5. Separate production release authorization and bounded LIVE-01 inputs/approval;
   deployed two-account cache/CORS/logout tests using approved synthetic accounts.

Phase B immutable revisions, answer-key/exam-blueprint pinning and publication
governance are next engineering dependencies. Historical mock review still joins
current content/marks; do not edit the bank before B. Phase C preliminary inventory
has begun; no question is authenticated by this audit. D–G have not been implemented
in this recovery pass. Real beginner/expert validation and delayed learning outcomes
cannot be replaced by synthetic CI.

## All-topic audit baseline

Pattern counts are existing label counts, not independently validated question families.
Subtopics/prerequisites/official-syllabus coverage remain pending editorial mapping.
Zero topics have year+shift-attributed questions in this snapshot.

| Subject | Topic | Questions | Official label | Explanation <90 chars | Pattern labels |
|---|---|---:|---:|---:|---:|
| english | Active & Passive Voice | 105 | 0 | 105 | 11 |
| english | Cloze Test | 105 | 0 | 105 | 9 |
| english | Direct & Indirect Speech | 105 | 0 | 104 | 11 |
| english | Error Spotting | 105 | 0 | 101 | 11 |
| english | Fill in the Blanks | 105 | 0 | 105 | 11 |
| english | Idioms & Phrases | 105 | 0 | 102 | 11 |
| english | One Word Substitution | 105 | 0 | 98 | 11 |
| english | Para Jumbles | 105 | 0 | 80 | 11 |
| english | Reading Comprehension | 105 | 0 | 105 | 11 |
| english | Sentence Improvement | 105 | 0 | 102 | 11 |
| english | Spelling | 105 | 0 | 105 | 3 |
| english | Synonyms & Antonyms | 105 | 0 | 102 | 11 |
| english | Vocabulary | 105 | 0 | 105 | 11 |
| general-awareness | Art & Culture | 35 | 0 | 35 | 11 |
| general-awareness | Awards & Honours | 23 | 18 | 13 | 2 |
| general-awareness | Biology | 35 | 0 | 35 | 11 |
| general-awareness | Books & Authors | 35 | 0 | 35 | 11 |
| general-awareness | Chemistry | 35 | 0 | 35 | 11 |
| general-awareness | Current Affairs | 20 | 15 | 9 | 2 |
| general-awareness | Economics | 35 | 0 | 32 | 11 |
| general-awareness | Environment | 35 | 0 | 35 | 11 |
| general-awareness | Geography | 35 | 0 | 34 | 11 |
| general-awareness | History | 35 | 0 | 34 | 11 |
| general-awareness | Important Days | 35 | 0 | 35 | 11 |
| general-awareness | Indian Polity | 35 | 0 | 33 | 11 |
| general-awareness | Physics | 35 | 0 | 35 | 11 |
| general-awareness | Sports | 25 | 20 | 6 | 2 |
| general-awareness | Static GK | 35 | 0 | 35 | 11 |
| quant | Algebra | 105 | 0 | 105 | 11 |
| quant | Average | 105 | 0 | 105 | 11 |
| quant | Boats & Streams | 205 | 0 | 205 | 12 |
| quant | Compound Interest | 105 | 0 | 105 | 11 |
| quant | Coordinate Geometry | 200 | 0 | 200 | 11 |
| quant | Data Interpretation | 205 | 0 | 205 | 12 |
| quant | Elementary Statistics | 200 | 0 | 200 | 11 |
| quant | Geometry | 105 | 0 | 93 | 9 |
| quant | Heights & Distances | 200 | 0 | 200 | 11 |
| quant | LCM & HCF | 205 | 0 | 205 | 12 |
| quant | Mensuration | 205 | 0 | 205 | 12 |
| quant | Mixture & Alligation | 205 | 0 | 205 | 12 |
| quant | Number System | 105 | 0 | 105 | 11 |
| quant | Percentage | 205 | 0 | 175 | 15 |
| quant | Pipes & Cisterns | 205 | 0 | 205 | 12 |
| quant | Profit, Loss & Discount | 205 | 0 | 189 | 16 |
| quant | Ratio & Proportion | 205 | 0 | 183 | 16 |
| quant | Simple Interest | 205 | 0 | 205 | 12 |
| quant | Simplification | 105 | 0 | 105 | 11 |
| quant | Time & Work | 205 | 0 | 146 | 17 |
| quant | Time, Speed & Distance | 105 | 0 | 105 | 11 |
| quant | Trains | 205 | 0 | 205 | 12 |
| quant | Trigonometry | 205 | 0 | 205 | 12 |
| reasoning | Analogy | 105 | 0 | 104 | 6 |
| reasoning | Blood Relations | 205 | 0 | 205 | 12 |
| reasoning | Classification & Odd One Out | 105 | 0 | 105 | 11 |
| reasoning | Clock & Calendar | 200 | 0 | 200 | 11 |
| reasoning | Coding-Decoding | 205 | 0 | 179 | 11 |
| reasoning | Counting Figures | 205 | 0 | 205 | 3 |
| reasoning | Dice & Cubes | 205 | 0 | 205 | 3 |
| reasoning | Dictionary Order | 205 | 0 | 104 | 11 |
| reasoning | Direction Sense | 205 | 0 | 205 | 12 |
| reasoning | Embedded Figures | 205 | 0 | 5 | 3 |
| reasoning | Figure Series | 205 | 0 | 205 | 3 |
| reasoning | Letter Series | 205 | 0 | 205 | 12 |
| reasoning | Mathematical Operations & Sign Interchange | 105 | 0 | 105 | 11 |
| reasoning | Mirror & Water Images | 205 | 0 | 204 | 3 |
| reasoning | Missing Number & Number Matrix | 100 | 0 | 100 | 10 |
| reasoning | Number Series | 205 | 0 | 143 | 16 |
| reasoning | Paper Folding & Cutting | 205 | 0 | 205 | 3 |
| reasoning | Puzzle | 200 | 0 | 200 | 11 |
| reasoning | Ranking & Order | 105 | 0 | 105 | 11 |
| reasoning | Seating Arrangement | 200 | 0 | 200 | 11 |
| reasoning | Syllogism | 205 | 0 | 5 | 12 |
| reasoning | Venn Diagrams | 205 | 0 | 155 | 12 |
| reasoning | Word Building | 200 | 0 | 0 | 11 |

