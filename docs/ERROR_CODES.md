# Support error codes

These identifiers are stable support categories. Diagnostic output may include several codes.

| Code | Meaning | User impact | Recommended support action | Safe to retry? |
|---|---|---|---|---|
| `DB-001` | Local SQLite missing, unreadable, or unhealthy | Local assessment may be blocked | Preserve the DB, run diagnostics, restore only from a verified backup | No automatic retry/reset |
| `SYNC-001` | Attempt upload/backend temporarily unavailable | Completed work remains local | Check network/backend and retry the bounded sync | Yes |
| `SYNC-002` | Pending or failed sync backlog exists | Local assessment still works | Inspect queue counts and last error category | Usually |
| `AUTH-001` | No usable local device credential | Remote sync/content unavailable | Pair the device | After pairing |
| `AUTH-002` | Credential rejected or revoked | Remote operations require support action | Re-pair or verify backend device state | Not with same credential |
| `CONTENT-001` | Latest content sync failed | Installed packs remain usable | Check catalog availability, size/hash, and pack validation | Yes after cause is fixed |
| `UPDATE-001` | Update activation rolled back or failed | Current healthy release remains selected | Inspect update metadata and signature/artifact checks | After correction |
| `BACKEND-001` | Optional network probe cannot reach backend | Offline operation remains available | Check backend process/network/PostgreSQL | Yes |
