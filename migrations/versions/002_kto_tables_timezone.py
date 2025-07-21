"""Add timezone support to KTO data tables

Revision ID: 002_kto_timezone
Revises: 001_timezone_support
Create Date: 2025-01-20 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_kto_timezone'
down_revision: Union[str, None] = '001_timezone_support'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Phase 2: KTO 데이터 테이블들에 타임존 지원 추가
    destinations, attractions, accommodations, restaurants, cultural_facilities, leisure_sports
    """
    
    print("Phase 2: KTO 데이터 테이블 마이그레이션 시작...")
    
    # KTO 데이터 테이블 목록
    kto_tables = [
        'destinations',
        'attractions', 
        'accommodations',
        'restaurants',
        'cultural_facilities',
        'leisure_sports',
        'recommend_reviews'
    ]
    
    for table_name in kto_tables:
        print(f"  - {table_name} 테이블 마이그레이션...")
        
        # created_at 필드가 있는지 확인하고 변경
        try:
            op.execute(f"""
                ALTER TABLE {table_name} 
                ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE 
                USING created_at AT TIME ZONE 'Asia/Seoul' AT TIME ZONE 'UTC'
            """)
        except Exception as e:
            print(f"    Warning: {table_name}.created_at 필드 처리 중 오류: {e}")
        
        # updated_at 필드가 있는지 확인하고 변경
        try:
            op.execute(f"""
                ALTER TABLE {table_name} 
                ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE 
                USING updated_at AT TIME ZONE 'Asia/Seoul' AT TIME ZONE 'UTC'
            """)
        except Exception as e:
            print(f"    Warning: {table_name}.updated_at 필드 처리 중 오류: {e}")
        
        # last_sync_at 필드가 있는 경우 변경 (destinations 테이블)
        if table_name == 'destinations':
            try:
                op.execute(f"""
                    ALTER TABLE {table_name} 
                    ALTER COLUMN last_sync_at TYPE TIMESTAMP WITH TIME ZONE 
                    USING last_sync_at AT TIME ZONE 'Asia/Seoul' AT TIME ZONE 'UTC'
                """)
            except Exception as e:
                print(f"    Warning: {table_name}.last_sync_at 필드 처리 중 오류: {e}")
    
    # =============================================================================
    # 사용자 활동 관련 테이블 처리
    # =============================================================================
    
    # user_activity_logs 테이블
    print("  - user_activity_logs 테이블 마이그레이션...")
    try:
        op.execute("""
            ALTER TABLE user_activity_logs 
            ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE 
            USING created_at AT TIME ZONE 'UTC'
        """)
    except Exception as e:
        print(f"    Warning: user_activity_logs.created_at 필드 처리 중 오류: {e}")
    
    # review_likes 테이블
    print("  - review_likes 테이블 마이그레이션...")
    try:
        op.execute("""
            ALTER TABLE review_likes 
            ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE 
            USING created_at AT TIME ZONE 'Asia/Seoul' AT TIME ZONE 'UTC'
        """)
    except Exception as e:
        print(f"    Warning: review_likes.created_at 필드 처리 중 오류: {e}")
    
    print("Phase 2 완료: KTO 데이터 테이블")


def downgrade() -> None:
    """
    롤백: KTO 테이블들의 timezone-aware 필드를 다시 naive datetime으로 변경
    """
    
    print("Phase 2 롤백 시작...")
    
    kto_tables = [
        'destinations',
        'attractions', 
        'accommodations',
        'restaurants',
        'cultural_facilities',
        'leisure_sports',
        'recommend_reviews',
        'user_activity_logs',
        'review_likes'
    ]
    
    for table_name in kto_tables:
        print(f"  - {table_name} 테이블 롤백...")
        
        # created_at 롤백
        try:
            if table_name == 'user_activity_logs':
                # user_activity_logs는 이미 UTC로 저장되어 있음
                op.execute(f"""
                    ALTER TABLE {table_name} 
                    ALTER COLUMN created_at TYPE TIMESTAMP 
                    USING created_at AT TIME ZONE 'UTC'
                """)
            else:
                op.execute(f"""
                    ALTER TABLE {table_name} 
                    ALTER COLUMN created_at TYPE TIMESTAMP 
                    USING created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul'
                """)
        except Exception as e:
            print(f"    Warning: {table_name}.created_at 롤백 중 오류: {e}")
        
        # updated_at 롤백
        try:
            op.execute(f"""
                ALTER TABLE {table_name} 
                ALTER COLUMN updated_at TYPE TIMESTAMP 
                USING updated_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul'
            """)
        except Exception as e:
            print(f"    Warning: {table_name}.updated_at 롤백 중 오류: {e}")
        
        # destinations 테이블의 last_sync_at 롤백
        if table_name == 'destinations':
            try:
                op.execute(f"""
                    ALTER TABLE {table_name} 
                    ALTER COLUMN last_sync_at TYPE TIMESTAMP 
                    USING last_sync_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Seoul'
                """)
            except Exception as e:
                print(f"    Warning: {table_name}.last_sync_at 롤백 중 오류: {e}")
    
    print("Phase 2 롤백 완료")