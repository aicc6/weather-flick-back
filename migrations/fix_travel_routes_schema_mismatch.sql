-- TravelRoute 테이블 스키마 불일치 해결 마이그레이션
-- 데이터베이스 스키마를 ORM 모델과 일치시키기 위한 마이그레이션

-- 1. 기존 travel_routes 테이블 백업 생성
CREATE TABLE travel_routes_backup_$(date +%Y%m%d) AS 
SELECT * FROM travel_routes;

-- 2. 기존 테이블의 제약조건 및 인덱스 확인
-- 필요시 드롭할 외래키 제약조건들을 먼저 찾습니다
SELECT 
    tc.constraint_name, 
    tc.table_name, 
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name 
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' 
    AND tc.table_name='travel_routes';

-- 3. 기존 transportation_details 테이블의 외래키 제약조건 임시 삭제
-- (travel_routes를 참조하는 테이블이 있다면)
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (
        SELECT constraint_name, table_name 
        FROM information_schema.table_constraints 
        WHERE constraint_type = 'FOREIGN KEY' 
        AND constraint_name LIKE '%travel_routes%'
    ) LOOP
        EXECUTE 'ALTER TABLE ' || r.table_name || ' DROP CONSTRAINT IF EXISTS ' || r.constraint_name;
    END LOOP;
END $$;

-- 4. 기존 travel_routes 테이블 삭제
DROP TABLE IF EXISTS travel_routes CASCADE;

-- 5. ORM 모델에 맞는 새로운 travel_routes 테이블 생성
CREATE TABLE travel_routes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    travel_plan_id UUID NOT NULL,
    origin_place_id VARCHAR,
    destination_place_id VARCHAR,
    route_order INTEGER,
    transport_mode VARCHAR,
    duration_minutes INTEGER,
    distance_km FLOAT,
    route_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 외래키 제약조건
    CONSTRAINT fk_travel_routes_plan 
        FOREIGN KEY (travel_plan_id) 
        REFERENCES travel_plans(plan_id) 
        ON DELETE CASCADE
);

-- 6. 인덱스 생성
CREATE INDEX idx_travel_routes_plan_id ON travel_routes(travel_plan_id);
CREATE INDEX idx_travel_routes_order ON travel_routes(route_order);

-- 7. updated_at 자동 업데이트 트리거 생성
CREATE OR REPLACE FUNCTION update_travel_routes_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_travel_routes_updated_at 
    BEFORE UPDATE ON travel_routes 
    FOR EACH ROW 
    EXECUTE FUNCTION update_travel_routes_updated_at();

-- 8. transportation_details 테이블 외래키 복원
-- (id 컬럼명 변경에 따른 수정 필요)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'transportation_details') THEN
        -- transportation_details 테이블의 외래키 컬럼명 확인 및 수정 필요
        -- route_id -> travel_route_id로 변경되었을 수 있음
        ALTER TABLE transportation_details 
        ADD CONSTRAINT fk_transportation_details_route 
        FOREIGN KEY (travel_route_id) 
        REFERENCES travel_routes(id) 
        ON DELETE CASCADE;
    END IF;
END $$;

-- 9. 기존 데이터 마이그레이션 (수동으로 조정 필요)
-- 주의: 데이터 구조가 다르므로 실제 데이터 매핑은 수동으로 확인 후 실행
/*
-- 예시 (실제 데이터 구조에 따라 조정 필요):
INSERT INTO travel_routes (
    travel_plan_id, 
    origin_place_id, 
    destination_place_id, 
    route_order, 
    transport_mode, 
    duration_minutes, 
    distance_km, 
    route_data,
    created_at, 
    updated_at
)
SELECT 
    travel_plan_id,
    origin_place_id,
    destination_place_id, 
    route_order,
    transport_mode,
    duration_minutes,
    distance_km,
    route_data,
    created_at,
    updated_at
FROM travel_routes_backup_$(date +%Y%m%d)
WHERE travel_plan_id IS NOT NULL;
*/

-- 10. 테이블 코멘트 추가
COMMENT ON TABLE travel_routes IS '여행 경로 정보 테이블 - ORM 모델과 일치하도록 업데이트됨';
COMMENT ON COLUMN travel_routes.id IS '여행 경로 고유 ID (UUID)';
COMMENT ON COLUMN travel_routes.travel_plan_id IS '여행 계획 ID (UUID)';
COMMENT ON COLUMN travel_routes.origin_place_id IS '출발지 ID';
COMMENT ON COLUMN travel_routes.destination_place_id IS '도착지 ID';
COMMENT ON COLUMN travel_routes.route_order IS '경로 순서';
COMMENT ON COLUMN travel_routes.transport_mode IS '교통수단 (walk, car, transit 등)';
COMMENT ON COLUMN travel_routes.duration_minutes IS '소요 시간 (분)';
COMMENT ON COLUMN travel_routes.distance_km IS '거리 (킬로미터)';
COMMENT ON COLUMN travel_routes.route_data IS '상세 경로 정보 (JSON)';

-- 11. 권한 설정 (필요시)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON travel_routes TO your_app_user;

COMMIT;