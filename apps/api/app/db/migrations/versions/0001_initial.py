"""initial schema + FTS trigger + pgvector

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-29

This initial revision provisions the pgvector extension, materializes every
table from the SQLAlchemy metadata, then installs the full-text-search trigger
and supporting indexes. Subsequent migrations should use normal autogenerate.
"""
from alembic import op
from sqlalchemy import text

from app.db.base import Base
from app.db import models  # noqa: F401  (populate Base.metadata)

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


FTS_TRIGGER = """
CREATE OR REPLACE FUNCTION reports_search_vector_update() RETURNS trigger AS $$
BEGIN
  NEW.search_vector :=
    setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(NEW.summary, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(NEW.description, '')), 'C') ||
    setweight(to_tsvector('english', coalesce(NEW.project, '')), 'D') ||
    setweight(to_tsvector('english', coalesce(NEW.content_text, '')), 'D');
  RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER reports_search_vector_trigger
BEFORE INSERT OR UPDATE OF title, summary, description, project, content_text ON reports
FOR EACH ROW EXECUTE FUNCTION reports_search_vector_update();
"""


def _has_pgvector(bind) -> bool:
    return (
        bind.execute(
            text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
        ).first()
        is not None
    )


def _tables(bind):
    """All tables, minus `embeddings` when pgvector is unavailable."""
    has_vector = _has_pgvector(bind)
    return [t for t in Base.metadata.sorted_tables if has_vector or t.name != "embeddings"]


def upgrade() -> None:
    bind = op.get_bind()
    has_vector = _has_pgvector(bind)
    if has_vector:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # Create every table; skip `embeddings` (vector column) when pgvector is absent.
    Base.metadata.create_all(bind=bind, tables=_tables(bind))
    op.execute("CREATE INDEX IF NOT EXISTS ix_reports_search_vector ON reports USING GIN (search_vector)")
    op.execute(FTS_TRIGGER)
    if has_vector:
        # Approximate-nearest-neighbour index for semantic search (AI phase).
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_embeddings_vector ON embeddings "
            "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
        )


def downgrade() -> None:
    bind = op.get_bind()
    op.execute("DROP TRIGGER IF EXISTS reports_search_vector_trigger ON reports")
    op.execute("DROP FUNCTION IF EXISTS reports_search_vector_update")
    Base.metadata.drop_all(bind=bind, tables=_tables(bind))
