"""Add destination likes and saves tables

Revision ID: add_destination_likes_saves
Revises: 20250119_add_sharing_collaboration_tables
Create Date: 2025-01-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_destination_likes_saves'
down_revision = 'add_sharing_collaboration'
branch_labels = None
depends_on = None


def upgrade():
    # 여행지 좋아요 테이블 생성
    op.create_table('destination_likes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('destination_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['destination_id'], ['destinations.destination_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 유저별 여행지 중복 좋아요 방지를 위한 유니크 제약
    op.create_index('idx_unique_user_destination_like', 'destination_likes', ['user_id', 'destination_id'], unique=True)
    
    # 여행지 저장(북마크) 테이블 생성
    op.create_table('destination_saves',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('destination_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),  # 사용자가 메모를 남길 수 있도록
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['destination_id'], ['destinations.destination_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 유저별 여행지 중복 저장 방지를 위한 유니크 제약
    op.create_index('idx_unique_user_destination_save', 'destination_saves', ['user_id', 'destination_id'], unique=True)
    
    # 조회 성능 향상을 위한 인덱스
    op.create_index('idx_destination_likes_user', 'destination_likes', ['user_id'])
    op.create_index('idx_destination_likes_destination', 'destination_likes', ['destination_id'])
    op.create_index('idx_destination_saves_user', 'destination_saves', ['user_id'])
    op.create_index('idx_destination_saves_destination', 'destination_saves', ['destination_id'])


def downgrade():
    # 인덱스 삭제
    op.drop_index('idx_destination_saves_destination', table_name='destination_saves')
    op.drop_index('idx_destination_saves_user', table_name='destination_saves')
    op.drop_index('idx_destination_likes_destination', table_name='destination_likes')
    op.drop_index('idx_destination_likes_user', table_name='destination_likes')
    op.drop_index('idx_unique_user_destination_save', table_name='destination_saves')
    op.drop_index('idx_unique_user_destination_like', table_name='destination_likes')
    
    # 테이블 삭제
    op.drop_table('destination_saves')
    op.drop_table('destination_likes')