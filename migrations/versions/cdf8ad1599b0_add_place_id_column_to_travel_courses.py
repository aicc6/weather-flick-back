"""Add place_id column to travel_courses

Revision ID: cdf8ad1599b0
Revises: f4184722f9ae
Create Date: 2025-07-16 19:37:54.717333

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cdf8ad1599b0'
down_revision: Union[str, Sequence[str], None] = 'f4184722f9ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('travel_courses', sa.Column('place_id', sa.String(), nullable=True))
    op.create_index('ix_travel_courses_place_id', 'travel_courses', ['place_id'])


def downgrade() -> None:
    op.drop_index('ix_travel_courses_place_id', table_name='travel_courses')
    op.drop_column('travel_courses', 'place_id')
