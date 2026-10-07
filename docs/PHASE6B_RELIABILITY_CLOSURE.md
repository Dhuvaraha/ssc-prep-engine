# Phase 6B — Reliability & Edge-Case Closure

## Release gates

- exactly one active exam target is authoritative per learner
- duplicate mock starts reuse the in-progress attempt instead of creating parallel state
- duplicate mock submission is idempotent
- expired mocks reject late answer writes but still submit safely
- saved answer, review flag and time survive resume
- mock state is isolated between learners
- full mock section/timer rules remain server-authoritative
- active mock warns before accidental tab/window close
- reconnect triggers a server timing resync
- long question text and visual-question metadata survive mock creation/resume
- stale/expired sessions return the learner to the same route after login

Phase 6B is complete only when backend + frontend CI are green on the final branch and the PR diff contains only reliability changes.
