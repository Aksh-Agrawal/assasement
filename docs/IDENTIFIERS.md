# Domain Identifier Contract

Status: Phase 0 contract.

Identifiers are opaque, case-sensitive strings. Consumers must compare the complete value and must not infer business meaning beyond the formats stated here. Once issued, an identifier is never reused for a different entity.

## Profile

A profile ID is a UUID stored in canonical lowercase hyphenated form.

```text
550e8400-e29b-41d4-a716-446655440000
```

Profile IDs remain stable when profile data changes.

## Question set

`set_id` is a stable logical identifier using lowercase ASCII letters, digits, and single hyphens. It starts and ends with an alphanumeric character and is 3–100 characters long.

```text
set_id = biology-cell-practice-01
version = 1
```

`version` is a separate positive integer. The immutable identity of pack content is the pair `(set_id, version)`. Publishing changed content under an existing pair is forbidden; changes require a higher version. The `set_id` remains unchanged when the material is still the same logical set.

## Question

A question ID follows the same lowercase, hyphenated stable-ID syntax as `set_id`.

```text
bio-cell-q0001
```

It remains stable across question-set versions when it represents the same logical question. Editorial corrections that do not change the tested proposition may retain the ID. A change to the proposition, correct answer, or essential meaning creates a new question ID. Reordering never changes a question ID; `position` carries order.

Question IDs are unique within a pack. A future content catalogue should also avoid assigning one question ID to unrelated logical questions across packs.

## Attempt

An attempt ID is a UUIDv4 generated locally on the device when the attempt is created. It is generated before the attempt is first persisted and never changes during resume or upload.

## Response

A response ID is a UUIDv4 generated locally when the durable response record is created. Updates to the answer or confidence retain that response ID; they do not create a new logical response unless a future event model explicitly specifies otherwise.

## Why stable identifiers matter

- **Resume:** the device can reload the exact attempt, set version, question, and response after a crash or power loss.
- **Immutable question sets:** `(set_id, version)` pins an attempt to the exact content and marking rules it used.
- **Synchronization:** independently created device records have globally collision-resistant identities and can be correlated with server records.
- **Idempotency:** retrying an upload with the same attempt UUID can return the original outcome instead of creating a duplicate attempt.
- **Analytics:** stable question IDs allow longitudinal comparison across compatible set versions without relying on mutable text or position.

UUID validation, uniqueness, referential integrity, and the semantic decision to retain or replace a question ID are responsibilities of future domain and pack validators, not merely display code.
