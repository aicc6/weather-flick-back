"""add participants and transportation to travel_plans

Revision ID: 72710c00e558
Revises: fc6b86a4232f
Create Date: 2025-07-05 20:39:03.888349

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '72710c00e558'
down_revision: str | Sequence[str] | None = 'fc6b86a4232f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('travel_plans', sa.Column('participants', sa.Integer(), nullable=True))
    op.add_column('travel_plans', sa.Column('transportation', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('travel_plans', 'participants')
    op.drop_column('travel_plans', 'transportation')
