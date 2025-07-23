-- 여행 계획 즐겨찾기 테이블 생성
CREATE TABLE IF NOT EXISTS travel_plan_bookmarks (
    bookmark_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES travel_plans(plan_id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT _user_plan_bookmark_uc UNIQUE (user_id, plan_id)
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_travel_plan_bookmarks_user_id ON travel_plan_bookmarks(user_id);
CREATE INDEX IF NOT EXISTS idx_travel_plan_bookmarks_plan_id ON travel_plan_bookmarks(plan_id);

-- 테이블 코멘트
COMMENT ON TABLE travel_plan_bookmarks IS '여행 계획 즐겨찾기';
COMMENT ON COLUMN travel_plan_bookmarks.bookmark_id IS '즐겨찾기 ID';
COMMENT ON COLUMN travel_plan_bookmarks.user_id IS '사용자 ID';
COMMENT ON COLUMN travel_plan_bookmarks.plan_id IS '여행 계획 ID';
COMMENT ON COLUMN travel_plan_bookmarks.created_at IS '생성 일시';