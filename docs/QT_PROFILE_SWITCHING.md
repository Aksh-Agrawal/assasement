# Qt StudyProfile switching

## Selected-profile lifecycle

The existing ProfilePickerScreen serves startup and runtime switch modes. Startup still requires an explicit selection; last_active_profile_id highlights a valid cached profile rather than silently entering it. The Home header identity (name, cloud exam context and dropdown indicator) is a single 48-pixel-high touch area. Tap it to enter Switch Study Profile; Cancel returns Home. Account & Profiles rows also select by stable profile ID and indicate Currently using.

ProfileController owns picker/PIN state. UIController owns the selected index, preserves identity across catalogue refresh/reordering, and filters the cloud account_profiles snapshot by account and active link. QML passes stable IDs instead of relying on row positions. PIN selection is revalidated against the current snapshot, including after entry; PinUnlock.unlock is the existing verifier. A revoked/unlinked or archived profile cannot activate. Active removal routes back to the picker. Last-profile persistence stores only the local ID corresponding to the cloud profile, not credentials.

Header grade/context comes from cached cloud exam_context; no fabricated Primary 6 label is inferred. The Profile dataclass itself has no grade field.

## Offline behavior

Switching between already synchronized, linked profiles is entirely local and works offline. It neither logs out the account nor pairs/reconnects the device. Network failure retains the cached account/profile snapshot. New profile creation uses the existing account_create cloud operation; it does not create local-only student identities. Cloud remains authoritative for additions, archiving and revocation.

## Transient state

On activation, pause the outgoing assessment to save timing and responses. Replace only the in-memory AssessmentApplication; do not abandon or delete its durable attempt. Reset subject/chapter/set/navigator indices, institute setup, result/review data, Qt pack ID/version, countdown and review caches. Clear old navigation history. Reload profile-filtered content and emit profile, catalogue, selection, assessment, history, account and storage notifications. Completed history remains in SQLite and is queried by the selected profile.

## In-progress attempts

A valid A attempt stays in_progress when switching to B, but B's engine and resume card do not reference it. On switching back, A's validated resume query finds its original exact version, question order and responses. The existing content reconciliation policy still abandons genuinely revoked content; changing profiles by itself does not trigger abandonment.

Switching is exposed only from Home and Account. Calls from question, confidence, navigation, submission, result/review routes are rejected. Use the existing save-and-leave flow to return Home before switching; there is no silent mid-question change.

## Profile-scoped refresh

Home resume and recent history derive from the new profile. Library and Practice use visible_question_sets/profile_library_catalog. History uses completed attempts filtered by profile_id. Settings installedPacks reloads on the profile signal. Institute Work is currently a placeholder screen, so its identity header updates; the framework controller's assignment setup is cleared. Account indicators use the same selected profile. Background SQLite revision detection refreshes profile snapshots and ejects an active archived profile without restart.

## Verification

Offscreen Qt tests cover startup A selection, Home switch/cancel, offline A/B isolation, completed history, preservation of A's partial response across switching, mid-assessment refusal, last-profile highlighting, missing/archived profile handling and PIN-target revocation. Physical Pi touchscreen acceptance remains NOT YET VERIFIED.
