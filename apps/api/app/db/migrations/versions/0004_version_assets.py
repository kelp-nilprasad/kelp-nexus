"""generic version assets: asset_path/name, content_type, media_kind

Lets a report version hold any uploaded file (html, pdf, video, ...), not just
HTML/PDF, and records how the frontend should view it.

Revision ID: 0004_version_assets
Revises: 0003_collection_parent
Create Date: 2026-07-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0004_version_assets"
down_revision = "0003_collection_parent"
branch_labels = None
depends_on = None

_NEW_COLS = {
    "asset_path": sa.String(600),
    "asset_name": sa.String(400),
    "content_type": sa.String(200),
    "media_kind": sa.String(20),
}


def upgrade() -> None:
    existing = {c["name"] for c in inspect(op.get_bind()).get_columns("report_versions")}
    for name, coltype in _NEW_COLS.items():
        if name not in existing:
            op.add_column("report_versions", sa.Column(name, coltype, nullable=True))


def downgrade() -> None:
    for name in _NEW_COLS:
        op.drop_column("report_versions", name)
