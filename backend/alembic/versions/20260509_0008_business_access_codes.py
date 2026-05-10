"""add business access codes

Revision ID: 20260509_0008
Revises: 20260508_0007
Create Date: 2026-05-09 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260509_0008"
down_revision: Union[str, None] = "20260508_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("businesses", sa.Column("admin_join_code", sa.String(length=32), nullable=True))
    op.add_column("businesses", sa.Column("operator_code", sa.String(length=32), nullable=True))
    op.create_index("ix_businesses_admin_join_code", "businesses", ["admin_join_code"], unique=True)
    op.create_index("ix_businesses_operator_code", "businesses", ["operator_code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_businesses_operator_code", table_name="businesses")
    op.drop_index("ix_businesses_admin_join_code", table_name="businesses")
    op.drop_column("businesses", "operator_code")
    op.drop_column("businesses", "admin_join_code")
