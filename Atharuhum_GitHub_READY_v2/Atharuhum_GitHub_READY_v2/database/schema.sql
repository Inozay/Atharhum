CREATE TABLE organizations (id UUID PRIMARY KEY, name TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE contents (id TEXT PRIMARY KEY, organization_id UUID, title TEXT NOT NULL, language TEXT, status TEXT, current_version TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE content_versions (id UUID PRIMARY KEY, content_id TEXT REFERENCES contents(id), version TEXT, source_id TEXT, sha256 TEXT, reviewer_id UUID, reviewed_at TIMESTAMPTZ);
CREATE TABLE sources (id TEXT PRIMARY KEY, title TEXT NOT NULL, source_type TEXT, url TEXT, language TEXT, license TEXT, verification_status TEXT, accessed_at TIMESTAMPTZ);
CREATE TABLE events (id UUID PRIMARY KEY, event_type TEXT NOT NULL, content_id TEXT, organization_id UUID, anonymous_session_id TEXT, language TEXT, country_aggregate TEXT, source_channel TEXT, campaign_id TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE learning_journeys (id UUID PRIMARY KEY, title TEXT NOT NULL, description TEXT);
CREATE TABLE journey_steps (id UUID PRIMARY KEY, journey_id UUID REFERENCES learning_journeys(id), position INT NOT NULL, title TEXT NOT NULL, content_id TEXT);
CREATE TABLE collaborations (id UUID PRIMARY KEY, from_org UUID, to_org UUID, content_id TEXT, status TEXT, created_at TIMESTAMPTZ DEFAULT now());
