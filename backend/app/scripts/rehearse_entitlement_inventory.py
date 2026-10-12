"""Rehearse inventory topology with synthetic content on loopback PostgreSQL only.

Never loads real stems, answers, emails, credentials or scores. This validates
size/topology and transactional preservation, not actual rights or image coverage.
"""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, func, insert, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.db import Base
from app.models import (Exam, Flashcard, Lesson, LessonBlock, MockAttempt, MockAttemptQuestion,
                        Question, QuestionArchetype, QuestionAttempt, QuestionOption, Subject, Topic, User)
from app.access_models import ContentSource, SourceGrant
from app.phase_a_migration import TABLES, migrate, verify_rollout
from app.services.content_access import question_policy
from app.services.entitlement_admin import apply_manifest, manifest_digest
from app.services.entitlement_proposal import propose


def snapshot(connection, tables):
    result = {}
    for table in tables:
        rows = connection.execute(select(table).order_by(*table.primary_key.columns)).all()
        result[table.name] = sha256(json.dumps([list(row) for row in rows], default=str).encode()).hexdigest()
    return result


def validate_asset_coverage(inventory, proposal, coverage):
    """Check cached mappings only; never upgrade metadata into asset approval."""
    bindings = {b['resource_id']: b['source_id'] for b in proposal['bindings']}
    expected = sorted((a['usage'], tuple(sorted(a['question_ids'])), sha256(a['asset_url'].encode()).hexdigest()) for a in inventory['assets'])
    actual = sorted((a['usage'], tuple(sorted(a['question_ids'])), a.get('asset_reference_digest')) for a in coverage['assets'])
    if actual != expected or coverage['proposal_source_groups'] != len(proposal['sources']):
        raise ValueError('Asset coverage does not match the existing proposal/inventory')
    for asset in coverage['assets']:
        if asset['source_ids'] != sorted({bindings[qid] for qid in asset['question_ids']}):
            raise ValueError('Asset contributor references do not match question bindings')
        if asset['visual_review_complete'] is not False or asset['rights_approved'] is not False:
            raise ValueError('Metadata rehearsal must not claim visual or rights approval')
    return {'mapped_asset_reference_groups': len(actual),
            'static_svg_screen_passed': sum(a['static_svg_screen_passed'] is True for a in coverage['assets']),
            'asset_delivery_tested': False, 'asset_mapping_digest': manifest_digest(coverage)}


def run(inventory, topology, url, *, proposal=None, coverage=None):
    parsed = make_url(url)
    if parsed.host not in {"127.0.0.1", "localhost"} or parsed.database != "ssc_phase_a_test":
        raise ValueError("Rehearsal requires loopback database ssc_phase_a_test")
    if parsed.drivername != "postgresql+psycopg" or parsed.query:
        raise ValueError("Use postgresql+psycopg without connection query overrides")
    if proposal is None:
        proposal = propose(inventory)
    else:
        expected = {qid for group in inventory["sources"] for qid in group["question_ids"]}
        bindings = proposal["bindings"]
        sources = {source["id"] for source in proposal["sources"]}
        if (len(sources) != len(proposal["sources"]) or len(bindings) != len(expected)
                or {b["resource_id"] for b in bindings} != expected
                or any(b["resource_kind"] != "question" or b["source_id"] not in sources for b in bindings)):
            raise ValueError("Proposal must exactly cover inventory questions with existing source IDs")
    asset_report = validate_asset_coverage(inventory, proposal, coverage) if coverage is not None else {}
    if len(inventory["users"]) != 1 or len(inventory["exams"]) != 1:
        raise ValueError("This rehearsal currently supports the observed one-account, one-course topology only")
    schema = "phase_a_" + uuid4().hex
    # libpq query/service/PGHOSTADDR settings must never redirect this rehearsal.
    # Explicit connection args override environment routing; query overrides are
    # rejected above. The generated schema is the only schema we later remove.
    local_args = {"hostaddr": "127.0.0.1", "dbname": "ssc_phase_a_test"}
    admin = create_engine(url, connect_args=local_args)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={**local_args, "options": f"-csearch_path={schema}"})
    legacy = [table for table in Base.metadata.sorted_tables if table not in TABLES]
    try:
        with engine.begin() as connection:
            Base.metadata.create_all(connection, tables=legacy)
            for exam in inventory["exams"]:
                connection.execute(insert(Exam), dict(id=exam["id"], slug=exam["slug"],
                                                     name="Synthetic course", duration_minutes=60))
            for subject in topology["subjects"]:
                connection.execute(insert(Subject), {**subject, "name": "Synthetic subject"})
            for topic in topology["topics"]:
                connection.execute(insert(Topic), {**topic, "name": "Synthetic topic"})
            user_ids = [user["id"] for user in inventory["users"]]
            outsider = max(user_ids, default=0) + 1
            for user_id in [*user_ids, outsider]:
                connection.execute(insert(User), dict(id=user_id, email=f"synthetic-{user_id}@example.invalid",
                                                     password_hash="not-a-login", is_active=True))
            question_rows = []
            for group in topology["question_groups"]:
                for qid in group["ids"]:
                    question_rows.append(dict(id=qid, exam_id=group["exam_id"], subject_id=group["subject_id"],
                        topic_id=group["topic_id"], difficulty=group["difficulty"],
                        question_text=f"Synthetic arithmetic fixture {qid}: 1+1?", correct_option=1,
                        explanation="One plus one equals two.", verification_status="verified"))
            connection.execute(insert(Question), question_rows)
            options = [dict(question_id=q["id"], position=i, text=str(i + 1))
                       for q in question_rows for i in range(1, 5)]
            connection.execute(insert(QuestionOption), options)
            model_map = {"lesson": Lesson, "archetype": QuestionArchetype, "flashcard": Flashcard}
            for resource in inventory["resources"]:
                common = dict(id=resource["id"], topic_id=resource["topic_id"])
                if resource["kind"] == "lesson":
                    values = dict(title="Synthetic lesson", intro="Synthetic", concept="Synthetic")
                elif resource["kind"] == "archetype":
                    values = dict(slug=f"synthetic-{resource['id']}", name="Synthetic", skill="Synthetic",
                                  recognition_cues="Synthetic", canonical_method="Synthetic")
                else:
                    values = dict(front="Synthetic question", back="Synthetic answer")
                connection.execute(insert(model_map[resource["kind"]]), {**common, **values})
            for block in inventory["lesson_blocks"]:
                connection.execute(insert(LessonBlock), {**block, "block_type": "concept",
                                                         "title": "Synthetic", "body": "Synthetic"})
            # Match history row counts, not private learner answers or historical scores.
            baseline = inventory["baseline"]
            for index in range(baseline["question_attempts"]):
                connection.execute(insert(QuestionAttempt), dict(user_id=user_ids[0],
                    question_id=question_rows[index % len(question_rows)]["id"], selected_option=1, is_correct=True))
            for index in range(baseline["mock_attempts"]):
                connection.execute(insert(MockAttempt), dict(id=index+1, user_id=user_ids[0],
                    exam_id=inventory["exams"][0]["id"], mode="full", duration_minutes=60,
                    status="submitted", score=123.5))
            for index in range(baseline["mock_responses"]):
                connection.execute(insert(MockAttemptQuestion), dict(attempt_id=1,
                    question_id=question_rows[index % len(question_rows)]["id"],
                    section_slug="synthetic", position=index+1, selected_option=1))
            before = snapshot(connection, legacy)
        migrate(engine)
        migrate(engine)
        # Draft must not be executable. Hypothetical approvals below apply only
        # to the synthetic fixtures created in this generated schema.
        manifest = {"operator": "synthetic-rehearsal", "reason": "Original synthetic topology fixtures",
                    "sources": [], "bindings": [], "courses": [], "grants": []}
        for source in proposal["sources"]:
            manifest["sources"].append(dict(id=source["id"], exam_id=source["exam_id"], rights_basis="original",
                approval_reference="synthetic-fixture-only", private_use_approved=True, public_use_approved=False))
        manifest["bindings"] = [{k: b[k] for k in ("resource_kind", "resource_id", "source_id")}
                                for b in proposal["bindings"]]
        for resource in inventory["resources"]:
            source = next(s for s in manifest["sources"] if s["exam_id"] == resource["exam_id"])
            manifest["bindings"].append(dict(resource_kind=resource["kind"], resource_id=resource["id"],
                                              source_id=source["id"]))
        for course in proposal["courses"]:
            manifest["courses"].append(dict(user_id=course["user_id"], exam_id=course["exam_id"], active=True))
            manifest["grants"].extend(dict(user_id=course["user_id"], source_id=s["id"], active=True)
                                      for s in manifest["sources"] if s["exam_id"] == course["exam_id"])
        with Session(engine) as db:
            dry_run = apply_manifest(db, manifest)
            assert all(dry_run["unmapped_" + kind] == 0 for kind in ("question", "lesson", "archetype", "flashcard"))
            assert not db.scalar(select(func.count()).select_from(ContentSource))
            db.rollback()
            with engine.connect() as connection:
                assert before == snapshot(connection, legacy)
            apply_manifest(db, manifest, approved_digest=manifest_digest(manifest))
            db.commit()
        verify_rollout(engine, manifest_digest(manifest))
        exam_id = inventory["exams"][0]["id"]
        with Session(engine) as db:
            allowed = db.scalar(select(func.count()).select_from(Question).where(question_policy(user_ids[0], exam_id)))
            denied = db.scalar(select(func.count()).select_from(Question).where(question_policy(outsider, exam_id)))
            assert allowed == len(question_rows) and denied == 0
            source_id = manifest["sources"][0]["id"]
            grant = db.get(SourceGrant, (user_ids[0], source_id))
            grant.active = False
            db.flush()
            reduced = db.scalar(select(func.count()).select_from(Question).where(question_policy(user_ids[0], exam_id)))
            assert reduced < allowed
            db.rollback()
            assert db.scalar(select(func.count()).select_from(Question).where(question_policy(user_ids[0], exam_id))) == allowed
        scoped_counts = {}
        for model in (Question, Lesson, LessonBlock, QuestionArchetype, Flashcard):
            with Session(engine) as db:
                expected = len(db.scalars(select(model.id)).all())
                db.info["content_scope"] = (user_ids[0], exam_id)
                actual = len(db.scalars(select(model.id)).all())
                db.info["content_scope"] = (outsider, exam_id)
                assert len(db.scalars(select(model.id)).all()) == 0
                assert actual == expected
                scoped_counts[model.__tablename__] = actual
        with engine.connect() as connection:
            assert before == snapshot(connection, legacy)
        return {**asset_report, "proposal_digest": manifest_digest(proposal),
                "synthetic_only": True, "question_count": len(question_rows),
                "question_options": len(options), "source_groups": len(proposal["sources"]),
                "resource_count": len(inventory["resources"]), "lesson_blocks": len(inventory["lesson_blocks"]),
                "legacy_columns_preserved": True, "migration_repeatable": True,
                "dry_run_rolled_back": True, "scoped_orm_allow_deny_passed": True,
                "scoped_resource_counts": scoped_counts,
                "tested_learner_accounts": 1, "tested_denied_accounts": 1, "tested_courses": 1,
                "http_routes_tested_by_this_rehearsal": False,
                "revocation_transaction_rollback_passed": True,
                "production_rights_validated": False, "production_assets_validated": False,
                "production_backend_role_validated": False, "production_ready": False}
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("topology", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--proposal", type=Path, help="Reuse the existing private proposal without regenerating it")
    parser.add_argument("--coverage", type=Path, help="Existing private image/source mapping; not approvals")
    args = parser.parse_args()
    url = os.environ.get("PHASE_A_TEST_DATABASE_URL")
    if not url:
        parser.error("Set PHASE_A_TEST_DATABASE_URL to the isolated loopback test database")
    result = run(json.loads(args.inventory.read_text(encoding="utf-8")),
                 json.loads(args.topology.read_text(encoding="utf-8")), url,
                 proposal=json.loads(args.proposal.read_text(encoding="utf-8")) if args.proposal else None,
                 coverage=json.loads(args.coverage.read_text(encoding="utf-8")) if args.coverage else None)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
