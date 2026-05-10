"""add customer pending operator fields

Revision ID: 20260504_0003
Revises: 20260503_0002
Create Date: 2026-05-04 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260504_0003"
down_revision: Union[str, None] = "20260503_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("pending_operator_message", sa.Text(), nullable=True))
    op.add_column("customers", sa.Column("pending_operator_ai_reply", sa.Text(), nullable=True))
    op.add_column("customers", sa.Column("pending_operator_intent", sa.String(length=100), nullable=True))
    op.add_column("customers", sa.Column("pending_operator_confidence", sa.Numeric(5, 4), nullable=True))


def downgrade() -> None:
    op.drop_column("customers", "pending_operator_confidence")
    op.drop_column("customers", "pending_operator_intent")
    op.drop_column("customers", "pending_operator_ai_reply")
    op.drop_column("customers", "pending_operator_message")
