"""Pytest fixtures.

Integration fixtures bind to the configured Postgres (the docker-compose `db`
service). If Postgres is unreachable the DB-dependent tests are skipped, so the
pure-unit suite (sanitization, JWT) still runs anywhere.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import create_access_token
from app.db.base import Base
from app.db import models  # noqa: F401
from app.db.models.user import Role, User
from app.db.session import get_db
from app.main import app


def _engine_or_skip():
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        pytest.skip("Postgres not reachable; skipping DB-backed tests")
    return engine


@pytest.fixture(scope="session")
def engine():
    engine = _engine_or_skip()
    with engine.begin() as conn:
        has_vector = conn.execute(
            text("SELECT 1 FROM pg_available_extensions WHERE name='vector'")
        ).first() is not None
        if has_vector:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    # Skip the embeddings table (vector column) when pgvector isn't installed.
    tables = [t for t in Base.metadata.sorted_tables if has_vector or t.name != "embeddings"]
    Base.metadata.create_all(bind=engine, tables=tables)
    yield engine


@pytest.fixture()
def db_session(engine):
    """Transactional fixture: each test runs in a rolled-back transaction."""
    connection = engine.connect()
    trans = connection.begin()
    TestingSession = sessionmaker(bind=connection, autoflush=False, autocommit=False)
    session = TestingSession()

    app.dependency_overrides[get_db] = lambda: session
    yield session

    session.close()
    trans.rollback()
    connection.close()
    app.dependency_overrides.clear()


@pytest.fixture()
def client(db_session):
    return TestClient(app)


@pytest.fixture()
def author(db_session) -> User:
    user = User(
        id=uuid.uuid4(), email=f"author-{uuid.uuid4().hex[:6]}@test.dev", name="Test Author",
        role=Role.author,
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture()
def auth_headers(author) -> dict:
    token = create_access_token(str(author.id), author.role.value)
    return {"Authorization": f"Bearer {token}"}
