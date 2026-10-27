"""Add immutable published question-pack catalog.

Revision ID: 20261019_03
Revises: 20261018_02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261019_03"
down_revision: str | None = "20261018_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "question_packs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("set_id", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("subject", sa.String(64), nullable=False),
        sa.Column("chapter", sa.String(200), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("question_count", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("set_id", "version", name="uq_question_packs_set_version"),
        sa.UniqueConstraint("storage_path", name="uq_question_packs_storage_path"),
    )
    op.create_index(
        "ix_question_packs_catalog",
        "question_packs",
        ["subject", "set_id", "version"],
    )


def downgrade() -> None:
    op.drop_index("ix_question_packs_catalog", table_name="question_packs")
    op.drop_table("question_packs")
