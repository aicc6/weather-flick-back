"""
Revision ID: 20240711_add_user_id_to_travel_course_likes
Revises:
Create Date: 2024-07-11

"""
from alembic import op
import sqlalchemy as sa

revision = '20240711_add_user_id_to_travel_course_likes'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('travel_course_likes', sa.Column('user_id', sa.Integer(), nullable=False))
    op.create_index('ix_travel_course_likes_user_id', 'travel_course_likes', ['user_id'])
    # 필요시 ForeignKey 제약조건 추가 가능

def downgrade():
    op.drop_index('ix_travel_course_likes_user_id', 'travel_course_likes')
    op.drop_column('travel_course_likes', 'user_id')
