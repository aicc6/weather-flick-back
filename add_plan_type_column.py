from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # 컬럼이 이미 존재하는지 확인
    result = conn.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'travel_plans' AND column_name = 'plan_type'
    """))
    
    if not result.fetchone():
        # 컬럼 추가
        conn.execute(text("ALTER TABLE travel_plans ADD COLUMN plan_type VARCHAR(50) DEFAULT 'manual'"))
        conn.commit()
        print("Added plan_type column")
    else:
        print("plan_type column already exists")
    
    # 기존 데이터 업데이트
    conn.execute(text("""
        UPDATE travel_plans 
        SET plan_type = 'custom' 
        WHERE (description LIKE '%여행 -%' 
           OR description LIKE '%맞춤%'
           OR title LIKE '%맞춤%')
           AND plan_type = 'manual'
    """))
    conn.commit()
    
    # 인덱스 추가
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_travel_plans_plan_type ON travel_plans(plan_type)"))
    conn.commit()
    
    # 결과 확인
    result = conn.execute(text("SELECT plan_type, COUNT(*) FROM travel_plans GROUP BY plan_type"))
    for row in result:
        print(f"plan_type: {row[0]}, count: {row[1]}")
    
    print('Migration completed successfully!')