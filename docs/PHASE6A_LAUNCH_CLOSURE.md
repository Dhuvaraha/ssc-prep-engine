# Phase 6A — Pedagogy & Sprint Closure

This phase closes the remaining learner-strategy and teaching-quality gaps from the launch plan.

## Gates

- 7-day sprint has explicit D-7/D-6 coverage, D-5/D-4 consolidation, D-3/D-2 test-and-repair, D-1 taper, and exam-day light recall stages.
- D-1 and exam day never schedule a fatigue-heavy full mock.
- Planner still fills the declared study budget and preserves completed tasks during rebalance.
- Topic weakness labels remain evidence-aware.
- Teacher readiness is audited per topic, not inferred from file existence.
- Quant and Reasoning require published concept, recognition, method, shortcut and trap blocks.
- English requires published concept, recognition, method and trap blocks.
- General Awareness additionally requires active-recall content.
- Every topic must have at least one published archetype.
- Every topic must have verified explained Easy, SSC-level and Hard examples.
- No learner-facing explanation may invent distractor logic that is not present in verified content.

Run the teacher gate with:

```bash
cd backend
PYTHONPATH=. python scripts/audit_teacher_readiness.py
```

Phase 6A is signable only when CI is green and the production teacher-readiness report returns `status=ready` with zero pending topics.
