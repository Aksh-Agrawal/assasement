
CREATE TABLE profile_link_context (
    local_profile_id TEXT PRIMARY KEY REFERENCES profiles(id) ON DELETE RESTRICT,
    link_id TEXT NOT NULL UNIQUE,
    account_display_name TEXT NOT NULL,
    study_profile_name TEXT NOT NULL
);
CREATE TABLE attempt_ownership (
    attempt_id TEXT PRIMARY KEY REFERENCES attempts(id) ON DELETE RESTRICT,
    study_profile_id TEXT NOT NULL,
    link_id TEXT NOT NULL
);
