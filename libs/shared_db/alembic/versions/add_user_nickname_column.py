"""Add nickname column to users

Revision ID: add_user_nickname_column
Revises: 4536a6e293b9
Create Date: 2025-10-20 12:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_user_nickname_column"
down_revision = "4536a6e293b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add nullable nickname column to users table
    op.add_column("users", sa.Column("nickname", sa.String(), nullable=True))


def downgrade() -> None:
    # Remove nickname column
    op.drop_column("users", "nickname")
