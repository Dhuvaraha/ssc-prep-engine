# Phase 7D-01 — Responsive navigation and mock assessment

Status: implementation in branch; CI and browser acceptance required before merging.

## Hosting contract (unchanged)
- Public frontend: Vercel `ssc-prep-engine.vercel.app` (Vite/React).
- API: Render `ssc-prep-engine-api.onrender.com` (FastAPI).
- Learner database: Supabase PostgreSQL.
- Existing Render frontend is a temporary fallback, **not** the public frontend. This PR does not change Render services, environment variables, database schema or production deploy settings.
- On 2026-10-08, Vercel's last confirmed production release was behind `main`; direct team-scoped deployment writes returned HTTP 403 and a Vercel build-rate-limit status was seen. Release independently after fixing team authorization and build quota.

## Learner-visible changes
1. Mobile bottom navigation shows four high-use destinations (Today, Learn, Practice, Tests) and a fifth **More** action. More contains Dashboard, Revision, Analytics, Exams, Profile/Sign in. Links retain prefetch where already available, active route announcements, keyboard Escape dismissal and auto-close on route change.
2. At tablet/mobile widths, the exam question-number navigator stays compact until opened; hidden palette no longer pushes the question below a 25–40 button grid. Tapping a number moves to that question and closes the navigator after successful autosave.
3. Sticky exam header stays usable at narrow widths, preserves visible authoritative timer and submit controls, and increases mobile touch targets.
4. Diagnostic runner is correctly labelled **Starting Diagnostic** rather than Quick Sprint. Test mode cards expose pressed selection.
5. Phone spacing, safe-area bottom navigation, and score/action wrapping improved without changing exam layout on desktop.

## Acceptance gates
- [ ] GitHub backend and frontend CI green including GlobalNav interaction tests.
- [ ] Vercel preview or controlled local build at 320 / 360 / 390 / 430 / 768 / 1024 / 1440px widths, portrait and landscape; no horizontal document overflow, tiny tap targets or clipped controls.
- [ ] Verify all mobile destinations including keyboard navigation, More Escape, safe-area placement, and screen reader active navigation.
- [ ] On signed-in account, start/resume 40Q diagnostic and 100Q timed mock; check palette open/close, saved-answer navigation and locked full-test sections.
- [ ] Check timer at section rollover and expiry, submit disabled/allowed rules, login, analytics, and other routes.
- [ ] Independently confirm Vercel production SHA, API CORS and signed-in browser flow before calling production released.

## Explicitly not changed
- No exam scoring/timer/backend changes; no migrations; no new learner records.
- No Render frontend redeployment; no hidden Vercel workaround or pricing commitment.
- Remaining app pages need full 7D responsive device-matrix testing in follow-up slices.
