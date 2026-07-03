"""users.msal_token_cache for delegated Graph (SharePoint) tokens

Revision ID: 0005_user_msal_cache
Revises: 0004_version_assets
Create Date: 2026-07-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0005_user_msal_cache"
down_revision = "0004_version_assets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = {c["name"] for c in inspect(op.get_bind()).get_columns("users")}
    if "msal_token_cache" not in existing:
        op.add_column("users", sa.Column("msal_token_cache", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "msal_token_cache")
