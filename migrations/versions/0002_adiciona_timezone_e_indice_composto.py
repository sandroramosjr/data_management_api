"""adiciona timezone nos timestamps e indice composto

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-29 23:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(),
            type_=sa.DateTime(timezone=True),
            existing_nullable=False,
            postgresql_using="created_at AT TIME ZONE 'UTC'",
        )
        batch_op.alter_column(
            "updated_at",
            existing_type=sa.DateTime(),
            type_=sa.DateTime(timezone=True),
            existing_nullable=False,
            postgresql_using="updated_at AT TIME ZONE 'UTC'",
        )
        batch_op.create_index("ix_products_category_price", ["category_id", "price"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.drop_index("ix_products_category_price")
        batch_op.alter_column(
            "updated_at",
            existing_type=sa.DateTime(timezone=True),
            type_=sa.DateTime(),
            existing_nullable=False,
            postgresql_using="updated_at AT TIME ZONE 'UTC'",
        )
        batch_op.alter_column(
            "created_at",
            existing_type=sa.DateTime(timezone=True),
            type_=sa.DateTime(),
            existing_nullable=False,
            postgresql_using="created_at AT TIME ZONE 'UTC'",
        )
