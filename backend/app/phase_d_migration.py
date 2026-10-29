"""Additive Phase D schema only; no production execution or grants implied."""
from sqlalchemy import text
from app.routers.pilot_objectives import ObjectiveProgress


def migrate(engine):
    with engine.begin() as connection:
        ObjectiveProgress.__table__.create(connection,checkfirst=True)
        if engine.dialect.name=='postgresql':
            connection.execute(text('ALTER TABLE pilot_objective_progress ENABLE ROW LEVEL SECURITY'))
            roles=list(connection.scalars(text("SELECT rolname FROM pg_roles WHERE rolname IN ('anon','authenticated')")))
            for role in ['PUBLIC',*roles]:
                connection.execute(text(f'REVOKE ALL ON pilot_objective_progress FROM {role}'))
