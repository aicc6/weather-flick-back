"""add is_used column to email_verifications

Revision ID: f5dbf3ed9a01
Revises: 45373fac032f
Create Date: 2025-06-30 16:03:39.447318

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f5dbf3ed9a01'
down_revision: str | Sequence[str] | None = '45373fac032f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('email_verifications', sa.Column('is_used', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('email_verifications', 'is_used')
    # ### end Alembic commands ###
