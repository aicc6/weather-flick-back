"""add review_likes table for review like/dislike

Revision ID: 8831066fc75a
Revises: 47a4c5bb2a39
Create Date: 2025-07-10 16:20:45.700022

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '8831066fc75a'
down_revision: str | Sequence[str] | None = '47a4c5bb2a39'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'review_likes',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('review_id', sa.UUID(as_uuid=True), sa.ForeignKey('reviews_recommend.id'), nullable=False, index=True),
        sa.Column('user_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.user_id'), nullable=False),
        sa.Column('is_like', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('review_id', 'user_id', 'is_like', name='uq_review_like_user_type'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('review_likes')
