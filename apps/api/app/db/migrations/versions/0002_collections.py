"""collections + collection_reports

Revision ID: 0002_collections
Revises: 0001_initial
Create Date: 2026-06-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import UUID

revision = "0002_collections"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 0001's metadata create_all may already have created these (the Collection
    # model lives in Base.metadata), so guard each create to stay idempotent.
    existing = set(inspect(op.get_bind()).get_table_names())
    if "collections" in existing:
        return
    op.create_table(
        "collections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("slug", sa.String(180), nullable=False, unique=True, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "collection_reports",
        sa.Column("collection_id", UUID(as_uuid=True),
                  sa.ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("report_id", UUID(as_uuid=True),
                  sa.ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("collection_reports")
    op.drop_table("collections")
