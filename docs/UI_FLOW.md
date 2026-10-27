# Offline Desktop UI Flow

Status: Phase 8A laptop implementation. Raspberry Pi GUI benchmarking, touchscreen validation,
and physical GPIO verification remain pending.

## Layer path

```text
Keyboard / mouse hit-test
          ↓
   Canonical Action
          ↓
     UIController
          ↓
AssessmentApplication
          ↓
Engine + Repository → SQLite
```

Renderers never execute SQL, calculate scores, or mutate domain objects. Mouse clicks and keyboard
keys converge on the same `Action` values before controller routing.

Keyboard shortcuts are A–D for answers, arrows for Previous/Next, Enter for Confirm, Escape for
Back, S/N/G for confidence, R for review marking, T for Submit, and M for Menu.

## Screens

### Profile

Shows local display names only. Previous/Next selects among profiles and Confirm continues. When
none exists, Confirm explicitly creates the fixed development-only `Development Student` profile.
Custom profile naming, PIN setup, and backend accounts remain deferred.

### Subject

Lists only distinct subjects found in installed SQLite question sets. No Biology or Chemistry list
is hard-coded in the UI. Back returns to Profile.

### Question Set

Filters installed sets by subject and shows title, chapter, question count, and version. Confirm
starts the selected immutable version. If the profile has an in-progress attempt, the screen shows
its set plus answered/total counts and Confirm resumes it instead of starting another attempt.

### Assessment

Shows compact subject/title/chapter metadata, position, wrapped question text, four whole-row
answer targets, current answer, confidence, answered count, review state, navigation, and submit.
Previous is disabled on the first question. Next from the final question enters confirmation and
does not submit automatically. Confirm opens the page-like full-content view.

### Confidence

Answer selection is already durably stored as `unrated` before this screen appears. Sure, Not
Sure, Guessing, or Continue Unrated updates the existing response through the application service.

### Submit

Shows total, answered, unanswered, and review-marked counts. Unanswered questions are explicitly
described as skipped. Continue returns to the assessment; Submit Assessment finalizes locally and
shows the engine-produced `ScoreResult`.

### Result

Shows score, correct, wrong, skipped, attempted, accuracy, confidence buckets, sure-but-wrong, and
guessed-right. Review Answers enters immutable review; Return Home returns to Profile without
reopening the completed attempt.

### Review

Shows the question, selected and correct answers, confidence, outcome, response time, explanation,
and review flag. Correct, wrong, and skipped states use distinct labeled/color presentation.
Previous/Next changes only the review view. Full text opens the detail pages. Exit Review returns
to Result; no review action can edit stored responses.

### Error and empty states

No-profile, no-subject/set, startup/database, and controller resume failures produce concise
screens or status messages. Invalid empty question packs are rejected before repository import,
so a stored zero-question set is treated as unavailable/corrupt rather than rendered.

## Persistence and recovery

Window close calls `AssessmentApplication.pause()` and never submits. A selected answer survives
closing on the confidence screen because answer selection is committed immediately with
`unrated`. Resume loads the attempt's exact stored set version and write-once question order.
Completed attempts are never returned by the in-progress lookup and review cannot mutate them.
