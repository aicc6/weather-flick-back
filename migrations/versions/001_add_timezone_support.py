"""Add timezone support to datetime fields

Revision ID: 001_timezone_support
Revises: 
Create Date: 2025-01-20 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_timezone_support'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Phase 1: Critical tables - users, travel_plans, weather_data
    기존 KST 시간을 UTC로 변환하여 저장
    """
    
    # =============================================================================
    # Phase 1: Critical Tables (즉시 적용 필요)
    # =============================================================================
    
    print("Phase 1: Critical tables 마이그레이션 시작...")
    
    # 1. users 테이블
    print("  - users 테이블 마이그레이션...")
    
    # created_at 필드를 timezone-aware로 변경
    op.execute("""
        ALTER TABLE users 
        ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE 
        USING created_at AT TIME ZONE 'Asia/Seoul' AT TIME ZONE 'UTC'
    """)
    
    # updated_at 필드를 timezone-aware로 변경
    op.execute("""
        ALTER TABLE users 
        ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE 
        USING updated_at AT TIME ZONE 'Asia/Seoul' AT TIME ZONE 'UTC'
    """)
    
    # 기본값을 UTC now()로 변경
    op.execute("""
        ALTER TABLE users 
        ALTER COLUMN created_at SET DEFAULT (NOW() AT TIME ZONE 'UTC'),
        ALTER COLUMN updated_at SET DEFAULT (NOW() AT TIME ZONE 'UTC')
    """)
    
    # 2. travel_plans 테이블
    print("  - travel_plans 테이블 마이그레이션...")
    
    op.execute("""
        ALTER TABLE travel_plans 
        ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE 
        USING created_at AT TIME ZONE 'Asia/Seoul' AT TIME ZONE 'UTC'
    """)
    
    op.execute("""
        ALTER TABLE travel_plans 
        ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE 
        USING updated_at AT TIME ZONE 'Asia/Seoul' AT TIME ZONE 'UTC'
    """)
    
    # start_date, end_date는 날짜 정보이므로 KST 유지
    op.execute("""
        ALTER TABLE travel_plans 
        ALTER COLUMN start_date TYPE TIMESTAMP WITH TIME ZONE 
        USING start_date AT TIME ZONE 'Asia/Seoul'
    """)
    
    op.execute("""
        ALTER TABLE travel_plans 
        ALTER COLUMN end_date TYPE TIMESTAMP WITH TIME ZONE 
        USING end_date AT TIME ZONE 'Asia/Seoul'
    """)
    
    # 3. weather_data 테이블
    print("  - weather_data 테이블 마이그레이션...")
    
    op.execute("""
        ALTER TABLE weather_data 
        ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE 
        USING created_at AT TIME ZONE 'Asia/Seoul' AT TIME ZONE 'UTC'
    """)
    
    op.execute("""
        ALTER TABLE weather_data 
        ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE 
        USING updated_at AT TIME ZONE 'Asia/Seoul' AT TIME ZONE 'UTC'
    """)
    
    # forecast_date는 예보 날짜이므로 KST 유지
    op.execute("""
        ALTER TABLE weather_data 
        ALTER COLUMN forecast_date TYPE TIMESTAMP WITH TIME ZONE 
        USING forecast_date AT TIME ZONE 'Asia/Seoul'
    """)
    
    print("Phase 1 완료: Critical tables")


def downgrade() -> None:
    """
    롤백: timezone-aware 필드를 다시 naive datetime으로 변경
    """
    
    print("Phase 1 롤백 시작...")
    
    # users 테이블 롤백
    op.execute("""
        ALTER TABLE users 
        ALTER COLUMN created_at TYPE TIMESTAMP 
        USING created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul'
    """)
    
    op.execute("""
        ALTER TABLE users 
        ALTER COLUMN updated_at TYPE TIMESTAMP 
        USING updated_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul'
    """)
    
    # travel_plans 테이블 롤백
    op.execute("""
        ALTER TABLE travel_plans 
        ALTER COLUMN created_at TYPE TIMESTAMP 
        USING created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul'
    """)
    
    op.execute("""
        ALTER TABLE travel_plans 
        ALTER COLUMN updated_at TYPE TIMESTAMP 
        USING updated_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul'
    """)
    
    op.execute("""
        ALTER TABLE travel_plans 
        ALTER COLUMN start_date TYPE TIMESTAMP 
        USING start_date AT TIME ZONE 'Asia/Seoul'
    """)
    
    op.execute("""
        ALTER TABLE travel_plans 
        ALTER COLUMN end_date TYPE TIMESTAMP 
        USING end_date AT TIME ZONE 'Asia/Seoul'
    """)
    
    # weather_data 테이블 롤백
    op.execute("""
        ALTER TABLE weather_data 
        ALTER COLUMN created_at TYPE TIMESTAMP 
        USING created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul'
    """)
    
    op.execute("""
        ALTER TABLE weather_data 
        ALTER COLUMN updated_at TYPE TIMESTAMP 
        USING updated_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul'
    """)
    
    op.execute("""
        ALTER TABLE weather_data 
        ALTER COLUMN forecast_date TYPE TIMESTAMP 
        USING forecast_date AT TIME ZONE 'Asia/Seoul'
    """)
    
    # 기본값을 원래대로 복원
    op.execute("""
        ALTER TABLE users 
        ALTER COLUMN created_at SET DEFAULT NOW(),
        ALTER COLUMN updated_at SET DEFAULT NOW()
    """)
    
    print("Phase 1 롤백 완료")