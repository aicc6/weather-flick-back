"""add parent_id to reviews_recommend for replies

Revision ID: 47a4c5bb2a39
Revises: 8bd75104112b
Create Date: 2025-07-10 15:49:09.107547

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '47a4c5bb2a39'
down_revision: str | Sequence[str] | None = '8bd75104112b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'reviews_recommend',
        sa.Column('parent_id', sa.UUID(as_uuid=True), sa.ForeignKey('reviews_recommend.id'), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('reviews_recommend', 'parent_id')
