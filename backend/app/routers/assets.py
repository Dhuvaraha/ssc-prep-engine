from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.deps import get_current_user
from app.models import User

router = APIRouter(prefix="/assets", tags=["private-assets"])
settings = get_settings()


@router.get("/{asset_key:path}")
def get_private_asset(
    asset_key: str,
    _: User = Depends(get_current_user),
):
    root = Path(settings.private_asset_dir).resolve()
    candidate = (root / asset_key).resolve()

    try:
        candidate.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid asset path")

    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")

    return FileResponse(candidate)
