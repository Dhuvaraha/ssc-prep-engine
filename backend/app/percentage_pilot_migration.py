"""Explicit additive migration; production execution requires release approval."""
from sqlalchemy import text
from app.routers.percentage_pilot import PercentageProgress


def migrate(engine):
    with engine.begin() as connection:
        PercentageProgress.__table__.create(connection,checkfirst=True)
        if engine.dialect.name == 'postgresql':
            connection.execute(text('ALTER TABLE percentage_pilot_progress ENABLE ROW LEVEL SECURITY'))
            roles=list(connection.scalars(text("SELECT rolname FROM pg_roles WHERE rolname IN ('anon','authenticated')")))
            for role in ['PUBLIC',*roles]:
                connection.execute(text(f'REVOKE ALL ON percentage_pilot_progress FROM {role}'))
