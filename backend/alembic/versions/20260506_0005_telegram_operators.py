"""add telegram operators

Revision ID: 20260506_0005
Revises: 20260506_0004
Create Date: 2026-05-06 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260506_0005"
down_revision: Union[str, None] = "20260506_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "telegram_operators",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("telegram_chat_id", sa.String(length=100), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", "telegram_chat_id", name="uq_telegram_operators_business_chat"),
    )
    op.create_index("ix_telegram_operators_business_id", "telegram_operators", ["business_id"], unique=False)
    op.create_index("ix_telegram_operators_id", "telegram_operators", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_telegram_operators_id", table_name="telegram_operators")
    op.drop_index("ix_telegram_operators_business_id", table_name="telegram_operators")
    op.drop_table("telegram_operators")
