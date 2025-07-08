#!/usr/bin/env python3
"""
데이터베이스 스키마 확인 스크립트
"""
import os
import sys
from sqlalchemy import create_engine, text

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import settings

def check_tourist_attractions_schema():
    """tourist_attractions 테이블 스키마 확인"""
    try:
        # 데이터베이스 연결
        engine = create_engine(settings.database_url)

        with engine.connect() as connection:
            # 테이블 존재 여부 확인
            result = connection.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'tourist_attractions'
                );
            """))
            table_exists = result.scalar()

            if not table_exists:
                print("❌ tourist_attractions 테이블이 존재하지 않습니다.")
                return

            print("✅ tourist_attractions 테이블이 존재합니다.")

            # 컬럼 정보 조회
            result = connection.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = 'tourist_attractions'
                ORDER BY ordinal_position;
            """))

            columns = result.fetchall()
            print(f"\n📋 tourist_attractions 테이블 컬럼 목록 ({len(columns)}개):")
            print("-" * 80)
            print(f"{'컬럼명':<25} {'데이터타입':<15} {'NULL':<8} {'기본값'}")
            print("-" * 80)

            for column in columns:
                column_name = column[0]
                data_type = column[1]
                is_nullable = column[2]
                column_default = column[3] or ''

                print(f"{column_name:<25} {data_type:<15} {is_nullable:<8} {column_default}")

            # 샘플 데이터 확인
            result = connection.execute(text("""
                SELECT COUNT(*) as total_count
                FROM tourist_attractions;
            """))
            total_count = result.scalar()
            print(f"\n📊 총 레코드 수: {total_count:,}개")

            if total_count > 0:
                # 첫 번째 레코드 샘플
                result = connection.execute(text("""
                    SELECT * FROM tourist_attractions LIMIT 1;
                """))
                sample = result.fetchone()
                column_names = list(result.keys())

                print(f"\n🔍 첫 번째 레코드 샘플:")
                print("-" * 80)
                for i, column_name in enumerate(column_names):
                    value = sample[i]
                    if value is None:
                        value = "NULL"
                    elif isinstance(value, str) and len(value) > 50:
                        value = value[:50] + "..."
                    print(f"{column_name}: {value}")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    check_tourist_attractions_schema()
