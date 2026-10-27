# Scoring Specification

Status: Phase 0 contract for the first prototype.

## Scope

The first prototype supports only single-correct multiple-choice questions. Every question has exactly four options identified by the stored keys `A`, `B`, `C`, and `D`.

## Marking configuration

Marking is configuration owned by a specific question-set version, not a global application constant. The initial default is:

| Outcome | Marks |
| --- | ---: |
| Correct | `4` |
| Incorrect | `-1` |
| Skipped | `0` |

A later set version may use other numeric values. An attempt retains or can reconstruct the marking configuration of the immutable set version it used.

## Response classification

- **Attempted:** an answer key `A`, `B`, `C`, or `D` has been selected.
- **Correct:** attempted and the selected key equals the question's `correct_key`.
- **Wrong:** attempted and the selected key does not equal `correct_key`.
- **Skipped:** no answer key is selected when the attempt is scored.

These categories are mutually exclusive and exhaustive. Therefore:

```text
attempted = correct + wrong
question_count = correct + wrong + skipped
```

Changing an answer replaces the effective selection; scoring uses the final persisted selection at submission.

## Score and accuracy

```text
score = correct × correct_marks
      + wrong × wrong_marks
      + skipped × skip_marks
```

Accuracy is a ratio, not a percentage:

```text
accuracy = correct / attempted
```

If `attempted = 0`, then `accuracy = 0.0`. Implementations must not round the internal value for storage or comparisons; a UI may format it for display.

## Confidence

An attempted response stores exactly one of these values:

- `sure`
- `not_sure`
- `guessing`
- `unrated`

`unrated` means an answer exists but the student did not provide a confidence value. It is not a synonym for skipped. A skipped question has no response confidence and is excluded from all confidence buckets.

If a selected answer is cleared before submission, its effective classification is skipped and any formerly selected confidence does not contribute to submitted analytics.

## Required analytics

For every completed attempt, calculate and retain or expose:

- `correct`: number of correct responses.
- `wrong`: number of incorrect responses.
- `skipped`: number of questions without a selected answer.
- `attempted`: `correct + wrong`.
- `score`: total calculated using the attempt's question-set marking configuration.
- `accuracy`: `correct / attempted`, or `0.0` when no questions were attempted.
- Responses per confidence bucket: attempted response count for each of `sure`, `not_sure`, `guessing`, and `unrated`.
- Correct responses per confidence bucket: correct response count in each bucket.
- Wrong responses per confidence bucket: wrong response count in each bucket.
- `sure_but_wrong`: count of responses where `confidence = sure` and the answer is incorrect.
- `guessed_right`: count of responses where `confidence = guessing` and the answer is correct.

For each confidence bucket:

```text
responses = correct + wrong
```

Across all confidence buckets, response counts sum to `attempted`; correct counts sum to `correct`; and wrong counts sum to `wrong`.

### Sure but wrong

```text
confidence = sure
AND
answer is incorrect
```

### Guessed right

```text
confidence = guessing
AND
answer is correct
```

## Fixture convention

`tests/fixtures/scoring_vectors.json` is the normative deterministic example set. In those vectors, `selected_key: null` denotes a skipped question and requires `confidence: null`. An attempted response always carries one of the four stored confidence values, including `unrated` where no explicit rating was supplied.
