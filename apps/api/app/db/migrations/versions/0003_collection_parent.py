"""nested collections: collections.parent_id

Revision ID: 0003_collection_parent
Revises: 0002_collections
Create Date: 2026-06-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import UUID

revision = "0003_collection_parent"
down_revision = "0002_collections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    cols = {c["name"] for c in inspect(op.get_bind()).get_columns("collections")}
    if "parent_id" in cols:
        return
    op.add_column(
        "collections",
        sa.Column(
            "parent_id", UUID(as_uuid=True),
            sa.ForeignKey("collections.id", ondelete="CASCADE"), nullable=True,
        ),
    )
    op.create_index("ix_collections_parent_id", "collections", ["parent_id"])


def downgrade() -> None:
    op.drop_index("ix_collections_parent_id", table_name="collections")
    op.drop_column("collections", "parent_id")
