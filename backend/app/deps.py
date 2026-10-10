from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db import get_db
from app.models import User

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")

    subject = decode_access_token(credentials.credentials)
    if not subject:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    try:
        user_id = int(subject)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token subject")

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not available")
    return user


def get_content_reviewer(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    allowed = {
        email.strip().lower()
        for email in get_settings().reviewer_emails.split(",")
        if email.strip()
    }
    if user.email.lower() not in allowed:
        raise HTTPException(status_code=403, detail="Content review access is not enabled")
    from app.services.content_access import lock_learner, require_no_assessment
    lock_learner(db, user.id)
    require_no_assessment(db, user.id)
    return user
