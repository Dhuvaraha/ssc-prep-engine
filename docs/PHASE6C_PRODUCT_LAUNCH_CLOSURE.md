# Phase 6C — Product & Production Launch Closure

## Product-quality gates

- Analytics exposes first-attempt accuracy, repeat accuracy, repeat gain and time leakage.
- Practice review shows verified worked reasoning and a safe option audit without inventing unsupported distractor explanations.
- "Try one similar" resolves to a different verified same-pattern question when available, with same-topic fallback.
- Full/section mock selection prioritises official/licensed/private-PYQ evidence before original practice content.
- A 25-question section targets 7 easy / 12 medium / 6 hard questions, with deterministic fallback only when the bank cannot satisfy the target.
- Mock readiness is audited per section for unique verified depth, difficulty coverage and exam-ready traceability. PYQ/high-fidelity depth remains explicit and is prioritised when available, but original verified SSC-style content is not falsely relabelled as PYQ.

## Production gates

- Phase 6A teacher-readiness audit: status=ready, pending_topics=0.
- Phase 6C mock-readiness audit: status=ready, pending_sections=0; each section has at least 25 exam-ready questions and reports PYQ/high-fidelity availability separately.
- Rollback-safe learner canary: status=passed and rollback_verified=true.
- Backend and frontend are deployed from the final main commit.
- Public health and SPA deep-route smoke checks pass.
- Auth-required endpoints reject anonymous access.
- No startup audit/canary failure appears in production logs.
- Production request latency is measured after generating representative traffic; any 5s learner path is a release blocker and 2s+ paths require investigation.
- P0 bugs = 0 and P1 launch UX defects = 0.

## One-time production validation

The launch audit and learner canary are opt-in environment flags. They remain disabled during normal operation.

```
RUN_LAUNCH_AUDIT_ON_STARTUP=true
RUN_LEARNER_CANARY_ON_STARTUP=true
```

Deploy once, capture `PHASE6_LAUNCH_READINESS` and `PHASE4D_LEARNER_CANARY`, then return both flags to `false` and deploy the normal production configuration.

## Sign-off rule

Do not mark Phase 6C complete from CI alone. Production data gates, live deploy status, smoke checks and the rollback-safe learner canary must all pass.
