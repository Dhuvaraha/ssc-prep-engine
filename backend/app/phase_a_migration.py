"""Additive DDL, invoked explicitly by an operator after review.

No legacy rows are updated. Empty grant tables deny access. PostgreSQL tables
are backend-only: RLS enabled, PUBLIC/anon/authenticated privileges revoked.
"""
import os

from sqlalchemy import create_engine, inspect, select, text

from app import access_models
from app.db import Base, normalize_database_url
from app.models import MockAttempt


TABLES = [table for table in Base.metadata.sorted_tables if table.name in {
    model.__tablename__ for model in vars(access_models).values()
    if isinstance(model, type) and hasattr(model, "__tablename__")
}]


def migrate(engine):
    with engine.begin() as connection:
        Base.metadata.create_all(connection, tables=TABLES)
        if engine.dialect.name == "postgresql":
            roles = set(connection.scalars(text("SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')")))
            for table in TABLES:
                name = connection.dialect.identifier_preparer.quote(table.name)
                connection.execute(text(f"ALTER TABLE {name} ENABLE ROW LEVEL SECURITY"))
                connection.execute(text(f"REVOKE ALL ON TABLE {name} FROM PUBLIC"))
                for role in sorted(roles):
                    connection.execute(text(f"REVOKE ALL ON TABLE {name} FROM {role}"))
                sequence = connection.scalar(text("SELECT pg_get_serial_sequence(:name, 'id')"), {"name":table.name}) if "id" in table.c and table.c.id.type.python_type is int else None
                if sequence:
                    connection.execute(text(f"REVOKE ALL ON SEQUENCE {sequence} FROM PUBLIC"))
                    for role in sorted(roles):
                        connection.execute(text(f"REVOKE ALL ON SEQUENCE {sequence} FROM {role}"))


def verify_rollout(engine, approved_digest):
    missing = {table.name for table in TABLES} - set(inspect(engine).get_table_names())
    if missing or not approved_digest:
        raise RuntimeError("Phase A requires reviewed additive migration and entitlement manifest before rollout")
    with engine.connect() as connection:
        audit = access_models.EntitlementAudit
        if not connection.scalar(select(audit.id).where(audit.manifest_digest == approved_digest).limit(1)):
            raise RuntimeError("Reviewed Phase A entitlement manifest has not been applied")
        # Existing pre-Phase-A running assessments must finish before cutover.
        from app.models import MockAttemptQuestion
        delivery = access_models.AssessmentDelivery
        unbound = select(MockAttemptQuestion.attempt_id).where(~select(delivery.attempt_id).where(
            delivery.attempt_id == MockAttemptQuestion.attempt_id,
            delivery.question_id == MockAttemptQuestion.question_id).exists())
        if connection.scalar(select(MockAttempt.id).where(MockAttempt.status == "in_progress", MockAttempt.id.in_(unbound)).limit(1)):
            raise RuntimeError("Legacy active assessments must finish before Phase A cutover")
        if engine.dialect.name == "postgresql":
            for table in TABLES:
                rls = connection.scalar(text("SELECT relrowsecurity FROM pg_class WHERE oid = to_regclass(:name)"), {"name": table.name})
                if not rls:
                    raise RuntimeError("Phase A backend-only tables require RLS")
                for role in connection.scalars(text("SELECT rolname FROM pg_roles WHERE rolname IN ('anon','authenticated')")):
                    if connection.scalar(text("SELECT has_table_privilege(:role,:name,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')"), {"role":role,"name":table.name}):
                        raise RuntimeError("Phase A backend-only table has unexpected direct-client privileges")


def main():
    url = os.environ.get("PHASE_A_ADMIN_DATABASE_URL")
    if not url:
        raise SystemExit("PHASE_A_ADMIN_DATABASE_URL must be explicitly configured")
    engine = create_engine(normalize_database_url(url))
    migrate(engine)
    engine.dispose()
    print("Phase A additive schema installed; no learner grants created")


if __name__ == "__main__":
    main()
