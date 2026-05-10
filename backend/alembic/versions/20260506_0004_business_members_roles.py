"""add business members and public business ids

Revision ID: 20260506_0004
Revises: 20260504_0003
Create Date: 2026-05-06 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260506_0004"
down_revision: Union[str, None] = "20260504_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("global_role", sa.String(length=50), nullable=False, server_default="user"))
    op.add_column("businesses", sa.Column("public_business_id", sa.String(length=32), nullable=True))

    conn = op.get_bind()
    businesses = conn.execute(sa.text("SELECT id FROM businesses ORDER BY id")).fetchall()
    for row in businesses:
        public_id = f"BIZ-{row.id:06d}"
        conn.execute(
            sa.text("UPDATE businesses SET public_business_id = :public_id WHERE id = :business_id"),
            {"public_id": public_id, "business_id": row.id},
        )

    op.alter_column("businesses", "public_business_id", existing_type=sa.String(length=32), nullable=False)
    op.create_index("ix_businesses_public_business_id", "businesses", ["public_business_id"], unique=True)

    op.create_table(
        "business_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("invited_by_user_id", sa.Integer(), nullable=True),
        sa.Column("approved_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", "user_id", name="uq_business_members_business_user"),
    )
    op.create_index("ix_business_members_business_id", "business_members", ["business_id"], unique=False)
    op.create_index("ix_business_members_id", "business_members", ["id"], unique=False)
    op.create_index("ix_business_members_user_id", "business_members", ["user_id"], unique=False)

    conn.execute(
        sa.text(
            """
            INSERT INTO business_members
                (business_id, user_id, role, status, approved_by_user_id, created_at, updated_at)
            SELECT id, owner_id, 'owner', 'active', owner_id, now(), now()
            FROM businesses
            ON CONFLICT DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_business_members_user_id", table_name="business_members")
    op.drop_index("ix_business_members_id", table_name="business_members")
    op.drop_index("ix_business_members_business_id", table_name="business_members")
    op.drop_table("business_members")
    op.drop_index("ix_businesses_public_business_id", table_name="businesses")
    op.drop_column("businesses", "public_business_id")
    op.drop_column("users", "global_role")
