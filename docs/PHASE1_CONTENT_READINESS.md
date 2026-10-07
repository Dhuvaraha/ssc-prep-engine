# Phase 1 Content Readiness

SSC Prep Engine keeps the private question bank in the database, not in the public repository.

## Readiness rules

- Reasoning / Quant / English: at least 100 verified questions, 10 published lesson blocks and 8 published archetypes.
- Static General Awareness: at least 30 verified fact questions, 25 published recall flashcards, 10 lesson blocks and 8 archetypes.
- Dynamic General Awareness (Current Affairs, Sports, Awards & Honours): at least 20 verified questions, at least 15 official-source questions, 15 flashcards, 10 lesson blocks, 8 archetypes, and content refreshed for the current year.
- Visual Reasoning: in addition to the Reasoning thresholds, at least 50 verified questions must contain a question visual.

Visual practice items use deterministic SVG data URLs so the private question bank can render diagrams without copying copyrighted PYQ figures into the public repository.

Use:

```bash
cd backend
python scripts/audit_content_readiness.py
```

The audit is intentionally stricter for dynamic content freshness and visual question coverage.
