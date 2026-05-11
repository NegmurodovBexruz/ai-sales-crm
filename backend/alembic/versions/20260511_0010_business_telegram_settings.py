"""add business telegram settings

Revision ID: 20260511_0010
Revises: 20260510_0009
Create Date: 2026-05-11 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260511_0010"
down_revision: Union[str, None] = "20260510_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("businesses", sa.Column("telegram_bot_token_encrypted", sa.Text(), nullable=True))
    op.add_column("businesses", sa.Column("telegram_webhook_secret", sa.String(length=255), nullable=True))
    op.add_column(
        "businesses",
        sa.Column("telegram_webhook_set", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("businesses", "telegram_webhook_set", server_default=None)


def downgrade() -> None:
    op.drop_column("businesses", "telegram_webhook_set")
    op.drop_column("businesses", "telegram_webhook_secret")
    op.drop_column("businesses", "telegram_bot_token_encrypted")
