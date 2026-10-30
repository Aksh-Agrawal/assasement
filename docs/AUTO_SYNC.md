# Automatic Pi synchronization

## Scheduler and lifecycle

The Qt entry point starts AutoSyncScheduler on one daemon worker thread after constructing the UI. Its initial cycle is due immediately. The systemd app.sync.service entry point uses the same scheduler. An OS-held <database>.scheduler.lock elects one owner when both are launched, while <database>.sync.lock serializes every manual/automatic run_cycle. Locks release on process exit. Manual Sync Now runs the same run_cycle(refresh=True) in DeviceConsole's existing background worker and waits behind an active cycle rather than overlapping it.

Default online reconciliation interval is 25 seconds plus 0–2 seconds jitter, configurable through ASSESS_SYNC_INTERVAL. Failure intervals are 25, 50, 100, 200 and 300 seconds maximum plus jitter. Fresh successful contact resets backoff. Existing successful online evidence or enabling Automatic Sync wakes reconciliation early. DeviceConsole additionally records a local wake-up after Wi-Fi reconnect and successful account/profile synchronization, bypassing long offline backoff without an extra polling service. Local wake-up checks run every two seconds, read only three settings, and make no network calls. Offline heartbeat attempts also respect backoff; successful heartbeat is normally every 60 seconds and can wake refresh after reconnect. No claimed real-time changes while offline.

The existing sync operation handles profile verification, completed uploads, heartbeat, personal catalogue/delivery/removals and institute work. A compact per-profile operation/manifest endpoint returns a catalogue hash and pending states. Unchanged snapshots reuse validated cached catalogue metadata; installed sets are excluded from repeated installation work. Bounded rotating downloads retain the existing per-cycle budget. Manual download still refreshes eligibility before using bytes.

## Settings

Settings → Sync has Automatic Sync ON/OFF (default ON), description, last successful sync, next automatic sync countdown, pending results and Sync Now. automatic_sync is persisted in SQLite. OFF stops automatic profile/content/result reconciliation; operational heartbeat continues and startup/account verification is not disabled. Manual sync still reconciles immediately through the shared service. Next-sync countdown uses a local QTimer; it performs no network work.

## Delivery and removal acknowledgement

Existing delivery states report queued → device_seen → downloading → downloaded (shown as Installing) → installed, or failed. Installation acknowledgement follows verified SQLite import. Removal operations reuse the existing unique selection/link delivery record, with operation=remove and a revision. The Pi reports device_seen/removing, fetches the complete authoritative catalogue, commits profile eligibility plus partial-attempt repair, validates absence from the profile catalogue, then acknowledges removed. Failed local reconciliation reports a safe error code. Lost acknowledgements retry idempotently after restart; cloud pending records survive shutdown. A revision prevents a delayed removal acknowledgement from changing a reactivated installation.

No physical bytes are erased. Removed means no longer available to that StudyProfile. Profile B may retain the same installed version. Completed history, response rows, exact versions and ownership remain. Revoked partial attempts become abandoned under CONTENT_RECONCILIATION_POLICY.md and no longer block new assessments. Qt's existing SQLite revision detection reloads committed availability and clears transient selections/resume state without restart; acknowledgements attest durable profile availability, not a rendered frame or storage-byte erasure.

## Rollout and verification

Deploy cloud migration 94bde2efcab6 and backend/web before upgrading Pi for the full operation lifecycle. Production migration was NOT applied by this task. The device falls back to a full catalogue refresh when the operation endpoint is absent, but an old backend cannot confirm removals. Preserve SQLite and pack history; no reset is needed. Physical Pi acceptance remains separate from automated tests.

Tests cover scheduler window/backoff/enable/reconnect/lock behavior, automatic real-cloud delivery/removal without manual sync, offline waiting, disabled automatic mode plus manual sync, lost acknowledgement/restart, profile isolation, preserved completed history, abandoned revoked partial attempts, and Qt asset/model regressions.
