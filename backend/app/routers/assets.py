from pathlib import Path
import hashlib

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import get_db
from app.services.content_access import content_user, require_no_assessment
from app.services.mock_engine import mock_timing
from app.access_models import AssessmentAsset
from app.models import MockAttempt, MockAttemptQuestion, Question, QuestionOption, User

router = APIRouter(prefix="/assets", tags=["private-assets"])
settings = get_settings()


@router.get("/{asset_key:path}")
def get_private_asset(
    asset_key: str,
    user: User = Depends(content_user),
    db: Session = Depends(get_db),
):
    root = Path(settings.private_asset_dir).resolve()
    candidate = (root / asset_key).resolve()

    try:
        candidate.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid asset path")

    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")

    locator = "private://" + asset_key
    referenced = select(Question.id).where(Question.verification_status == "verified", or_(
        Question.question_image_url == locator,
        Question.id.in_(select(QuestionOption.question_id).where(QuestionOption.image_url == locator)),
    ))
    active = db.scalar(select(MockAttempt).where(MockAttempt.user_id == user.id, MockAttempt.status == "in_progress"))
    if active:
        timing = mock_timing(active)
        reviewed = db.get(AssessmentAsset, asset_key)
        rows = select(MockAttemptQuestion.question_id).where(MockAttemptQuestion.attempt_id == active.id)
        if active.mode == "full":
            rows = rows.where(MockAttemptQuestion.section_slug == timing["active_section_slug"])
        if not reviewed or timing["seconds_left"] <= 0 or not db.scalar(referenced.where(Question.id.in_(rows)).limit(1)):
            require_no_assessment(db, user.id)
        data = candidate.read_bytes()
        if hashlib.sha256(data).hexdigest() != reviewed.content_sha256:
            raise HTTPException(409, "ASSET_REVIEW_REQUIRED")
    else:
        if db.scalar(referenced.limit(1)) is None:
            raise HTTPException(404, "Asset not found")
        data = candidate.read_bytes()
    import mimetypes
    return Response(data, media_type=mimetypes.guess_type(candidate.name)[0] or "application/octet-stream",
                    headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
