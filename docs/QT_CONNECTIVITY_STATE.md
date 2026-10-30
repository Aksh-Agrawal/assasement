# Canonical device cloud and sync status

## Audited sources and original defect

UIController.network_label previously used DeviceConsole.network and network_checked_at, expiring the separately requested probe after 180 seconds. Successful profile/catalogue/download/heartbeat/upload operations never updated that probe. SettingsController.cloudStatus invented another label from the probe. LegacyController used settings.network_state; sync_label independently said Synced when no uploads were pending. Settings last-sync time was the button press time rather than a successful operation. This produced Cloud: Unverified alongside Synced despite working authenticated delivery.

Source inventory: app/api/transport.py constructs shared HTTP clients; DeviceApi constructs content, institute, heartbeat, attempt, profile-link and update clients; auth/account_device.py constructs account requests directly. sync/worker.py owns durable upload/retry state; sync/service.py orchestrates account/delivery/heartbeat work. diagnostics.collect_network_status performs health/ready/auth probes, and backend/app/api/routes/health.py implements the existing backend probes. DeviceConsole runs background jobs on separate connections. Qt AppController polls SQLite revisions; AppHeader reads its properties. Settings and diagnostics now consume canonical cloud status.

## Single state holder

app/connectivity.py persists connectivity_cloud in the existing settings table, atomically recording state, observed_at and last_cloud_success across GUI/worker processes. It stores no tokens, request URLs, headers or response bodies. An observed HTTP transport wraps DeviceApi domain clients and direct account requests. Successful authenticated HTTP 2xx contact is Online immediately, without an additional readiness prerequisite. Network/TLS/DNS/timeout failures are Offline. Authenticated 401/403 means Authentication required. Server 5xx means Server unavailable. HTTP success proves contact even if subsequent domain/content validation fails; such a validation failure does not mean the network is offline.

Canonical labels are Checking…, Online, Offline, Server unavailable and Authentication required. App startup resets displayed status to Checking… pending its existing account verification. Cached old probe booleans remain diagnostic details, not competing cloud availability models. Last successful cloud contact survives later failures.

## Health / ready and network independence

Explicit probe results update the same holder: unreachable backend is Offline; a reachable server whose readiness fails is Server unavailable; rejected device authentication is Authentication required. A readiness 503 never rewrites Wi-Fi association or internet availability. A later successful authenticated operation sets Online even if an older probe reported not ready. The latest observed evidence drives display.

Wi-Fi association and OS internet reachability remain distinct device facts. Header networkLabel means cloud availability. Settings Wi-Fi cloudStatus and diagnostic cloud_status use exactly the same cloud holder; underlying probe details remain available for support.

## Sync semantics

Sync status is independent of cloud reachability. connectivity_sync records worker progress/outcome, while pending count and attention state derive from durable attempts. Supported labels: Up to date, Syncing, X pending, Failed and Authentication required. A stale Syncing marker older than ten minutes no longer claims a live worker. last_sync_success remains the real upload acknowledgement time or a completed cycle with fresh authenticated contact, never the time Sync Now was pressed. last_cloud_success is separate and updates for any successful authenticated contact.

Offline plus pending uploads is valid; Up to date means no pending assessment uploads, not proof of current internet access. A catalogue refresh can make Cloud Online without changing assessment-upload history.

## Qt propagation

Background workers persist state through their own SQLite connections. AppController detects data_version/local revision changes on its existing 100ms timer, reloads shared models and emits statusChanged. Header properties update immediately. Settings wires statusChanged to Wi-Fi/sync notifications. Profile changes additionally notify account, institute and storage properties. No worker touches QML objects directly and no restart is required.

## Tests and limits

Mock HTTP plus real SQLite tests cover catalogue/streamed content contact, account sync, heartbeat-based empty sync, server/network/auth failures, readiness classification, timestamp preservation and credential exclusion. Offscreen Qt checks verify that background contact changes both header and Settings through signals. The full device suite retains pairing, offline, content reconciliation, resume and asset-path coverage. Physical Pi/web acceptance is NOT YET VERIFIED in this environment.
