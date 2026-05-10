"""add customer telegram uniqueness

Revision ID: 20260503_0002
Revises: 20260503_0001
Create Date: 2026-05-03
"""
from typing import Sequence, Union

from alembic import op

revision: str = "20260503_0002"
down_revision: Union[str, None] = "20260503_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_customers_business_telegram_user",
        "customers",
        ["business_id", "telegram_user_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_customers_business_telegram_user",
        "customers",
        type_="unique",
    )

