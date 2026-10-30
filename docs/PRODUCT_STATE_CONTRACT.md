# Product state and reconciliation contract

Current as of 2026-10-30. This supersedes conflicting wording in earlier phase
reports, especially archived-profile capacity and the old downloaded-only delivery UI.

## Identity and profiles

StudentAccount and StudyProfile are cloud authoritative. A web session authenticates
the human; a DeviceCredential authenticates a Raspberry Pi transport. An active
AccountDeviceLink establishes account ownership. A credential or cached display name
alone never proves ownership. No student password or web session is stored on the Pi.

Normal flow: Connect Raspberry Pi to Account → Sync Study Profiles → Choose Study
Profile → Library / Practice & Downloads. New profiles are created on the server via
the web or `POST /api/v1/device-account/profiles`; there is no anonymous creation
fallback. Previously synchronized profiles and installed content remain usable offline.
Legacy maintenance flows are explicitly outside normal student navigation.

There may be at most **three active profiles**. Creation and restoration serialize on
the StudentAccount row. Archived profiles retain history and identity, consume no active
slot and can be restored if capacity allows. No hard-delete route is introduced.
Restore: `POST /api/v1/student/profiles/{id}/restore`, owner scoped, 409 at capacity.
Existing over-limit accounts are preserved; creating/restoring further active profiles
is denied until capacity is available.

`GET /api/v1/device-account` verifies active account ownership, returns the active profile
list and count, adds missing internal links and revokes links for archived profiles.
New/renamed profiles update the Pi cache. Archived profiles disappear from the active
picker; SQLite profiles, attempts, immutable start-time ownership and content bytes
remain. Restore preserves the profile identity but creates a fresh authorization link;
historical attempts are never reassigned to that link.

## Connection and availability

Account (web): `signed_out`, `signed_in`.
Device/account: `not_connected`, `pairing`, `connected`, `offline_cached`,
`verification_required`, `revoked`, `error`.

Pi Connected requires successful account verification within 180 seconds and evidence
of verification in the current UI process. Restart or expiry shows verification required;
an account job shows Verifying. Network failure retains the cached identity and last
verified timestamp. Confirmed 401/403 on verify/create/disconnect clears active account
routing and records revocation; it never deletes SQLite, profiles, bytes or attempts.
The UI explains that reconnection is required. A failed creation never creates a fake
profile. Other server errors show Needs attention without claiming a valid connection.

Cloud availability vocabulary: `offline`, `wifi_only`, `internet_available`,
`cloud_unreachable`, `cloud_available`. Unknown observations remain unknown.
Wi-Fi association is measured by NetworkManager; its independent CONNECTIVITY observation
reports internet available/limited/portal/offline/unknown. It is not a cloud-auth check.
Cloud availability is a fresh successful API observation (180 seconds), separately from
account verification. Network and account screens retain these separate meanings.

Web online means the device was seen within 180 seconds. Account & Devices refreshes
every 15 seconds while visible, shows last seen and safe reported software/pack/pending
attempt/heartbeat/health information. It does not infer real-time Wi-Fi association.
On refresh failure it explicitly warns that displayed information may be stale.

## Sync

States: `idle`, `syncing`, `synced`, `pending`, `failed`, `auth_required`.
An empty queue is labelled No pending attempts, not proof of successful cloud sync.
The device shows pending attempts, last successful sync and attention state.
Sync Now runs off the GUI thread using separate repository connections: verify account,
reconcile profiles, upload the existing bounded attempt batch, report heartbeat, process
bounded rotating profile/institute deliveries and refresh metadata. Failed verification
stops that cycle without deleting local evidence. Attempt acknowledgements remain UUID
idempotent; heartbeat failure does not undo a durable attempt acknowledgement.

## Delivery

Conceptual states: `not_selected`, `selected`, `queued`, `device_seen`, `downloading`,
`downloaded`, `installed`, `failed`, `removed`.

| Wire state | Meaning | Student label |
| --- | --- | --- |
| queued | Cloud intent only | Queued; if offline, download when Pi reconnects |
| device_seen | Pi parsed catalogue and explicitly acknowledged request | Device received |
| downloading | Pi started fetching bytes | Downloading |
| downloaded | Pi obtained and validated exact bytes, import not yet confirmed | Downloaded - awaiting installation |
| installed | Atomic import succeeded, or existing hash-verified bytes reused | Ready on Pi |
| failed | Download/verification/import failed | Failed - retry |
| removed | Selection/delivery removed; historical data retained | Removed |

The Pi posts `{local_profile_id, set_id, version, status}` to
`/api/v1/profile-content/{link_id}/status`, using its bearer credential. The server
validates the device, exact profile link, account, active selection and eligible version.
Acknowledgement of a superseded version returns 409. All progress is persisted server-side
against the exact pack; row locking and ordered progress prevent late receipt/failure
from overwriting installation. Repeated Send preserves existing progress; failed/removed
deliveries can be explicitly requeued. A newer published version is presented as queued
with Update available until acknowledged for that version.

Installed bytes and acknowledgements are separate: acknowledgement failure leaves bytes
intact. The rotating delivery cycle rechecks eligible persisted catalogue entries after
restart and resends installed acknowledgements without redownloading matching bytes.
This relies on the configured sync service or an explicit Sync Now; it is not an
independent push notification service. Practice & Downloads polls every five seconds
while visible, and also offers a manual refresh.

Old clients may continue to send `downloaded`; that state is never upgraded to installed
by assumption. Deploy cloud support before updated devices.

## Ownership and storage authority

| Record | Authority |
| --- | --- |
| Account / active StudyProfile list and count | Cloud |
| AccountDeviceLink / ProfileDeviceLink / credential validity | Cloud |
| Profile-scoped selection and eligible content version | Cloud |
| Cached account/profile metadata | Pi copy of last successful cloud verification |
| Installed exact bytes / local download result | Pi, reported to cloud |
| Durable delivery acknowledgement | Cloud persistence of authenticated Pi report |
| Attempt evidence | Immutable start-time ownership; Pi queue → cloud durable acknowledgement |
| Device online observation | Cloud last seen, with 180-second threshold |

Migration `20261030_01` follows `20261029_04`, expands only the existing delivery status
constraint, preserves PostgreSQL RLS and installs missing SELECT/INSERT/UPDATE grants
and operation-specific policies for an existing restricted assessment_backend role.
PUBLIC/anon/authenticated remain blocked; DELETE is not granted. Existing policies are
retained without duplicate creation. It adds no tables or secrets. If the runtime role is
created after migrations, apply the documented baseline role provisioning before serving. Downgrade refuses to discard new progress
states; retain schema and roll back code instead. Run migrations only through the
operator's authorized migration process, never automatically against production.

## Discovery and evidence

Library is discovery; Sample Content filters the existing four labelled five-MCQ demo
sets; My Uploads exposes private JSON upload and the manual builder. Explicit local seed:
`python -m backend.tools.seed_demo_library`; verify four Sample Content cards, run twice
to verify idempotency. `--remove` archives discovery without deleting historical bytes.
The command is never run at startup and refuses production mode. Demo identities 1/2/3/4
support browser practice, Pi delivery, profile isolation and version-update testing;
version tests create an explicit newer immutable version rather than overwriting a seed.

Practice & Downloads holds selections, unfinished practice and delivery status. History
contains completed evidence only. Institute access remains explicit consent and assignment
scoped. Analytics remains unavailable; no new calculations or unrelated features are added.

Local software tests and rendered previews do not certify physical display/touch/GPIO,
NetworkManager privileges, boot/reboot or deployed hosting. Record physical acceptance
separately at 800×480 logical and 800×600 physical.
