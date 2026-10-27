# Future hosted acceptance — pending real hardware

Run only after the API and web admin have been hosted and authorized test content
is available. Nothing in this checklist was executed against a hosted service.
Record Pi model, software version, date, API release, pack identity/version/hash,
attempt UUID, observed timings and pass/fail evidence. Do not record credentials,
PINs, Wi-Fi passwords, private keys, or database URLs.

## Loop A: publish to offline assessment

Web admin → publish content → assign to Pi → Pi fetches catalogue → verified
download/import → disconnect network → assessment succeeds.

- [ ] cloud_check confirms DNS, verified HTTPS, health, auth and catalogue.
- [ ] Pair device through the displayed short code; admin approval is required.
- [ ] Reboot Pi; credential persists and authenticated catalogue still works.
- [ ] Startup shows local home/profile promptly while API is unavailable.
- [ ] Heartbeat updates last-seen/version/pack/pending/storage metadata only.
- [ ] Admin publishes and assigns v2; Pi sees matching metadata/hash/size.
- [ ] Download v2; interrupted transfer leaves old content intact and retry works.
- [ ] Invalid hash/schema cannot activate a pack; existing packs remain usable.
- [ ] Start v2 attempt, publish/download v3; active attempt stays on v2.
- [ ] New attempt can select v3; old required versions remain stored.
- [ ] Disconnect network and reboot; installed assessment and resume work.
- [ ] Submit offline; SQLite commits and result appears without HTTP delay.

## Loop B: offline attempt to web Results

Pi completes assessment offline → pending sync → restore internet → background
upload → durable acknowledgement → web Results shows the same attempt.

- [ ] Record offline attempt UUID and pending count without exposing answers/tokens.
- [ ] Restore network; sync resumes within the configured 60-second cycle.
- [ ] Manual Sync Now also uploads and sends heartbeat without freezing navigation.
- [ ] Web Results shows correct device/profile/set version/score/responses.
- [ ] Pending count decreases only after server acknowledgement.
- [ ] Lose connection after server acceptance; retry preserves UUID and creates no duplicate.
- [ ] Repeat upload ten times; web/database owns exactly one attempt for that UUID.
- [ ] Restart both app and sync service; no completed attempt is lost or regenerated.
- [ ] Revoke credential in admin; device shows auth-required, retains pending data
      and permits already authorized local assessment. Re-pair and recover sync.
- [ ] Server 500, timeout, malformed JSON and offline states remain retryable/safe.
- [ ] Diagnostics/support output has no credential, claim secret, PIN or Wi-Fi secret.

Sign off only with physical-Pi and hosted-web evidence for both loops. Mocked CI
establishes repository behavior; it does not establish real network or hardware success.
