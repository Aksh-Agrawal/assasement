-- Profile-specific institute grants; content stays in existing immutable storage.
CREATE TABLE institute_work (
 local_profile_id TEXT NOT NULL REFERENCES profiles(id),
 assignment_id TEXT NOT NULL,
 link_id TEXT NOT NULL,
 metadata_json TEXT NOT NULL,
 eligible INTEGER NOT NULL DEFAULT 1 CHECK(eligible IN (0,1)),
 PRIMARY KEY(local_profile_id, assignment_id)
);
CREATE TABLE attempt_institute_context (
 attempt_id TEXT PRIMARY KEY REFERENCES attempts(id),
 assignment_id TEXT NOT NULL,
 institute_id TEXT NOT NULL,
 membership_id TEXT NOT NULL,
 study_profile_id TEXT NOT NULL
);
