# Content reconciliation policy

Cloud owns StudentAccount, StudyProfile mapping, personal Practice selection and profile eligibility. The device keeps the last complete validated profile catalogue for offline use. A network/protocol failure retains that snapshot; a successful empty catalogue revokes availability. Removal is learned on successful synchronization, not while offline.

Owned profiles require their own current link-specific grant for normal Library and Practice, including packs installed by old builds as shared content. Legacy unclaimed maintenance profiles retain shared sample compatibility. Physical installation is never evidence of cloud authorization.

Catalogue replacement and partial-attempt repair share a SQLite transaction. Removed links remain as ineligible cache rows; no content/history deletion is necessary. Failure rolls back the entire replacement and repair. Startup uses the same repeat-safe repair against the persisted snapshot; it does not infer cloud changes while offline. Automatic sync and Sync Now both reach refresh_library/cache_profile_library through sync_profile_deliveries. Institute catalogue changes use the same partial-attempt repair.

A genuinely eligible in-progress attempt retains its exact installed version, fixed order and responses even when a newer version becomes active. Previously downloaded versions of a still-selected set remain eligible for offline continuity. Removing the set or revoking its link abandons its incomplete attempt. Abandoned work is terminal and non-blocking; response rows, event history, question order and ownership remain. Completed attempts are untouched. Institute assignment removal follows the same abandonment rule.

There is no independent persisted resume ID: attempts.status=in_progress is the resume pointer and unique per-profile lock. Reconciliation changes only invalid in-progress rows to the existing abandoned status. Before offering or executing resume, validate profile authorization, exact installed question-set version, complete unique question order, resolvable question IDs and response references with the assessment engine. The resume question index is derived from validated answers, not persisted separately. Repeated resume constructs a fresh engine so its IDLE precondition is satisfied.

The Qt application observes local writes and other SQLite connections' committed data_version changes. It reloads profile-filtered catalogue state, clears removed pack/subject/chapter selections, drops abandoned engine/timer pointers and emits catalogue/selection/question notifications. Profile switching reloads the same models. A's removal cannot revoke B's grant or remove B's shared content bytes. Valid offline assessments keep their last synchronized grants and remain resumable.

Physical pack data stays in question_sets/questions. This repair performs no garbage collection and deletes no pack files. Future garbage collection must require zero profile references, zero valid/pinned attempt requirements and zero local download/import/review operations. Current history/review resolves exact question content, so completed attempts conservatively retain their referenced versions as well. Existing foreign keys use RESTRICT to protect those references.

Structured logs identify profile catalogue reconciliation, orphan attempt ID/reason and cleared in-memory resume pointers without credentials. Unexpected resume exceptions are logged with traceback and shown as: "This practice session can no longer be resumed. Your completed history is safe."

## Acceptance on hardware

For A, select Chemistry Basics on web, synchronize, start and leave partial work. Remove it on web and use Sync Now: Library/Practice and Resume disappear without restart. Start another selected pack successfully. Repeat with Cell: The Unit of Life. Confirm completed history remains and B retains any independently selected copy. Disconnect network and verify a still-selected downloaded set starts and resumes offline. These physical-Pi/web steps require hardware/account access and are not represented as completed by automated mocks.
