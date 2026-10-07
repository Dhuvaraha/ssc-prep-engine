# Phase 3 — Production QA & Release Readiness

Status: **COMPLETE**

Release commit validated: `2200b1c38ba2fcc46dbf4c8b07c435bff6644bbb`

Phase 3 validates and hardens the Phase 2 learner workflow for production use.

## Release gates passed

### Automated code quality
- Frontend TypeScript + Vite production build passes.
- Backend `pyflakes` undefined-name/static gate passes.
- Backend Python compile check passes.
- Full backend pytest suite passes.
- GitHub Actions runs on current Node 24-compatible action majors with read-only repository permissions.

### Routed HTTP workflow
Automated FastAPI HTTP smoke covers:
- health endpoint
- CORS preflight
- registration and authenticated profile
- content tree
- planner configuration
- focused topic mock creation
- active mock resume
- answer autosave
- mock submission
- post-mock review score and accuracy
- active-attempt cleanup
- content-review authorization

### Frontend production serving
- Production bundle is served by the repository's Node static server.
- Direct SPA routes such as `/learn` and `/mocks` survive hard refresh.
- Missing asset paths return 404 instead of incorrectly serving the SPA shell.
- Health endpoint and HEAD requests are supported.
- Hashed assets receive long-lived immutable cache headers.
- Basic frame, content-type, referrer and browser-permission headers are enabled.

### Defects fixed during Phase 3
- Fixed active-mock resume crash caused by review scoring running in the wrong endpoint.
- Restored section score and accuracy in mock review.
- Weak-pattern analysis now excludes unanswered questions.
- Removed stale hard-coded planner exam date.
- Planner/settings dates use local calendar dates and reject past exam targets.
- Mobile offline banner no longer overlaps bottom navigation.
- Added keyboard focus visibility and reduced-motion support.
- Invalid answer option positions are rejected at the API boundary.
- Inactive accounts cannot receive fresh login tokens.
- Global content-review endpoints now require an explicit reviewer allowlist.
- Reviewer access denial no longer clears a valid learner login.

## Production deployment

Both production services are deployed from `main` in Render Singapore:

- Web: `https://ssc-prep-engine-web.onrender.com`
- API: `https://ssc-prep-engine-api.onrender.com`

The web service is configured to call the production API. The API CORS allowlist contains the production web origin.

Render build/deploy events for the Phase 3 release succeeded and both services reached live state. Runtime startup logs show the frontend server listening and the FastAPI application starting successfully.

## Security note

Content review is intentionally **deny-by-default** in production. Normal learner accounts cannot change global question verification data. Set `REVIEWER_EMAILS` only for explicitly approved reviewer accounts.

## Release interpretation

Phase 3 is complete with all currently known release blockers closed and automated/live deployment gates green.

No software release can prove that no defect exists on every browser/device combination. Any defect discovered during real use should be treated as a normal post-release bugfix, not as unfinished Phase 3 scope.
