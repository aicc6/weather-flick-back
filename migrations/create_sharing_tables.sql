-- Create travel_plan_shares table
CREATE TABLE IF NOT EXISTS travel_plan_shares (
    share_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES travel_plans(plan_id),
    share_token VARCHAR(100) UNIQUE NOT NULL,
    permission VARCHAR(20) DEFAULT 'view',
    expires_at TIMESTAMP,
    max_uses INTEGER,
    use_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_by UUID NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_travel_plan_shares_share_id ON travel_plan_shares(share_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_travel_plan_shares_share_token ON travel_plan_shares(share_token);

-- Create travel_plan_versions table
CREATE TABLE IF NOT EXISTS travel_plan_versions (
    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES travel_plans(plan_id),
    version_number INTEGER NOT NULL,
    title VARCHAR(200),
    description TEXT,
    itinerary JSONB,
    change_description VARCHAR(500),
    created_by UUID NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_travel_plan_versions_version_id ON travel_plan_versions(version_id);

-- Create travel_plan_comments table
CREATE TABLE IF NOT EXISTS travel_plan_comments (
    comment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES travel_plans(plan_id),
    user_id UUID NOT NULL REFERENCES users(user_id),
    parent_comment_id UUID REFERENCES travel_plan_comments(comment_id),
    content TEXT NOT NULL,
    day_number INTEGER,
    place_index INTEGER,
    is_deleted BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_travel_plan_comments_comment_id ON travel_plan_comments(comment_id);

-- Create travel_plan_collaborators table
CREATE TABLE IF NOT EXISTS travel_plan_collaborators (
    id SERIAL PRIMARY KEY,
    plan_id UUID NOT NULL REFERENCES travel_plans(plan_id),
    user_id UUID NOT NULL REFERENCES users(user_id),
    permission VARCHAR(20) DEFAULT 'edit',
    invited_by UUID NOT NULL REFERENCES users(user_id),
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_viewed_at TIMESTAMP,
    UNIQUE(plan_id, user_id)
);

CREATE INDEX IF NOT EXISTS ix_travel_plan_collaborators_id ON travel_plan_collaborators(id);