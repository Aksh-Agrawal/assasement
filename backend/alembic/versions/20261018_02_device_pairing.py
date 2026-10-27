"""Add device pairing and credential authentication.

Revision ID: 20261018_02
Revises: 20261018_01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261018_02"
down_revision: str | None = "20261018_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(255)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paired_at", sa.DateTime(timezone=True)),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("device_id", name="uq_devices_device_id"),
    )
    op.create_table(
        "pairing_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("claim_secret_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("code_hash", name="uq_pairing_sessions_code_hash"),
    )
    op.create_index("ix_pairing_sessions_code_hash", "pairing_sessions", ["code_hash"])
    op.create_table(
        "device_credentials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("credential_id", sa.String(64), nullable=False),
        sa.Column("secret_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("credential_id", name="uq_device_credentials_credential_id"),
    )
    op.create_index(
        "ix_device_credentials_credential_id", "device_credentials", ["credential_id"]
    )
    with op.batch_alter_table("attempts") as batch:
        batch.add_column(sa.Column("authenticated_device_id", sa.Integer()))
        batch.create_foreign_key(
            "fk_attempts_authenticated_device_id",
            "devices",
            ["authenticated_device_id"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    with op.batch_alter_table("attempts") as batch:
        batch.drop_constraint("fk_attempts_authenticated_device_id", type_="foreignkey")
        batch.drop_column("authenticated_device_id")
    op.drop_index("ix_device_credentials_credential_id", table_name="device_credentials")
    op.drop_table("device_credentials")
    op.drop_index("ix_pairing_sessions_code_hash", table_name="pairing_sessions")
    op.drop_table("pairing_sessions")
    op.drop_table("devices")
