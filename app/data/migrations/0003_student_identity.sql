
ALTER TABLE profiles ADD COLUMN cloud_account_id TEXT;
ALTER TABLE profiles ADD COLUMN cloud_profile_id TEXT;
ALTER TABLE profiles ADD COLUMN ownership_state TEXT NOT NULL DEFAULT 'legacy_unclaimed'
    CHECK (ownership_state IN ('legacy_unclaimed', 'owned'));
ALTER TABLE profiles ADD COLUMN link_state TEXT NOT NULL DEFAULT 'unlinked'
    CHECK (link_state IN ('unlinked', 'link_pending', 'linked', 'link_error'));
CREATE TABLE student_account_context (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    cloud_account_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    auth_state TEXT NOT NULL CHECK (auth_state IN ('signed_out', 'verification_required')),
    last_verified_at TEXT,
    offline_policy TEXT NOT NULL DEFAULT 'pending' CHECK (offline_policy = 'pending')
);
CREATE TRIGGER profile_identity_insert BEFORE INSERT ON profiles
WHEN NOT (
    (NEW.ownership_state = 'legacy_unclaimed' AND NEW.cloud_account_id IS NULL
        AND NEW.cloud_profile_id IS NULL AND NEW.link_state = 'unlinked')
    OR (NEW.ownership_state = 'owned' AND NEW.cloud_account_id IS NOT NULL
        AND NEW.cloud_profile_id IS NOT NULL)
)
BEGIN SELECT RAISE(ABORT, 'Invalid profile ownership metadata'); END;
CREATE TRIGGER profile_identity_update BEFORE UPDATE ON profiles
WHEN NOT (
    (NEW.ownership_state = 'legacy_unclaimed' AND NEW.cloud_account_id IS NULL
        AND NEW.cloud_profile_id IS NULL AND NEW.link_state = 'unlinked')
    OR (NEW.ownership_state = 'owned' AND NEW.cloud_account_id IS NOT NULL
        AND NEW.cloud_profile_id IS NOT NULL)
)
BEGIN SELECT RAISE(ABORT, 'Invalid profile ownership metadata'); END;
