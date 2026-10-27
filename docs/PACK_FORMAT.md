# Question Pack Format

`schemas/pack.schema.json` is the normative JSON Schema Draft 2020-12 contract for pack schema version `1`.

## Version 1 rules

- `schema_version` is exactly `1`.
- A set is identified by immutable `(set.id, set.version)`; version is a positive integer.
- Marking belongs to the set and contains numeric `correct`, `wrong`, and `skip` values. Correct marks must be positive; wrong and skip marks may be zero or negative.
- A pack contains at least one question.
- Each question has a stable ID, positive position, non-empty text and topic, difficulty from 1 through 5, exactly four options, a correct key, and a nullable media reference.
- Options are canonically ordered `A`, `B`, `C`, `D`. Enforcing order in schema version 1 guarantees exactly one of each key and gives deterministic serialization/display input.
- `correct_key` is one of `A`, `B`, `C`, or `D`; because the canonical four options are required, it necessarily names an option.
- `explanation` is optional. When present, it is non-empty.
- `content_status` and `content_notice` are optional provenance labels. Development fixtures should use them to prevent accidental treatment as production educational content.

## Application-level validation

JSON Schema validates each value and object shape, but the future pack validator must additionally check cross-item and operational invariants:

- question IDs are unique within the pack;
- question positions are unique and, for version 1 policy, contiguous from 1 through the question count;
- `(set.id, set.version)` has not previously been published with different bytes or meaning;
- a retained question ID still represents the same logical question across set versions;
- non-null media references are normalized relative POSIX paths beneath `media/`; Phase 5 rejects absolute, drive, backslash, dot-component, and traversal paths;
- referenced media existence, format, asset size, and asset hash pass a future archive/manifest policy;
- text and explanations satisfy content, encoding, language, and licensing policy;
- the schema version is supported by the installed application before activation;
- the pack or manifest passes the future integrity/signature policy.

In a design that allowed options in arbitrary order, JSON Schema would need more elaborate constraints and still would not conveniently express all cross-field uniqueness rules. Version 1 avoids ambiguity by requiring the literal order `A`, `B`, `C`, `D`; a future schema version must retain an explicit validator check if it relaxes that ordering.
