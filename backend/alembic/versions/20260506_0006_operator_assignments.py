"""add operator assignments

Revision ID: 20260506_0006
Revises: 20260506_0005
Create Date: 2026-05-06 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260506_0006"
down_revision: Union[str, None] = "20260506_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "operator_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("operator_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["operator_id"], ["telegram_operators.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_operator_assignments_business_id", "operator_assignments", ["business_id"], unique=False)
    op.create_index("ix_operator_assignments_customer_id", "operator_assignments", ["customer_id"], unique=False)
    op.create_index("ix_operator_assignments_id", "operator_assignments", ["id"], unique=False)
    op.create_index("ix_operator_assignments_operator_id", "operator_assignments", ["operator_id"], unique=False)
    op.create_index("ix_operator_assignments_order_id", "operator_assignments", ["order_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_operator_assignments_order_id", table_name="operator_assignments")
    op.drop_index("ix_operator_assignments_operator_id", table_name="operator_assignments")
    op.drop_index("ix_operator_assignments_id", table_name="operator_assignments")
    op.drop_index("ix_operator_assignments_customer_id", table_name="operator_assignments")
    op.drop_index("ix_operator_assignments_business_id", table_name="operator_assignments")
    op.drop_table("operator_assignments")
