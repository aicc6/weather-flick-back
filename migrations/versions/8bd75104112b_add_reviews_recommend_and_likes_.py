"""add reviews_recommend and likes_recommend tables

Revision ID: 8bd75104112b
Revises: 09a536f1e451
Create Date: 2025-07-10 13:47:06.616303

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8bd75104112b'
down_revision: Union[str, Sequence[str], None] = '09a536f1e451'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('likes_recommend',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('course_id', 'user_id', name='uq_likes_recommend_course_user')
    )
    op.create_index(op.f('ix_likes_recommend_course_id'), 'likes_recommend', ['course_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_likes_recommend_course_id'), table_name='likes_recommend')
    op.drop_table('likes_recommend')
