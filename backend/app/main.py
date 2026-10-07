import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db import Base, SessionLocal, engine
from app.routers import analytics, assets, auth, backup, content, exams, health, learn, mocks, planner, practice, review, revision
from app.services.content_audit import collect_content_audit
from app.services.content_repair import repair_content_integrity
from app.services.learner_canary import run_production_learner_canary
from app.services.mock_readiness import collect_mock_readiness
from app.services.teacher_readiness import collect_teacher_readiness


logger = logging.getLogger("uvicorn.error")
settings = get_settings()


def run_launch_readiness_checks(db) -> dict:
    teacher = collect_teacher_readiness(db)
    mock = collect_mock_readiness(db)
    report = {"teacher": teacher, "mock": mock}
    logger.info(
        "PHASE6_LAUNCH_READINESS %s",
        json.dumps(report, separators=(",", ":"), sort_keys=True),
    )
    if teacher.get("status") != "ready" or mock.get("status") != "ready":
        raise RuntimeError("Launch readiness audit reported pending content gates")
    return report


def run_startup_content_checks(db) -> None:
    should_check = (
        settings.content_audit_on_startup
        or settings.apply_content_repair_on_startup
    )
    if not should_check:
        logger.info("PHASE4_CONTENT_CHECKS_SKIPPED")
        return

    report = collect_content_audit(db)
    logger.info(
        "PHASE4_CONTENT_AUDIT %s",
        json.dumps(report, separators=(",", ":"), sort_keys=True),
    )

    if settings.apply_content_repair_on_startup:
        applied_plan = repair_content_integrity(db, apply=True)
        logger.info(
            "PHASE4_CONTENT_REPAIR_APPLIED %s",
            json.dumps(applied_plan, separators=(",", ":"), sort_keys=True),
        )

    repair_plan = repair_content_integrity(db, apply=False)
    logger.info(
        "PHASE4_CONTENT_REPAIR_PLAN %s",
        json.dumps(repair_plan, separators=(",", ":"), sort_keys=True),
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)

    db = SessionLocal()
    try:
        run_startup_content_checks(db)
        if settings.run_launch_audit_on_startup:
            run_launch_readiness_checks(db)
    except Exception:
        logger.exception("STARTUP_CONTENT_OR_LAUNCH_AUDIT_FAILED")
    finally:
        db.close()

    if settings.run_learner_canary_on_startup:
        try:
            canary_report = run_production_learner_canary(engine)
            if canary_report.get("status") != "passed" or not canary_report.get("rollback_verified"):
                raise RuntimeError("Phase 4D learner canary did not pass cleanly")
            logger.info(
                "PHASE4D_LEARNER_CANARY %s",
                json.dumps(canary_report, separators=(",", ":"), sort_keys=True),
            )
        except Exception:
            logger.exception("PHASE4D_LEARNER_CANARY_FAILED")

    yield

app = FastAPI(
    title="SSC Prep Engine API",
    version="0.1.0",
    description="Backend for adaptive SSC preparation, practice, mocks, analytics and revision.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(exams.router, prefix="/api/v1")
app.include_router(practice.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(content.router, prefix="/api/v1")
app.include_router(learn.router, prefix="/api/v1")
app.include_router(mocks.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(revision.router, prefix="/api/v1")
app.include_router(planner.router, prefix="/api/v1")
app.include_router(backup.router, prefix="/api/v1")
app.include_router(review.router, prefix="/api/v1")
app.include_router(assets.router, prefix="/api/v1")


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "SSC Prep Engine API", "status": "running"}
