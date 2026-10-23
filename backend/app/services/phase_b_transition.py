"""Offline, additive active-mock transition under coordinated admission freeze.

Caller owns commit/rollback. Never start this from application lifespan.
"""
from sqlalchemy import select, text, update
from app.core.config import get_settings
from app.models import MockAttempt, MockAttemptQuestion, Question, QuestionOption
from app.access_models import AssessmentDelivery, ContentBinding
from app.revision_models import DeliveryRevision
from app.services.revision_capture import lock_questions, snapshot, bind_mock_timing, capture_state
from app.services.revision_ledger import canonical, digest
from app.services.practice_integrity import question_digest


def legacy_checksum(db):
    from app.models import QuestionAttempt
    result = {}
    for model in (Question, QuestionOption, QuestionAttempt, MockAttempt, MockAttemptQuestion):
        table = model.__table__
        rows = db.execute(select(table).order_by(*table.primary_key.columns)).mappings()
        values = [{k: v.isoformat() if hasattr(v, 'isoformat') else v for k,v in row.items()} for row in rows]
        result[table.name] = {'count': len(values), 'sha256': digest(values)}
    return result


def transition_active_mocks(db, blueprints, *, exam_id, admission_frozen, limit=100):
    settings = get_settings()
    if not (admission_frozen is True and settings.phase_b_transition_mode and
            settings.phase_b_capture_enabled and not settings.phase_b_publication_enabled):
        raise ValueError('Coordinated maintenance, capture on and publication off required')
    if db.info.get('content_scope'):
        raise ValueError('Transition requires the reviewed backend role, not a learner session')
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError('Bounded transition batch required')
    if type(exam_id) is not int or exam_id < 1:
        raise ValueError('Explicit exam scope required')
    from app.phase_b_migration import verify
    verify(db.bind)
    if db.bind.dialect.name == 'postgresql':
        # No content/answer writer may cross the snapshot boundary. Maintenance
        # drains old binaries; these locks also protect against stray DB writers.
        db.execute(text('LOCK TABLE questions, question_options, mock_attempts, mock_attempt_questions, assessment_deliveries, content_bindings, delivery_revisions IN ACCESS EXCLUSIVE MODE'))
    else:
        db.execute(update(Question).values(id=Question.id))
    before = legacy_checksum(db)
    attempts = db.scalars(select(MockAttempt).where(MockAttempt.status == 'in_progress', MockAttempt.exam_id == exam_id)
                         .order_by(MockAttempt.id)).all()
    transitioned = []
    for attempt in attempts:
        rows = db.scalars(select(MockAttemptQuestion).where(MockAttemptQuestion.attempt_id == attempt.id)
                          .order_by(MockAttemptQuestion.position)).all()
        pins = db.scalars(select(DeliveryRevision).where(DeliveryRevision.kind == 'mock',
                           DeliveryRevision.delivery_id == str(attempt.id))).all()
        if pins:
            bind_mock_timing(db, attempt)  # Partial evidence is never repaired by guessing.
            continue
        if len(transitioned) >= limit:
            break
        if not rows:
            raise ValueError('Active attempt has no question rows')
        blueprint = blueprints.get(attempt.mode)
        if not blueprint or blueprint.get('duration_minutes') != attempt.duration_minutes:
            raise ValueError('Explicit matching historical blueprint required')
        if any(type(blueprint.get(k)) not in (int, float) or blueprint[k] < 0 for k in ('positive_marks', 'negative_marks')):
            raise ValueError('Explicit nonnegative historical scoring required')
        questions = {q.id: q for q in lock_questions(db, [r.question_id for r in rows])}
        for row in rows:
            q = questions.get(row.question_id)
            if not q:
                raise ValueError('Missing legacy question')
            delivered = db.get(AssessmentDelivery, (attempt.id, q.id))
            if delivered and (delivered.content_digest != question_digest(q) or delivered.correct_option != q.correct_option):
                raise ValueError('Legacy assessed content changed; explicit adjudication required')
            sources = sorted(db.scalars(select(ContentBinding.source_id).where(
                ContentBinding.resource_kind == 'question', ContentBinding.resource_id == q.id)))
            if not sources:
                raise ValueError('Missing source bindings')
            capture_state(db, q)  # Refuse unversioned assets before transition.
            rid = snapshot(db, q, kind='legacy_capture_at_migration')
            db.add(DeliveryRevision(kind='mock', delivery_id=str(attempt.id), question_id=q.id,
                user_id=attempt.user_id, revision_id=rid, source_ids=canonical(sources),
                blueprint=canonical({**blueprint, 'mode': attempt.mode, 'position': row.position,
                    'section_slug': row.section_slug, 'transition_basis': 'operator_reviewed_current_capture',
                    'original_version_unknown': True})))
        db.flush()
        bind_mock_timing(db, attempt)
        transitioned.append(attempt.id)
    after = legacy_checksum(db)
    if before != after:
        raise RuntimeError('Transition changed legacy identity, content or learner history')
    return {'exam_id': exam_id, 'transitioned_attempt_ids': transitioned, 'legacy_checksums': before,
            'legacy_preserved': True, 'original_versions_reconstructed': False}
