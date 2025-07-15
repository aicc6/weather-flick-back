"""create reviews_recommend table

Revision ID: create_reviews_recommend
Revises: dc0742a94a4a
Create Date: 2025-01-13 08:15:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = 'create_reviews_recommend'
down_revision = 'dc0742a94a4a'
branch_labels = None
depends_on = None


def upgrade():
    # Create reviews_recommend table
    op.create_table('reviews_recommend',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('nickname', sa.String(length=50), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['reviews_recommend.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reviews_recommend_course_id'), 'reviews_recommend', ['course_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_reviews_recommend_course_id'), table_name='reviews_recommend')
    op.drop_table('reviews_recommend')
