# Phase 7Q — Learner Bugfix Sweep

## Findings and fixes

| Area | Repro/risk before this change | Resolution |
|---|---|---|
| Practice | Double click Check answer or timed expiry overlapping manual submit could record duplicate attempts | Synchronous per-route submission guard, disabled answer controls while saving, explicit timed retry |
| Practice | Change practice topic/mode while old request is pending could render old question results on the new route | Cancel stale fetch callbacks, fully reset local state, guard asynchronous submit result by route generation |
| Revision | Loading a tab or changing filters briefly displayed an incorrect 'No items due' state or stale previous queue | Actual loading state and cancelled stale requests |
| Revision | Rapid Review/Flashcard grade taps could schedule the same item twice | Synchronous grading lock and clear error feedback |
| Revision bookmarks | Question and option images were missing in bookmarked visual items | Secure question/option image rendering |
| Mock | Answer, review flag, next and submit actions could overlap, last response could win out of order | One in-flight save at a time; disable interactive writes while saving; pending answer completion awaited before submit |
| Mock start | API reused an active attempt, but frontend assumed fresh start in an initial active-check/two-tab race | Explicit `resumed_existing` API flag and 'Resume existing test' handoff, initial active check gate |
| Home | Duplicate navigation toolbar + misleading diagnostic CTA, empty-data zeros | Simplified header, state-aware copy, truthful Quick Sprint labelling, unknown metrics render as missing evidence |
| Backup | Export failure was unhandled with no user feedback | Loading/error states and safe object URL cleanup |
| Deep links | Context-bar browser-history back could send learner outside the product | Deterministic parent route; no back arrow on home |

## Automated release gates
- Backend unit suite including fresh/duplicate mock start flag asserts.
- Frontend TypeScript build + SPA server CI.
- Clean PR CI, no change to exam scoring or section timing.
- Latest main deploy for both API and Web + production smoke gate.

## Human acceptance checklist (still required)
- Desktop and mobile: browse Home, Learn, Practice, Tests, Revision, Analytics.
- Practice: rapidly double click Check answer; simulate a timed expiry; navigate between topic and mixed routes while a request is pending.
- Mock: select, clear, mark, save and navigate rapidly; reload/resume; test two browser tabs and slow/offline network. Ensure the selected answer remains saved and active timer remains server authoritative.
- Revision: switch Due/Flashcards/Bookmarks during loading; test manual grades under failed network; check image-backed bookmarked questions.
- Verify warm and cold page load separately. Existing Render sleep is not solved by UI bugfixes.

Do not mark human acceptance as complete from CI alone.
