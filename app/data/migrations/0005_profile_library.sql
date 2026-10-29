
-- Physical storage scope is separate from per-profile eligibility.
CREATE TABLE private_pack_versions (
    set_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    PRIMARY KEY(set_id, version),
    FOREIGN KEY(set_id, version) REFERENCES question_sets(id, version) ON DELETE RESTRICT
);
CREATE TABLE profile_library (
    local_profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE RESTRICT,
    set_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    link_id TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    eligible INTEGER NOT NULL DEFAULT 1 CHECK (eligible IN (0,1)),
    PRIMARY KEY(local_profile_id, set_id, version)
);
