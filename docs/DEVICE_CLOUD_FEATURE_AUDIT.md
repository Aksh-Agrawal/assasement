# Device–cloud feature audit

Audit date: 12 November 2026  
Target: Raspberry Pi app in this repository  
Reference: startup-cloud master at b74ebce8979a6af879599b7d38e271bbe14cc587

## Summary

The target already contains the core offline-first Pi workflow and current profile-scoped cloud delivery/upload paths. This pass completed the Qt/QML launch path, fixed practice filtering edge cases, exposed source in History, repaired current QML rendering issues, and added regression/capture coverage.

| Capability | Result | Evidence / qualification |
|---|---|---|
| Memory-based MCQ packs | Compatible | Pack v1 MCQ shape and solution_ref extension are validated and imported into SQLite. Current cloud PACK_FORMAT is v1 with four A–D options, topic, difficulty 1–5 and nullable media reference. |
| Authenticated cloud delivery | Compatible | Profile catalog and exact-version pack delivery use the paired device credential and profile link; downloaded bytes are bounded, hash checked, schema validated and atomically imported. |
| Figures | Compatible | Local media references are resolved against the media cache; authenticated media retrieval/cache and QML question figure display are present. |
| Offline assessment | Compatible | Local SQLite owns attempt state, immutable set/version and question order; answers/confidence autosave and interrupted attempts can resume without cloud access. |
| Practice filters | Implemented / covered | Topic, difficulty, count presets (all/5/10/20/custom where eligible), and shuffle are passed to the assessment service. Empty filter combinations are now a real zero-match state and disable start. |
| Attempt evidence | Compatible | Upload serializer includes response correctness, confidence, skipped response representation, per-question timing, first-shown/answered timestamps, overall duration, stable attempt UUID, set version and owning local/cloud profile references. |
| Cloud History attribution | Implemented | History rows retain the cloud source label (web or device) and the Qt view displays Raspberry Pi/Web with synced state. Cloud history is profile scoped and ownership is validated before caching. |
| Recovery practice | Compatible through delivery | Cloud recovery send-to-Pi queues a one-question versioned pack for a StudyProfile/link. The Pi receives it through the existing profile-content catalogue/download/import path; recovery policy stays cloud-owned. |
| QR Quick Add | Preserved | Existing Quick Add screen/controller and its content submission flow remain registered in the normal Qt application and in QML/capture coverage. |
| Numerical questions | Deferred | Memory-based MCQs are the priority. Numeric free-response is not claimed as supported; no cloud or database changes were made. |
| Offline Analytics | Implemented in native Qt from SQLite evidence | Progress calculates completed attempts, graded accuracy, correct/incorrect/skipped counts, confidence outcomes, practice duration, average answer time and 5/10/20-attempt trends. Profile-scoped cloud History snapshots are cached in SQLite and included. The web dashboard derives the same metrics from History; `/analytics` is recovery-oriented. |

## Practice setup behavior

Question count and filters operate on the installed immutable pack version. Shuffle and selected IDs/order are stored with the attempt so resume and review do not select a different question set. Presets are constrained by the eligible filtered count. Custom count remains editable up to that count. A pack with no matches produces an explanatory message instead of fabricating a one-question assessment.

The v1 cloud pack shape does not define a separate question-type facet. The Pi does not invent one. If future packs add type metadata, that requires an agreed schema/API extension and a device parser/UI update.

Assignments must retain their assigned pack, question set and order. Practice filters are for student-selected practice and must not alter the content or order of a fixed assignment.

## History ownership and Analytics evidence

Local completed attempts upload under their stored StudyProfile linkage. Upload retries keep the same attempt UUID and idempotency key. Cloud History endpoint responses are scoped to the exact linked profile; the device rejects/caches only results attributed to that profile. Web history is shown with its source and is not misrepresented as a local attempt. The Pi fetches web and device completions from the paired device's profile-link authorized `/api/v1/profile-content/{link_id}/history` endpoint and stores the snapshot in SQLite. It also fetches completed attempt detail from `/api/v1/profile-content/{link_id}/history/{attempt_uuid}` and caches authorized review evidence. When a returned UUID already exists in the selected local profile, the local attempt remains the single displayed and counted record and its richer evidence is kept. Cached web review can be opened offline through the existing Qt Review screen.

Offline Progress reads completed local attempts and their stored response correctness, confidence and timing from SQLite. It also uses the latest successfully cached authorized cloud History snapshot while offline. Accuracy is correct answers divided by correct plus incorrect answers; skips are reported separately. The trend follows the selected 5, 10 or 20 completed-attempt window. Profile switching and assessment completion notify the Qt binding; sync/import changes are detected through SQLite's data revision and refresh the bound properties.

The device preserves:
- selected option or null for skipped response;
- confidence bucket or null for skipped response;
- correctness snapshot;
- response duration and first-shown/answered timestamps;
- assessment start/completion and elapsed duration;
- immutable set ID/version and response/question IDs;
- stable attempt UUID and profile ownership context.

Cloud device ingestion remains a snapshot upload, not server-side rescoring. Student web metrics are derived from History in the dashboard; the separate recovery `/analytics` route is not an aggregate student metric API. Device Progress calculates locally from retained evidence. No Analytics schema migration is required.

## QR and synchronization

QR Quick Add remains available from the Qt router and the standard content sync cycle remains responsible for catalogue refresh, authenticated download, integrity checks, install, attempt upload and History refresh. No separate recovery backend or alternative QR service was added.

## Known limits

- Full History and Analytics acceptance needs a deployed cloud API and paired device; no live cloud mutation was performed during this local implementation.
- Custom subset attempts use the current device attempt v1 shape, which has no explicit subset/order manifest field. Cloud History can show the result and original set/version, but cloud consumers cannot reconstruct every custom subset from this payload alone. Full-pack practice remains the unambiguous path.
- Attempt figures are not transferred in History detail. The current device content figure route remains authorized through installed profile content; student-session figure URLs are omitted from attempt detail. Old cloud deployments without the attempt-detail route remain summary-only.
- The new authenticated cloud detail and QR revocation/rate-limit tests could not run on this Windows Python 3.14 host because Starlette TestClient hangs during asyncio socketpair startup. Ubuntu/Python 3.13 CI is configured; its first green run is still pending.
- Physical Raspberry Pi Zero 2 W execution, thermal/memory profile, Wi-Fi reconnection, display/input and actual upload acknowledgment remain unverified here.
- Numerical response entry remains deferred.
