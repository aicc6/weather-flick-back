-- 여행 경로 테이블 스키마 업데이트 마이그레이션
-- 현재 DB 스키마와 ORM 모델을 일치시키기 위한 마이그레이션

-- 1. 기존 travel_routes 테이블 백업
CREATE TABLE travel_routes_backup AS SELECT * FROM travel_routes;

-- 2. 기존 travel_routes 테이블 삭제 (외래키 제약조건 때문에 주의 필요)
DROP TABLE IF EXISTS travel_routes CASCADE;

-- 3. ORM 모델에 맞는 새로운 travel_routes 테이블 생성
CREATE TABLE travel_routes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    travel_plan_id UUID NOT NULL REFERENCES travel_plans(plan_id) ON DELETE CASCADE,
    origin_place_id VARCHAR,
    destination_place_id VARCHAR,
    route_order INTEGER,
    transport_mode VARCHAR,
    duration_minutes INTEGER,
    distance_km FLOAT,
    route_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. 인덱스 생성
CREATE INDEX idx_travel_routes_plan_id ON travel_routes(travel_plan_id);
CREATE INDEX idx_travel_routes_order ON travel_routes(route_order);

-- 5. 업데이트 트리거 생성 (updated_at 자동 업데이트)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_travel_routes_updated_at 
    BEFORE UPDATE ON travel_routes 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 6. 기존 데이터 마이그레이션 (가능한 경우)
-- 주의: 기존 데이터 구조가 다르므로 수동으로 데이터 매핑 필요
-- INSERT INTO travel_routes (travel_plan_id, origin_place_id, destination_place_id, route_order, transport_mode, duration_minutes, distance_km, route_data, created_at, updated_at)
-- SELECT ... FROM travel_routes_backup WHERE ...;

COMMENT ON TABLE travel_routes IS '여행 경로 정보 테이블 - ORM 모델과 일치하도록 업데이트됨';