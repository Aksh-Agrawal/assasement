-- requires_foreign_keys_off
-- Keep all existing pack versions and attempts while widening answer storage.
CREATE TABLE questions_new (
    set_id TEXT NOT NULL,
    set_version INTEGER NOT NULL,
    id TEXT NOT NULL,
    position INTEGER NOT NULL CHECK (position > 0),
    topic TEXT NOT NULL,
    difficulty INTEGER NOT NULL CHECK (difficulty BETWEEN 1 AND 5),
    question_text TEXT NOT NULL,
    options_json TEXT NOT NULL,
    correct_key TEXT NOT NULL CHECK (length(correct_key) BETWEEN 1 AND 64),
    explanation TEXT,
    media_ref TEXT,
    solution_ref TEXT,
    PRIMARY KEY (set_id, set_version, id),
    UNIQUE (set_id, set_version, position),
    FOREIGN KEY (set_id, set_version)
        REFERENCES question_sets(id, version) ON DELETE RESTRICT
);
INSERT INTO questions_new SELECT * FROM questions;
DROP TABLE questions;
ALTER TABLE questions_new RENAME TO questions;
CREATE INDEX idx_questions_set_position ON questions(set_id, set_version, position);

CREATE TABLE responses_new (
    id TEXT PRIMARY KEY,
    attempt_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    selected_key TEXT CHECK (length(selected_key) BETWEEN 1 AND 64),
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
INSERT INTO responses_new SELECT * FROM responses;
DROP TABLE responses;
ALTER TABLE responses_new RENAME TO responses;
CREATE INDEX idx_responses_attempt ON responses(attempt_id);
