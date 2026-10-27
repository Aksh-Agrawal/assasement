ALTER TABLE attempts ADD COLUMN next_sync_at TEXT;
ALTER TABLE attempts ADD COLUMN sync_started_at TEXT;
ALTER TABLE attempts ADD COLUMN sync_error_kind TEXT
    CHECK (sync_error_kind IS NULL OR sync_error_kind IN ('transient', 'permanent', 'authentication'));

CREATE INDEX idx_attempts_sync_eligibility
ON attempts(status, sync_status, next_sync_at, completed_at, id);
