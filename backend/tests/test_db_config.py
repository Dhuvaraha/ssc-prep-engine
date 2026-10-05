from app.db import normalize_database_url


def test_normalizes_legacy_postgres_url():
    assert normalize_database_url("postgres://user:pass@host/db") == (
        "postgresql+psycopg://user:pass@host/db"
    )


def test_normalizes_standard_postgresql_url():
    assert normalize_database_url("postgresql://user:pass@host/db") == (
        "postgresql+psycopg://user:pass@host/db"
    )


def test_keeps_sqlite_url():
    assert normalize_database_url("sqlite:///./app.db") == "sqlite:///./app.db"
