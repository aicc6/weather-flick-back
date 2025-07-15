"""add plan_type to travel_plans

Revision ID: add_plan_type_001
Revises: 
Create Date: 2025-01-13 20:00:00.000000

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = 'add_plan_type_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # plan_type 열 추가 (기본값: 'manual')
    op.add_column('travel_plans',
        sa.Column('plan_type', sa.String(50), nullable=True, server_default='manual')
    )

    # 기존 데이터 업데이트 - description을 기반으로 구분
    op.execute("""
        UPDATE travel_plans 
        SET plan_type = 'custom' 
        WHERE description LIKE '%여행 -%' 
           OR description LIKE '%맞춤%'
           OR title LIKE '%맞춤%'
    """)

    # 인덱스 추가
    op.create_index('idx_travel_plans_plan_type', 'travel_plans', ['plan_type'])


def downgrade():
    # 인덱스 제거
    op.drop_index('idx_travel_plans_plan_type', 'travel_plans')

    # 컬럼 제거
    op.drop_column('travel_plans', 'plan_type')
