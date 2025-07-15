"""Add is_public column to contact

Revision ID: 8e3ae7ff2fa5
Revises: d3175c1e235d
Create Date: 2025-07-15 10:55:25.708308

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8e3ae7ff2fa5'
down_revision: Union[str, Sequence[str], None] = 'd3175c1e235d'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('contact', sa.Column('is_public', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    op.drop_column('contact', 'is_public')
