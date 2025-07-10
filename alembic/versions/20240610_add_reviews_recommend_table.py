"""
create reviews_recommend table for recommend course comments
"""
from alembic import op
import sqlalchemy as sa
import uuid

revision = '20240610_add_reviews_recommend_table'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'reviews_recommend',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('course_id', sa.Integer(), nullable=False, index=True),
        sa.Column('user_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.user_id'), nullable=False),
        sa.Column('nickname', sa.String(50), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

def downgrade():
    op.drop_table('reviews_recommend')
