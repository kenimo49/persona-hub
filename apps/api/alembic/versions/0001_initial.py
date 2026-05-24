"""Initial schema: personas, signals, source_api_keys, persona_access, handoff_jti.

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_api_keys",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column("name", sa.String(length=64), nullable=False, unique=True),
        sa.Column("key_prefix", sa.String(length=16), nullable=False, unique=True),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("allowed_profile_ids", sa.JSON(), nullable=False),
        sa.Column("disabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_source_api_keys_key_prefix",
        "source_api_keys",
        ["key_prefix"],
        unique=True,
    )

    op.create_table(
        "personas",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_by_api_key_id",
            sa.String(length=26),
            sa.ForeignKey("source_api_keys.id"),
            nullable=False,
        ),
    )

    op.create_table(
        "signals",
        sa.Column("id", sa.String(length=26), primary_key=True),
        sa.Column(
            "persona_id",
            sa.String(length=26),
            sa.ForeignKey("personas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("profile_id", sa.String(length=128), nullable=False),
        sa.Column("profile_version", sa.String(length=32), nullable=False),
        sa.Column("scoring_version", sa.String(length=32), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=True),
        sa.Column(
            "created_by_api_key_id",
            sa.String(length=26),
            sa.ForeignKey("source_api_keys.id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_signals_persona_id", "signals", ["persona_id"])

    op.create_table(
        "persona_access",
        sa.Column(
            "persona_id",
            sa.String(length=26),
            sa.ForeignKey("personas.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "api_key_id",
            sa.String(length=26),
            sa.ForeignKey("source_api_keys.id"),
            primary_key=True,
        ),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("granted_via", sa.String(length=32), nullable=False),
    )

    op.create_table(
        "handoff_jti",
        sa.Column("jti", sa.String(length=26), primary_key=True),
        sa.Column(
            "persona_id",
            sa.String(length=26),
            sa.ForeignKey("personas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "issued_by_api_key_id",
            sa.String(length=26),
            sa.ForeignKey("source_api_keys.id"),
            nullable=False,
        ),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "consumed_by_api_key_id",
            sa.String(length=26),
            sa.ForeignKey("source_api_keys.id"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("handoff_jti")
    op.drop_table("persona_access")
    op.drop_index("ix_signals_persona_id", table_name="signals")
    op.drop_table("signals")
    op.drop_table("personas")
    op.drop_index("ix_source_api_keys_key_prefix", table_name="source_api_keys")
    op.drop_table("source_api_keys")
