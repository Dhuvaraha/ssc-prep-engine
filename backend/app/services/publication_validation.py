"""Shared gate for publishing reviewed single-answer MCQs."""
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
from fastapi import HTTPException
from sqlalchemy import select
from app.access_models import ContentBinding, ContentSource
from app.core.config import get_settings
from app.models import Subject, Topic


def option_identity(text, image):
    value = ' '.join((text or '').casefold().split())
    try:
        value = str(Fraction(value.replace(' ', '')))
    except (ValueError, ZeroDivisionError):
        pass
    return value, image or ''


def validate_publication(db, data, *, visual_reviewed=False):
    q, options = data['question'], data['options']
    valid = (bool(q.get('question_text', '').strip()) and bool((q.get('explanation') or '').strip())
             and q.get('difficulty') in (1, 2, 3) and len(options) == 4
             and {o['position'] for o in options} == {1, 2, 3, 4}
             and q.get('correct_option') in {1, 2, 3, 4})
    signatures = [option_identity(o.get('text'), o.get('image_url')) for o in options]
    valid = valid and len(set(signatures)) == 4 and all(t or image for t,image in signatures)
    subject = db.get(Subject, q['subject_id'])
    topic = db.get(Topic, q['topic_id']) if q.get('topic_id') else None
    valid = valid and subject and subject.exam_id == q['exam_id'] and (not q.get('topic_id') or topic and topic.subject_id == subject.id)
    if not valid:
        raise HTTPException(422, 'PUBLICATION_CONTENT_INVALID')
    sources = list(db.scalars(select(ContentSource).join(ContentBinding,
        ContentBinding.source_id == ContentSource.id).where(
        ContentBinding.resource_kind == 'question', ContentBinding.resource_id == q['id'])))
    if not sources or any(s.exam_id != q['exam_id'] or not s.approval_reference.strip() or
        not (s.public_use_approved if q['visibility'] == 'public' else s.private_use_approved)
        for s in sources):
        raise HTTPException(422, 'PUBLICATION_SOURCE_APPROVAL_REQUIRED')
    if q.get('requires_visual_review') and not visual_reviewed:
        raise HTTPException(422, 'PUBLICATION_VISUAL_REVIEW_REQUIRED')
    for asset in data['asset_refs']:
        if not visual_reviewed or not asset['bytes_verified']:
            raise HTTPException(422, 'PUBLICATION_VISUAL_REVIEW_REQUIRED')
        ref = asset['reference']
        if ref.startswith('private://'):
            root = Path(get_settings().private_asset_dir).resolve()
            path = (root / ref.removeprefix('private://')).resolve()
            if not path.is_relative_to(root) or not path.is_file() or sha256(path.read_bytes()).hexdigest() != asset['content_sha256']:
                raise HTTPException(422, 'PUBLICATION_ASSET_CHANGED')
