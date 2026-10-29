# Device compatibility and pilot policy

See startup-cloud/docs/COMPATIBILITY_MATRIX.md for the complete independently maintained
cloud/client matrix. Device runtime has no dependency on the sibling checkout.

- Legacy wire v1 without ownership/assignment is supported by current cloud. Legacy
  attempts remain unclaimed after profile linking; absent fields retain old fingerprints.
- New profile/library/institute routes and ownership fields require current cloud schema
  20261029_03. Deploy compatible cloud and migrate before enabling the new Pi client.
- New Pi with old cloud is unsupported for profile/institute features. Never strip
  assignment/ownership to force upload. Retain failed attempts and request operator help.
- Local SQLite 2/3/4/5/6 upgrades to 6 are tested with retained attempts, answers, packs,
  ordering and pending sync. New schema is not permission to infer ownership.
- Offline assessment/resume uses immutable SQLite evidence and no network. Revocation
  cannot reach a disconnected Pi; future online actions revalidate current authorization.
- Unrelated multi-account shared-device privacy and offline account authentication remain
  unresolved pilot policy. Restrict use to a single account or supervised pilot. Linking
  cannot transfer an already-owned local profile to another account.
- Software signature/hash verification/staging and simulated rollback are tested. Actual
  service activation/health rollback and Raspberry Pi performance are NOT TESTED.

Do not remove old cloud routes during the first rollout. Keep old credentials/content
compatible until explicit later retirement, based on actual client inventory.
