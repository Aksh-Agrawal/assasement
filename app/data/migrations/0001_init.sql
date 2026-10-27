CREATE TABLE schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT INTO schema_meta(key, value) VALUES
    ('schema_version', '0'),
    ('device_id', ''),
    ('created_at', strftime('%Y-%m-%dT%H:%M:%fZ', 'now'));

CREATE TABLE profiles (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL CHECK (length(trim(display_name)) > 0),
    server_user_id TEXT,
    pin_hash TEXT,
    pin_salt TEXT,
    created_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE question_sets (
    id TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version > 0),
    title TEXT NOT NULL,
    subject TEXT NOT NULL CHECK (subject IN ('Biology', 'Chemistry')),
    chapter TEXT NOT NULL,
    marking_json TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    downloaded_at TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 0 CHECK (is_active IN (0, 1)),
    PRIMARY KEY (id, version)
);

CREATE UNIQUE INDEX idx_question_sets_one_active
ON question_sets(id) WHERE is_active = 1;

CREATE TRIGGER question_sets_immutable_content
BEFORE UPDATE ON question_sets
WHEN OLD.id != NEW.id
  OR OLD.version != NEW.version
  OR OLD.title != NEW.title
  OR OLD.subject != NEW.subject
  OR OLD.chapter != NEW.chapter
  OR OLD.marking_json != NEW.marking_json
  OR OLD.content_hash != NEW.content_hash
  OR OLD.downloaded_at != NEW.downloaded_at
BEGIN
    SELECT RAISE(ABORT, 'question-set versions are immutable');
END;

CREATE TABLE questions (
    set_id TEXT NOT NULL,
    set_version INTEGER NOT NULL,
    id TEXT NOT NULL,
    position INTEGER NOT NULL CHECK (position > 0),
    topic TEXT NOT NULL,
    difficulty INTEGER NOT NULL CHECK (difficulty BETWEEN 1 AND 5),
    question_text TEXT NOT NULL,
    options_json TEXT NOT NULL,
    correct_key TEXT NOT NULL CHECK (correct_key IN ('A', 'B', 'C', 'D')),
    explanation TEXT,
    media_ref TEXT,
    PRIMARY KEY (set_id, set_version, id),
    UNIQUE (set_id, set_version, position),
    FOREIGN KEY (set_id, set_version)
        REFERENCES question_sets(id, version) ON DELETE RESTRICT
);

CREATE INDEX idx_questions_set_position
ON questions(set_id, set_version, position);

CREATE TABLE attempts (
    id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL,
    set_id TEXT NOT NULL,
    set_version INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('in_progress', 'completed', 'abandoned')),
    started_at TEXT NOT NULL,
    completed_at TEXT,
    duration_ms INTEGER NOT NULL DEFAULT 0 CHECK (duration_ms >= 0),
    score REAL,
    sync_status TEXT NOT NULL DEFAULT 'local'
        CHECK (sync_status IN ('local', 'pending', 'syncing', 'synced', 'failed')),
    sync_attempts INTEGER NOT NULL DEFAULT 0 CHECK (sync_attempts >= 0),
    last_sync_error TEXT,
    synced_at TEXT,
    FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE RESTRICT,
    FOREIGN KEY (set_id, set_version)
        REFERENCES question_sets(id, version) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX idx_attempts_one_in_progress_per_profile
ON attempts(profile_id) WHERE status = 'in_progress';

CREATE INDEX idx_attempts_status_sync
ON attempts(status, sync_status, started_at);

CREATE TABLE attempt_questions (
    attempt_id TEXT NOT NULL,
    position INTEGER NOT NULL CHECK (position > 0),
    question_id TEXT NOT NULL,
    PRIMARY KEY (attempt_id, position),
    UNIQUE (attempt_id, question_id),
    FOREIGN KEY (attempt_id) REFERENCES attempts(id) ON DELETE CASCADE
);

CREATE TABLE responses (
    id TEXT PRIMARY KEY,
    attempt_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    selected_key TEXT CHECK (selected_key IN ('A', 'B', 'C', 'D')),
    confidence TEXT CHECK (confidence IN ('sure', 'not_sure', 'guessing', 'unrated')),
    is_correct INTEGER CHECK (is_correct IS NULL OR is_correct IN (0, 1)),
    response_time_ms INTEGER NOT NULL DEFAULT 0 CHECK (response_time_ms >= 0),
    first_shown_at TEXT,
    answered_at TEXT,
    marked_review INTEGER NOT NULL DEFAULT 0 CHECK (marked_review IN (0, 1)),
    UNIQUE (attempt_id, question_id),
    FOREIGN KEY (attempt_id, question_id)
        REFERENCES attempt_questions(attempt_id, question_id) ON DELETE CASCADE,
    CHECK (
        (selected_key IS NULL AND confidence IS NULL)
        OR (selected_key IS NOT NULL AND confidence IS NOT NULL)
    )
);

CREATE INDEX idx_responses_attempt ON responses(attempt_id);

CREATE TABLE response_events (
    id TEXT PRIMARY KEY,
    attempt_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    value TEXT,
    at_ms INTEGER NOT NULL CHECK (at_ms >= 0),
    at_utc TEXT NOT NULL,
    FOREIGN KEY (attempt_id, question_id)
        REFERENCES attempt_questions(attempt_id, question_id) ON DELETE CASCADE
);

CREATE INDEX idx_response_events_attempt_question
ON response_events(attempt_id, question_id, at_ms, id);

CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
