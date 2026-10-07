# SSC Prep Engine

Personal SSC preparation platform focused first on **SSC CGL**, designed to extend to **SSC JE** without rewriting the core engine.

## Product loop

Learn → Practice → Test → Analyse → Revise → Improve

## Core modules

- Daily preparation dashboard
- Learn mode with concise notes, shortcuts, worked examples and quick checks
- Adaptive, guided, topic, PYQ, mixed, weak-topic, revision, speed, ladder and timed practice
- Contextual browser Voice Teacher with English/Tanglish prompts
- Mini, topic, sectional and full SSC CGL Tier-I tests with autosave/resume
- Accuracy, mastery, subject, trend, confidence, speed and error analysis
- Wrong/slow/guessed/bookmarked revision queues
- Spaced repetition for GK, vocabulary and formula recall
- Exam-date-based planner
- Optional browser voice assistance

## Tech stack

- Frontend: React + TypeScript + Vite
- Backend: FastAPI + SQLAlchemy + Pydantic
- Database: PostgreSQL
- Auth: JWT
- AI: optional assistance layer; core scoring and revision logic remain deterministic

## Status

- Phase 1 — Content Intelligence & Curriculum: **complete**
- Phase 2 — Connected learner functionality: **complete**
- Phase 3 — Production QA and release validation: **pending**

Phase 2 completion gates are documented in `docs/PHASE2_FUNCTIONALITY_READINESS.md`.

## Content note

Question sources are tracked explicitly. Private study material remains private; public deployment must only expose official, licensed, original, or otherwise permitted content.


## Run locally

### Backend

```bash
cd backend
python -m venv .venv
pip install -r requirements.txt
python -m app.scripts.bootstrap_dev
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the frontend at `http://localhost:5173`.

## Main product routes

- `/` — dashboard
- `/planner` — adaptive daily study plan
- `/learn` — topic learning
- `/practice` — adaptive/guided/topic/PYQ/mixed/weak/revision/speed/ladder/timed practice
- `/mocks` — mini, focused topic, sectional and full mocks
- `/analytics` — performance analytics
- `/revision` — revision queue, flashcards and bookmarks
- `/review` — private content verification

## Deployment

The repository contains Vercel frontend configuration and a Render backend blueprint. See `docs/DEPLOYMENT.md`.
