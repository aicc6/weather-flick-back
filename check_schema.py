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

def check_accommodations_schema():
    """accommodations 테이블 스키마 확인"""
    try:
        # 데이터베이스 연결
        engine = create_engine(settings.database_url)

        with engine.connect() as connection:
            # 테이블 존재 여부 확인
            result = connection.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'accommodations'
                );
            """))
            table_exists = result.scalar()

            if not table_exists:
                print("❌ accommodations 테이블이 존재하지 않습니다.")
                return

            print("✅ accommodations 테이블이 존재합니다.")

            # 컬럼 정보 조회
            result = connection.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'accommodations'
                ORDER BY ordinal_position;
            """))

            print("\n📋 accommodations 테이블 스키마:")
            print("-" * 80)
            print(f"{'컬럼명':<30} {'타입':<20} {'NULL':<8} {'기본값'}")
            print("-" * 80)

            for row in result:
                column_name = row[0]
                data_type = row[1]
                is_nullable = row[2]
                default_value = row[3] or ''
                print(f"{column_name:<30} {data_type:<20} {is_nullable:<8} {default_value}")

            # 샘플 데이터 확인
            result = connection.execute(text("SELECT COUNT(*) FROM accommodations;"))
            count = result.scalar()
            print(f"\n📊 총 레코드 수: {count:,}개")

            if count and count > 0:
                result = connection.execute(text("SELECT * FROM accommodations LIMIT 1;"))
                sample = result.fetchone()
                if sample:
                    print(f"\n📝 샘플 데이터 (첫 번째 레코드):")
                    print("-" * 80)
                    keys = list(result.keys())
                    for idx, value in enumerate(sample):
                        print(f"{keys[idx]}: {value}")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    check_accommodations_schema()
