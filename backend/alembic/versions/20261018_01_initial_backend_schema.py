"""Create Phase 9B attempt persistence schema.

Revision ID: 20261018_01
Revises: None
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261018_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_attempt_id", sa.Uuid(), nullable=False),
        sa.Column("payload_version", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.String(length=255), nullable=True),
        sa.Column("profile_id", sa.String(length=255), nullable=False),
        sa.Column("server_user_id", sa.String(length=255), nullable=True),
        sa.Column("question_set_id", sa.String(length=255), nullable=False),
        sa.Column("question_set_version", sa.Integer(), nullable=False),
        sa.Column("marking_correct", sa.Float(), nullable=False),
        sa.Column("marking_wrong", sa.Float(), nullable=False),
        sa.Column("marking_skip", sa.Float(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("device_attempt_id", name="uq_attempts_device_attempt_id"),
    )
    op.create_index("ix_attempts_profile_id", "attempts", ["profile_id"])
    op.create_index(
        "ix_attempts_question_set_id_version",
        "attempts",
        ["question_set_id", "question_set_version"],
    )
    op.create_index("ix_attempts_created_at", "attempts", ["created_at"])

    op.create_table(
        "attempt_responses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("attempt_id", sa.Integer(), nullable=False),
        sa.Column("device_response_id", sa.String(length=255), nullable=False),
        sa.Column("question_id", sa.String(length=255), nullable=False),
        sa.Column("selected_key", sa.String(length=1), nullable=True),
        sa.Column("confidence", sa.String(length=16), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("response_time_ms", sa.Integer(), nullable=False),
        sa.Column("marked_review", sa.Boolean(), nullable=False),
        sa.Column("first_shown_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["attempt_id"], ["attempts.id"], name="fk_attempt_responses_attempt_id", ondelete="RESTRICT"
        ),
        sa.UniqueConstraint(
            "attempt_id", "question_id", name="uq_attempt_responses_attempt_question"
        ),
    )


def downgrade() -> None:
    op.drop_table("attempt_responses")
    op.drop_index("ix_attempts_created_at", table_name="attempts")
    op.drop_index("ix_attempts_question_set_id_version", table_name="attempts")
    op.drop_index("ix_attempts_profile_id", table_name="attempts")
    op.drop_table("attempts")
