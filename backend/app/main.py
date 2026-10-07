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


logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)

    db = SessionLocal()
    try:
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
    except Exception:
        logger.exception("PHASE4_CONTENT_AUDIT_FAILED")
    finally:
        db.close()

    yield


settings = get_settings()

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
