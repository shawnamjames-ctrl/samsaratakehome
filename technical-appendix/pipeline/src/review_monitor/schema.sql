PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS apps (
    app_key TEXT PRIMARY KEY,
    app_name TEXT NOT NULL,
    source_platform TEXT NOT NULL CHECK (source_platform IN ('apple_app_store', 'google_play')),
    store_app_id TEXT NOT NULL,
    territory TEXT NOT NULL,
    requested_language TEXT NOT NULL,
    source_url TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    UNIQUE (source_platform, store_app_id, territory, requested_language)
);

CREATE TABLE IF NOT EXISTS pull_runs (
    run_id TEXT PRIMARY KEY,
    app_key TEXT NOT NULL REFERENCES apps(app_key),
    mode TEXT NOT NULL CHECK (mode IN ('backfill', 'daily', 'reconcile')),
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
    request_parameters TEXT NOT NULL,
    raw_snapshot_path TEXT,
    records_received INTEGER,
    parser_version TEXT NOT NULL,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS reviews (
    review_key TEXT PRIMARY KEY,
    app_key TEXT NOT NULL REFERENCES apps(app_key),
    source_platform TEXT NOT NULL,
    store_app_id TEXT NOT NULL,
    territory TEXT NOT NULL,
    requested_language TEXT NOT NULL,
    source_review_id TEXT NOT NULL,
    source_url TEXT,
    reviewer_display_name TEXT,
    title TEXT,
    body TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review_timestamp TEXT NOT NULL,
    app_version TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    currently_visible INTEGER NOT NULL DEFAULT 1 CHECK (currently_visible IN (0, 1)),
    UNIQUE (app_key, source_review_id)
);

CREATE TABLE IF NOT EXISTS review_observations (
    review_key TEXT NOT NULL REFERENCES reviews(review_key),
    observed_at TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    content_hash TEXT NOT NULL,
    helpful_count INTEGER,
    legacy_vote_count INTEGER,
    legacy_vote_sum INTEGER,
    developer_reply_present INTEGER NOT NULL CHECK (developer_reply_present IN (0, 1)),
    developer_reply_hash TEXT,
    developer_reply_timestamp TEXT,
    currently_visible INTEGER NOT NULL CHECK (currently_visible IN (0, 1)),
    PRIMARY KEY (review_key, observed_at)
);

CREATE TABLE IF NOT EXISTS developer_responses (
    review_key TEXT NOT NULL REFERENCES reviews(review_key),
    response_hash TEXT NOT NULL,
    response_text TEXT NOT NULL,
    response_timestamp TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    PRIMARY KEY (review_key, response_hash)
);

CREATE TABLE IF NOT EXISTS app_snapshots (
    app_key TEXT NOT NULL REFERENCES apps(app_key),
    observed_at TEXT NOT NULL,
    average_rating REAL,
    ratings_count INTEGER,
    written_reviews_count INTEGER,
    rating_1_count INTEGER,
    rating_2_count INTEGER,
    rating_3_count INTEGER,
    rating_4_count INTEGER,
    rating_5_count INTEGER,
    current_version TEXT,
    store_updated_at TEXT,
    minimum_os TEXT,
    install_min INTEGER,
    install_max INTEGER,
    app_size_bytes INTEGER,
    PRIMARY KEY (app_key, observed_at)
);

CREATE TABLE IF NOT EXISTS releases (
    app_key TEXT NOT NULL REFERENCES apps(app_key),
    version TEXT NOT NULL,
    release_timestamp TEXT,
    release_notes TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    PRIMARY KEY (app_key, version)
);

CREATE TABLE IF NOT EXISTS classifications (
    review_key TEXT NOT NULL REFERENCES reviews(review_key),
    classification_type TEXT NOT NULL,
    classification_value TEXT NOT NULL,
    confidence REAL,
    evidence_span TEXT,
    method TEXT NOT NULL,
    model_or_rule_version TEXT NOT NULL,
    taxonomy_version TEXT NOT NULL,
    classified_at TEXT NOT NULL,
    PRIMARY KEY (
        review_key,
        classification_type,
        classification_value,
        model_or_rule_version,
        taxonomy_version
    )
);

CREATE INDEX IF NOT EXISTS idx_reviews_app_date ON reviews(app_key, review_timestamp);
CREATE INDEX IF NOT EXISTS idx_reviews_platform ON reviews(source_platform);
CREATE INDEX IF NOT EXISTS idx_reviews_rating ON reviews(rating);
CREATE INDEX IF NOT EXISTS idx_reviews_version ON reviews(app_key, app_version);
CREATE INDEX IF NOT EXISTS idx_observations_time ON review_observations(observed_at);

CREATE TABLE IF NOT EXISTS monitoring_review_decisions (
    review_key TEXT NOT NULL REFERENCES reviews(review_key),
    content_hash TEXT NOT NULL,
    decision_status TEXT NOT NULL CHECK (decision_status IN ('matched_existing', 'residual', 'confirmed_no_theme')),
    confidence REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    method TEXT NOT NULL,
    classifier_version TEXT NOT NULL,
    human_review_required INTEGER NOT NULL CHECK (human_review_required IN (0, 1)),
    decided_at TEXT NOT NULL,
    PRIMARY KEY (review_key, content_hash)
);

CREATE TABLE IF NOT EXISTS monitoring_theme_assignments (
    review_key TEXT NOT NULL REFERENCES reviews(review_key),
    content_hash TEXT NOT NULL,
    theme_id TEXT NOT NULL,
    assignment_status TEXT NOT NULL CHECK (assignment_status IN ('approved_seed', 'provisional_rule', 'human_approved', 'dismissed')),
    confidence REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    method TEXT NOT NULL,
    classifier_version TEXT NOT NULL,
    assigned_at TEXT NOT NULL,
    PRIMARY KEY (review_key, content_hash, theme_id)
);

CREATE TABLE IF NOT EXISTS monitoring_candidate_clusters (
    candidate_id TEXT PRIMARY KEY,
    product TEXT NOT NULL CHECK (product IN ('Driver', 'Fleet')),
    platform TEXT NOT NULL CHECK (platform IN ('All', 'Android', 'iOS')),
    signature_hash TEXT NOT NULL,
    support_count INTEGER NOT NULL CHECK (support_count > 0),
    first_review_at TEXT NOT NULL,
    latest_review_at TEXT NOT NULL,
    average_rating REAL NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('candidate', 'confirmed', 'dismissed')),
    human_review_required INTEGER NOT NULL CHECK (human_review_required IN (0, 1)),
    generated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_monitoring_assignments_theme ON monitoring_theme_assignments(theme_id, assignment_status);
CREATE INDEX IF NOT EXISTS idx_monitoring_decisions_status ON monitoring_review_decisions(decision_status, human_review_required);

CREATE VIEW IF NOT EXISTS review_analysis_base AS
SELECT
    r.review_key,
    r.app_key,
    a.app_name,
    r.source_platform,
    r.store_app_id,
    r.territory,
    r.requested_language,
    r.source_review_id,
    r.source_url,
    r.reviewer_display_name,
    r.title,
    r.body,
    r.rating,
    r.review_timestamp,
    r.app_version,
    r.first_seen_at,
    r.last_seen_at,
    r.currently_visible
FROM reviews AS r
JOIN apps AS a USING (app_key);

CREATE VIEW IF NOT EXISTS latest_review_observations AS
SELECT
    review_key,
    observed_at,
    rating,
    content_hash,
    helpful_count,
    legacy_vote_count,
    legacy_vote_sum,
    developer_reply_present,
    developer_reply_hash,
    developer_reply_timestamp,
    currently_visible
FROM (
    SELECT
        o.*,
        ROW_NUMBER() OVER (PARTITION BY review_key ORDER BY observed_at DESC) AS row_number
    FROM review_observations AS o
)
WHERE row_number = 1;

CREATE VIEW IF NOT EXISTS review_analysis_current AS
SELECT
    b.*,
    o.observed_at AS latest_observed_at,
    o.helpful_count,
    o.legacy_vote_count,
    o.legacy_vote_sum,
    o.developer_reply_present,
    o.developer_reply_timestamp
FROM review_analysis_base AS b
LEFT JOIN latest_review_observations AS o USING (review_key);

CREATE VIEW IF NOT EXISTS latest_app_snapshots AS
SELECT
    app_key,
    observed_at,
    average_rating,
    ratings_count,
    written_reviews_count,
    rating_1_count,
    rating_2_count,
    rating_3_count,
    rating_4_count,
    rating_5_count,
    current_version,
    store_updated_at,
    minimum_os,
    install_min,
    install_max,
    app_size_bytes
FROM (
    SELECT
        s.*,
        ROW_NUMBER() OVER (PARTITION BY app_key ORDER BY observed_at DESC) AS row_number
    FROM app_snapshots AS s
)
WHERE row_number = 1;
