"""Explicit additive migration; never run automatically against production."""
from sqlalchemy import inspect, select, text
from app.db import Base
from app.revision_models import QuestionRevision, DeliveryRevision, EditorialCandidate, EditorialDecision, EditorialPublication, TeachingSupplement, SupplementReview
from app.access_models import AssessmentAsset
from app.models import Question, User

TABLES = [m.__table__ for m in (QuestionRevision, DeliveryRevision, EditorialCandidate, EditorialDecision, EditorialPublication, TeachingSupplement, SupplementReview)]
IMMUTABLE_TABLES = [*TABLES, AssessmentAsset.__table__]
LEGACY_DEPENDENCIES = {Question.__tablename__, User.__tablename__, AssessmentAsset.__tablename__}


def verify_capture_rollback(engine, *, capture_enabled):
    """This build cannot disable revision readers once delivery history exists."""
    if capture_enabled:
        return
    existing = set(inspect(engine).get_table_names())
    with engine.connect() as connection:
        for model in (DeliveryRevision, EditorialPublication):
            if model.__tablename__ not in existing:
                continue
            if engine.dialect.name == 'postgresql':
                visible = connection.scalar(text("""SELECT NOT c.relrowsecurity OR
                    r.rolsuper OR r.rolbypassrls OR
                    (NOT c.relforcerowsecurity AND pg_has_role(current_user,c.relowner,'USAGE'))
                    FROM pg_class c CROSS JOIN pg_roles r
                    WHERE c.oid=to_regclass(:name) AND r.rolname=current_user"""),
                    {'name': model.__tablename__})
                if not visible:
                    raise RuntimeError('Phase B rollback requires proven history visibility')
            if connection.execute(select(model.__table__).limit(1)).first() is not None:
                raise RuntimeError(
                    'Phase B history exists: keep revision capture enabled; '
                    'rollback requires a revision-compatible release'
                )


def migrate(engine):
    if LEGACY_DEPENDENCIES-set(inspect(engine).get_table_names()):
        raise RuntimeError('Phase B requires the existing legacy and Phase A schema')
    with engine.begin() as connection:
        Base.metadata.create_all(connection, tables=TABLES)
        if engine.dialect.name == 'postgresql':
            connection.execute(text("""CREATE OR REPLACE FUNCTION phase_b_immutable() RETURNS trigger
                LANGUAGE plpgsql SECURITY INVOKER AS $$ BEGIN
                RAISE EXCEPTION 'immutable Phase B evidence'; END $$"""))
            connection.execute(text('REVOKE ALL ON FUNCTION phase_b_immutable() FROM PUBLIC'))
            roles=list(connection.scalars(text("SELECT rolname FROM pg_roles WHERE rolname IN ('anon','authenticated')")))
            for table in IMMUTABLE_TABLES:
                name=table.name
                connection.execute(text(f'ALTER TABLE {name} ENABLE ROW LEVEL SECURITY'))
                for role in ['PUBLIC',*roles]:
                    connection.execute(text(f'REVOKE ALL ON TABLE {name} FROM {role}'))
                connection.execute(text(f'CREATE OR REPLACE TRIGGER phase_b_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON {name} FOR EACH STATEMENT EXECUTE FUNCTION phase_b_immutable()'))
        elif engine.dialect.name == 'sqlite':
            for table in TABLES:
                ddl=connection.scalar(text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:name"),{'name':table.name})
                if not ddl or 'WITHOUT ROWID' not in ddl.upper():
                    raise RuntimeError('Existing Phase B SQLite schema requires explicit compatibility migration')
            for table in IMMUTABLE_TABLES:
                name=table.name
                keys=' AND '.join(f'{c.name}=NEW.{c.name}' for c in table.primary_key.columns)
                if table is AssessmentAsset.__table__:
                    keys=f'({keys}) OR rowid=NEW.rowid'
                connection.execute(text(f"CREATE TRIGGER IF NOT EXISTS {name}_replace BEFORE INSERT ON {name} WHEN EXISTS(SELECT 1 FROM {name} WHERE {keys}) BEGIN SELECT RAISE(ABORT, 'immutable Phase B evidence'); END"))
                for op in ('UPDATE','DELETE'):
                    connection.execute(text(f"CREATE TRIGGER IF NOT EXISTS {name}_{op} BEFORE {op} ON {name} BEGIN SELECT RAISE(ABORT, 'immutable Phase B evidence'); END"))
        else:
            raise RuntimeError('Unsupported Phase B database')


def verify(engine):
    if engine.dialect.name not in {'postgresql','sqlite'}:
        raise RuntimeError('Unsupported Phase B database')
    if {t.name for t in TABLES}-set(inspect(engine).get_table_names()):
        raise RuntimeError('Phase B requires its reviewed additive migration')
    with engine.connect() as connection:
        for table in IMMUTABLE_TABLES:
            if engine.dialect.name=='postgresql':
                if not connection.scalar(text('SELECT relrowsecurity FROM pg_class WHERE oid=to_regclass(:name)'),{'name':table.name}):
                    raise RuntimeError('Phase B RLS is missing')
                if not connection.scalar(text("SELECT EXISTS(SELECT 1 FROM pg_trigger WHERE tgrelid=to_regclass(:name) AND tgname='phase_b_immutable' AND tgenabled='O' AND tgtype=58 AND tgfoid=to_regprocedure('phase_b_immutable()'))"),{'name':table.name}):
                    raise RuntimeError('Phase B immutable trigger missing')
                for privilege in ('SELECT','INSERT'):
                    if not connection.scalar(text('SELECT has_table_privilege(current_user,:name,:privilege)'),{'name':table.name,'privilege':privilege}):
                        raise RuntimeError('Backend role cannot read/write Phase B evidence')
                bypass=connection.scalar(text("""SELECT r.rolsuper OR r.rolbypassrls OR
                    (NOT c.relforcerowsecurity AND pg_has_role(current_user,c.relowner,'USAGE'))
                    FROM pg_class c CROSS JOIN pg_roles r WHERE c.oid=to_regclass(:name) AND r.rolname=current_user"""),{'name':table.name})
                if not bypass:
                    raise RuntimeError('Backend role requires a reviewed Phase B RLS access strategy')
                if connection.scalar(text("""SELECT EXISTS(SELECT 1 FROM pg_class c,
                    LATERAL aclexplode(coalesce(c.relacl,acldefault('r',c.relowner))) a
                    WHERE c.oid=to_regclass(:name) AND a.grantee=0)"""),{'name':table.name}):
                    raise RuntimeError('Phase B PUBLIC privileges must be revoked')
                roles=connection.scalars(text("SELECT rolname FROM pg_roles WHERE rolname IN ('anon','authenticated')")).all()
                for role in roles:
                    if connection.scalar(text("SELECT has_table_privilege(:role,:name,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')"),{'role':role,'name':table.name}):
                        raise RuntimeError('Phase B tables must remain backend-only')
            elif engine.dialect.name=='sqlite':
                if table in TABLES:
                    ddl=connection.scalar(text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:name"),{'name':table.name})
                    if not ddl or 'WITHOUT ROWID' not in ddl.upper():
                        raise RuntimeError('Phase B SQLite tables require WITHOUT ROWID')
                triggers=set(connection.scalars(text("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=:name"),{'name':table.name}))
                if not {table.name+s for s in ('_replace','_UPDATE','_DELETE')}<=triggers:
                    raise RuntimeError('Phase B immutable triggers missing')
