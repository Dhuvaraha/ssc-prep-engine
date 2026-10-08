# Phase 7P — Performance First (before 7A / 7B / 7C)

## Observed problem

A real learner reports study pages taking about 10 seconds to load. Previous
external warm smoke samples were about 0.94s P95 for health, 1.33s for the
content tree and 1.20s for lesson packages. Those numbers do **not** measure
the authenticated planner, revision, practice, or analytics page journeys.

Both Render web services (frontend Node server + backend FastAPI) currently
use the Free instance type in Singapore. Free instances spin down after
15 minutes without traffic. A subsequent request can have a large cold-start
delay. No React skeleton, cache, or database optimisation guarantees that
a completely cold service responds instantly.

## Changes in this slice

1. Batch-hydrate revision and bookmark questions instead of one question and
   option query per queue item.
2. Filter due flashcards in a single database outer join instead of scanning
   every published card and issuing a progress query for each card.
3. Cache authenticated **GET snapshots in browser memory only** for short
   TTLs: Analytics 45s, Today 20s, Revision 20s, Flashcards/Bookmarks 20s.
   No private sessionStorage or localStorage content cache.
4. Deduplicate inflight authenticated GET requests.
5. Invalidate on successful authenticated mutations, token change, and
   session expiry; guard against older inflight reads repopulating cache.
6. Prefetch only the selected route on nav hover/focus/touch, and linked
   lesson packages on Today task hover/focus.
7. Hide unnecessary dashboard back arrow.

## Automated gates

- 30 due revision items: <= 3 SELECT statements total.
- 30 bookmarks: <= 3 SELECT statements total.
- 60 flashcards (mixed due / not due): <= 1 SELECT statement for due 20.
- Existing complete backend regression and frontend production build remain green.
- Production smoke (health, content tree, lesson package, SPA) stays green.

## Remaining prerequisites for an honest instant-page signoff

- Measure *real authenticated* planner, revision, practice and analytics cold
  and warm P50/P95, plus browser navigation TTI on desktop/mobile.
- Reproduce in a fresh browser profile, then test revisits and a session idle
  for 15+ minutes. Warm-route code must not be conflated with Free cold start.
- For consistent sub-second first loads, move the frontend to a static CDN
  and run the API on non-sleeping infrastructure. This is an infrastructure
  decision involving the user's budget and approval; no paid plan is changed
  by this PR.
- Keep exact-section mock timer and write consistency authoritative, never
  cache answer/submit/mocked state mutations or practice question selection.

## Release criteria

Cached repeat navigation should render without waiting for another network
round-trip, warm APIs should remain ideally below 1.5s P95 and any 5s warm
learner route is a release blocker. Treat cold-start results separately.
