# SSC Prep Engine

Personal SSC preparation platform focused first on **SSC CGL**, designed to extend to **SSC JE** without rewriting the core engine.

## Product loop

Learn → Practice → Test → Analyse → Revise → Improve

## Core modules

- Daily preparation dashboard
- Learn mode with concise notes, shortcuts, worked examples and quick checks
- Topic-wise adaptive practice
- PYQ explorer
- Full mock and sectional tests
- Accuracy, attempt-rate, speed and error analysis
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

Initial architecture and application scaffold in progress.

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
- `/practice` — guided/adaptive/timed practice
- `/mocks` — mini, sectional and full mocks
- `/analytics` — performance analytics
- `/revision` — revision queue, flashcards and bookmarks
- `/review` — private content verification

## Deployment

The repository contains Vercel frontend configuration and a Render backend blueprint. See `docs/DEPLOYMENT.md`.
