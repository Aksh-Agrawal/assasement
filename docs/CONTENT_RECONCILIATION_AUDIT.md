# Device content reconciliation audit

Repository: startup, branch main. Initial working tree clean. startup-cloud inspected read-only.

## Actual state inventory

| State | Cloud authoritative? | Stored locally? | Screen / consumer | Previous removal behavior | Correct behavior |
|---|---|---|---|---|---|
| StudentAccount | Yes | student_account_context; settings account_profiles | Account, profile picker | Account sync manages mapping | Keep existing account verification |
| StudyProfile | Yes for owned profiles | profiles, profile_link_context | Profile picker, all profile screens | Link ownership separate from content | Require active matching link for grants |
| Personal Library / Practice selection | Yes | profile_library (local_profile_id, set_id, version, link_id, metadata_json, eligible) | Library, Practice, Test Setup | Complete catalogue sets removed rows eligible=0 | Same, plus repair attempts in same transaction |
| Catalogue metadata | Yes | profile_library.metadata_json; DeviceConsole.catalog | Remote/download cards | Profile cache replaced correctly, but installed shared packs bypassed grants | Owned profiles require exact profile grant even for shared bytes |
| Physical pack and version | No | question_sets composite PK (id, version), questions; private_pack_versions | Installed content, exact attempt content, diagnostics | Shared versions visible to every profile | Retain bytes; separate authorization from installation |
| Active installed version | No | question_sets.is_active | New assessment catalogue | Active installation mistaken for availability | Apply profile filter to installed active versions |
| Delivery acknowledgements | Cloud records progress | No local delivery table; settings delivery_ack_pending, profile_library_delivery_cursor; DeviceConsole.download_state | Download progress | Not an authorization source | Keep distinct from eligibility |
| Institute work | Yes | institute_work, attempt_institute_context | Institute Work | Removed grant left partial attempt resumable | Same terminal policy as personal removal; retain context |
| Active attempt / resume pointer | Derived locally | attempts.status=in_progress, unique partial index by profile_id | Resume card, new-assessment lock | Removal did not change status | Abandon revoked/structurally invalid partial work |
| Fixed question order | Local, immutable per attempt | attempt_questions | Resume, navigator | Could remain attached to orphan attempt | Validate against exact installed version before offering resume |
| Responses / timing / events | Local | responses, response_events | Assessment, review, history | Preserved | Preserve on abandonment and removal |
| Completed history / upload ownership | Local evidence | attempts, attempt_ownership, attempt_institute_context | History, sync uploads | Preserved | Never delete or downgrade completed rows |
| Selected set / subject / chapter | No, derived | UIController indices; LibraryController _selected_pack_id/_version/_subject/_chapter | Library, packs, Test Setup | Retained after catalogue change | Reload and clear invalid selection |
| Current question / attempt | No | AssessmentApplication.engine, timer; Qt AssessmentController flags | Question, navigator, resume | Existing engine reused for resume | Validate durable state; clear abandoned pointer; resume into fresh engine |
| Qt models | Derived | LibraryController properties, catalogChanged / selectionChanged | Subjects, chapters, cards, resume | Background commits and status refresh did not notify Library properties | Observe SQLite data_version and local changes; refresh and emit signals |

No separate current_attempt_id or resume_attempt_id exists in SQLite: the persisted pointer is the in_progress status query. Abandoning the row clears that pointer and releases the unique profile lock. Physical content is imported into SQLite, not retained as downloaded JSON files; temporary downloads are unlinked after import.

## Source inspection and tracing

Cloud backend/app/api/routes/library.py profile_catalog returns selected, eligible sets with pagination. Device ContentApiClient._fetch_profile_catalog collects all pages before replacing grants. An empty successful catalogue communicates removal. No API change is needed.

Read-only inspection of the supplied workspace var/assessment-device.db found the current 17-table schema, one profile, one question-set version, three attempts and nine responses, but zero profile_library and private_pack_versions rows. This is a workspace fixture, not evidence from the physical Pi. It demonstrates why old shared installations cannot serve as an owned profile authorization source. No user database was modified.

Automated trace: tests/content/test_profile_library.py creates linked A/B, installs shared legacy bytes, grants Chemistry/Biology-equivalent sample content, completes one attempt, starts another and records a response. Removing A's catalogue previously left question_sets, questions, attempts(in_progress), attempt_questions, responses and the live engine. Shared bytes passed can_start_pack without consulting grants; the active row then blocked any new assessment. The new trace asserts that only visibility and the partial attempt status change: A hidden, B visible, partial abandoned, responses/order retained, completed row unchanged, exact bytes retained, pointer cleared, and another authorized start succeeds. Sample Biology exercises the same path as Chemistry Basics and Cell: The Unit of Life.

The exact reported resume exception is generated by AssessmentEngine._require_state: resume_attempt requires IDLE but AssessmentApplication reused an engine in IN_QUESTION. It is not proof of deleted questions. A repeated-resume regression reproduces that lifecycle; resume now restores through a new validated engine and preserves timing. Separate invalid-order coverage handles genuinely broken persisted content references.

Other reproduction coverage: old persisted removal repaired on repository reopen; injected attempt-update failure rolls back both grant removal and attempt repair; valid offline start/resume and version pinning while the set stays selected; Qt offscreen test uses a second SQLite connection to remove selection and observes card, selection and resume signals without restart.
