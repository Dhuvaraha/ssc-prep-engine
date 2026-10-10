"""Offline operator workflow. No learner-facing grant mutation endpoint.

Review manifest -> dry run -> approve exact SHA -> apply in one transaction.
This module never reads credentials or connects to a database on import.
"""
from hashlib import sha256
import json
from pathlib import Path
import re

from sqlalchemy import func, select

from app.access_models import AssessmentAsset, ContentBinding, ContentSource, CourseGrant, EntitlementAudit, SourceGrant
from app.core.config import get_settings
from app.models import Exam, Flashcard, Lesson, MockAttempt, Question, QuestionArchetype, Subject, Topic, User


RESOURCE_MODELS = {"question": Question, "lesson": Lesson, "archetype": QuestionArchetype, "flashcard": Flashcard}


def manifest_digest(manifest):
    return sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def apply_manifest(db, manifest, *, approved_digest=None):
    """Dry runs roll back their savepoint. Grants never come from registration."""
    fingerprint = manifest_digest(manifest)
    apply = approved_digest is not None
    if apply and approved_digest != fingerprint:
        raise ValueError("Reviewed manifest digest does not match")
    if not manifest.get("operator") or not manifest.get("reason"):
        raise ValueError("Operator and review reason are required")
    # Same lock order as learner requests; source changes can affect any user.
    db.execute(select(User.id).order_by(User.id).with_for_update()).all()
    transaction = db.begin_nested()
    try:
        for item in manifest.get("sources", []):
            if not item.get("approval_reference") or item.get("rights_basis") not in {"original", "licensed", "private_permission"}:
                raise ValueError("Explicit rights review required; official/verified is not a license")
            if item.get("public_use_approved") and item["rights_basis"] == "private_permission":
                raise ValueError("Private permission cannot approve public publication")
            if not db.get(Exam, item["exam_id"]):
                raise ValueError("Unknown course")
            source = db.get(ContentSource, item["id"])
            if source and source.exam_id != item["exam_id"]:
                raise ValueError("Existing source course cannot be reassigned")
            if not source:
                source = ContentSource(id=item["id"], exam_id=item["exam_id"])
                db.add(source)
            source.private_use_approved = item.get("private_use_approved") is True
            source.public_use_approved = item.get("public_use_approved") is True
            source.approval_reference = item["rights_basis"] + ": " + item["approval_reference"]
        db.flush()
        for item in manifest.get("bindings", []):
            kind, resource_id, source_id = item["resource_kind"], item["resource_id"], item["source_id"]
            if kind not in RESOURCE_MODELS:
                raise ValueError("Unknown resource kind")
            resource = db.get(RESOURCE_MODELS[kind], resource_id)
            source = db.get(ContentSource, source_id)
            if not resource or not source:
                raise ValueError("Unknown resource or source")
            topic = db.get(Topic, resource.topic_id) if resource.topic_id else None
            subject = db.get(Subject, topic.subject_id) if topic else None
            exam_id = resource.exam_id if kind == "question" else subject.exam_id if subject else None
            if exam_id != source.exam_id or (kind == "question" and subject and subject.id != resource.subject_id):
                raise ValueError("Resource/course/source mismatch")
            key = (kind, resource_id, source_id)
            if not db.get(ContentBinding, key):
                db.add(ContentBinding(resource_kind=kind, resource_id=resource_id, source_id=source_id))
        for item in manifest.get("courses", []):
            if not db.get(User, item["user_id"]) or not db.get(Exam, item["exam_id"]):
                raise ValueError("Unknown user or course")
            grant = db.get(CourseGrant, (item["user_id"], item["exam_id"]))
            if not grant:
                grant = CourseGrant(user_id=item["user_id"], exam_id=item["exam_id"])
                db.add(grant)
            grant.active = item["active"] is True
        for item in manifest.get("grants", []):
            if not db.get(User, item["user_id"]) or not db.get(ContentSource, item["source_id"]):
                raise ValueError("Unknown user or source")
            grant = db.get(SourceGrant, (item["user_id"], item["source_id"]))
            if not grant:
                grant = SourceGrant(user_id=item["user_id"], source_id=item["source_id"])
                db.add(grant)
            grant.active = item["active"] is True
        for item in manifest.get("assessment_assets", []):
            root = Path(get_settings().private_asset_dir).resolve()
            candidate = (root / item["asset_key"]).resolve()
            if not candidate.is_relative_to(root) or not candidate.is_file() or not item.get("review_reference"):
                raise ValueError("Reviewed assessment crop must exist under the private asset root")
            if not re.fullmatch(r"[0-9a-f]{64}", item["content_sha256"]) or sha256(candidate.read_bytes()).hexdigest() != item["content_sha256"]:
                raise ValueError("Assessment asset bytes do not match the reviewed digest")
            asset = db.get(AssessmentAsset, item["asset_key"])
            if not asset:
                asset = AssessmentAsset(asset_key=item["asset_key"])
                db.add(asset)
            asset.content_sha256 = item["content_sha256"]
            asset.review_reference = item["review_reference"]
        db.flush()
        report = {"manifest_digest": fingerprint, "applied": apply,
                  "active_assessments": db.scalar(select(func.count()).select_from(MockAttempt).where(MockAttempt.status == "in_progress")),
                  "active_course_grants": db.scalar(select(func.count()).select_from(CourseGrant).where(CourseGrant.active.is_(True))),
                  "active_source_grants": db.scalar(select(func.count()).select_from(SourceGrant).where(SourceGrant.active.is_(True)))}
        report["accounts_without_active_course"] = db.scalar(select(func.count()).select_from(User).where(
            User.id.not_in(select(CourseGrant.user_id).where(CourseGrant.active.is_(True)))))
        report["accounts_without_active_source"] = db.scalar(select(func.count()).select_from(User).where(
            User.id.not_in(select(SourceGrant.user_id).where(SourceGrant.active.is_(True)))))
        for kind, model in RESOURCE_MODELS.items():
            mapped = select(ContentBinding.resource_id).where(ContentBinding.resource_kind == kind)
            report["unmapped_" + kind] = db.scalar(select(func.count()).select_from(model).where(model.id.not_in(mapped)))
        if apply:
            db.add(EntitlementAudit(operator=manifest["operator"], reason=manifest["reason"], manifest_digest=fingerprint))
            transaction.commit()
        else:
            transaction.rollback()
        return report
    except Exception:
        transaction.rollback()
        raise
