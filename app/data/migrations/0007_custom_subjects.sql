-- requires_foreign_keys_off
-- Rebuild only pack metadata; children and historical attempts retain their keys.
CREATE TABLE question_sets_new (
    id TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version > 0),
    title TEXT NOT NULL,
    subject TEXT NOT NULL CHECK (length(trim(subject)) BETWEEN 1 AND 64),
    chapter TEXT NOT NULL,
    marking_json TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    downloaded_at TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 0 CHECK (is_active IN (0, 1)),
    PRIMARY KEY (id, version)
);


INSERT INTO question_sets_new SELECT * FROM question_sets;
DROP TABLE question_sets;
ALTER TABLE question_sets_new RENAME TO question_sets;

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
