# Device UI flow

The device UI follows `Offline_First_Assessment_Device_Product_Implementation_Playbook_v2.docx`
(version 2, 13 October 2026), particularly sections 3–5 and the navigation invariants.
Local implementation and verification were updated on 27 October 2026.

## Run locally

```powershell
.\.venv\Scripts\python.exe -m app.ui.app
```

The existing Pi command remains supported:

```bash
cd ~/assasement
source .venv/bin/activate
DISPLAY=:0 python -m app.ui.app
```

Optional flags: `--db PATH`, `--base-url URL`, `--fullscreen`, and `--gpio`.
The GUI uses the existing database by default. Do not replace it with a preview database.
No systemd or display-server configuration is changed by this UI work.

## Route graph

```text
Startup checks -> Profile picker -> PIN (when protected) -> Home
       |
       +-> Recovery -> Retry / startup diagnostics / recovery guidance

Profile -> Add local profile / Pair device
Home -> Continue test
     -> Practice / Subjects -> Subject -> Chapter -> Question set -> Test setup
     -> Progress
     -> Settings

Test setup -> Start / Resume -> Question -> Confidence -> Question
Question -> Previous / Next / Review flag / Full text
         -> Assessment menu -> Navigator / Resume / Submit / Device status / Home confirmation
Submit confirmation -> Continue test / explicit Submit -> Result
Result -> Review all / wrong / guessed / sure-but-wrong / guessed-right -> Result -> Home

Settings -> Wi-Fi / Sync / Account-pairing / Content updates / Software update
         -> Device-storage / Diagnostics / About
```

The welcome screen is the profile picker. There is no extra welcome gate or online/offline mode.
`app/ui/router.py` declares routes. `app/ui/screens/console.py` is the renderer registry;
each major screen has its own module. Historical direct-controller integration calls are
retained with `startup=False`; the GUI always selects the complete device flow.

## Startup and recovery

The window appears before opening SQLite. `StartupSession` advances real local checks:
configuration, repository open/integrity validation, applied migration version, device identity,
credential availability, installed content, interrupted attempts, update metadata, and quick check.
There is no timed splash, fabricated success animation, or internet requirement. A malformed
update-state file is advisory; inability to safely open/check the local database is blocking.
Recovery never deletes, overwrites, or automatically restores data. Its diagnostics show completed
startup checks and a safe support code. See `RECOVERY.md` for the support procedure.

## Input and layout

The logical canvas is 800 × 480 and is scaled to the display window. Colours and typography live
in `app/ui/theme.py`. Fonts and bounded label surfaces are cached. The event loop redraws after
input, a device-job completion, a resize, or a timer-second change; there is no continuous animation.

Touch/finger input and mouse hit targets emit the same `Action` plus optional UI payload as keyboard
and GPIO input. Synthesised touch mouse events are ignored to prevent a single tap being processed
twice. GPIO is opt-in and uses the existing button adapter; callbacks post events to the GUI thread.

- Questions: A/B/C/D or 1/2/3/4 answer; Left/Right previous/next; R review flag; M menu.
- Confidence: A/B/C or S/N/G select Sure/Not Sure/Guessing; Back returns to options.
- Lists: Left/Right choose, A or Enter select, M/Escape back.
- Submit: A/Enter continues the test; T or the labelled touch target performs final submission.
- Text entry: type normally on a keyboard, or use the on-screen keys. GPIO Left/Right chooses
  a character, A types it, B deletes, C changes key sets, D confirms, Menu goes back.
- Full text: Left/Right changes page, A/Menu/Back returns. Page counts derive from all content.
- F12 saves a local screenshot under `var/screenshots`.

Every emitted touch target is at least 48 × 48 logical pixels. Headers and contextual physical-button
footers are persistent. Long question/option bodies scroll; full-text pages expose all text without a
fixed three-page limit. Review explanations scroll and are also available in full text. Navigator
buttons are paged in groups of 40 and use `+` answered, `-` unanswered, `*` review, `>` current as
well as colour and border changes. Diagram paths are confined to the configured media root,
file/pixel sizes are bounded, and scaled surfaces are cached. Missing media has an explicit state.

## Assessment boundaries

Only `AssessmentApplication` writes assessment events and transitions the engine. The UI does not
execute SQL or calculate scores. Result accuracy, correctness counts, confidence matrices and
priority-review IDs come from the engine's `ScoreResult`. Local Progress shows the most recent 20
completed attempts for the selected profile, using persisted scores and sync state.

An in-progress attempt always resumes its exact stored version and question order. The existing
engine allows one in-progress attempt per profile. Start New explains that the existing test must
be finished; it never abandons or replaces that attempt. Leaving for Home requires a confirmation
and pauses/saves timing. Closing and restarting preserves answers, confidence and review flags.

## Device services

`DeviceConsole` runs bounded operations on a daemon worker. Each operation that needs SQLite opens
its own repository connection; it never passes the GUI connection to a thread. Results are applied
on the main thread. The assessment can continue while a network request fails or is waiting.

- Wi-Fi uses argument-array NetworkManager calls with timeouts. Saved networks, scanning,
  password entry, connect and forget stay in the UI. Missing NetworkManager is a visible state.
  Association and internet/API reachability are checked separately.
- Pairing reuses `PairingClient` and `CredentialStore`; only the user pairing code is displayed.
  Polling is bounded, expiry is handled, and cancelling invalidates pending results/credential saves.
  Existing local profiles remain available. Removal of pairing has an explicit confirmation.
- Sync reuses `SyncWorker`, preserving retry/idempotency behavior and local assessment independence.
- Content uses `ContentApiClient` and the existing download/hash/schema/atomic-import pipeline.
  Local versions remain listed and usable. Fetched remote metadata adds catalogue entries without
  hiding local content. Download, update, validation failure and unavailable-offline states are shown.
- Software update uses `UpdateClient`, `verify_update` and `stage_update`. Install & Restart remains
  disabled: the existing activation service updates release metadata but this checkout has no
  boot/restart launcher that consumes it. This UI does not pretend to have installed a staged release.
- Diagnostics reuses `collect_device_status`; support export reuses `create_support_bundle`.
  Account/device screens show only pairing state and a shortened ID, never token or secret paths.

## PIN integration limit

The existing checkout contained nullable `pin_hash` / `pin_salt` columns but no PIN verifier,
provisioning UI, hash-format contract or lockout implementation. The repository now exposes these
fields through a read-only accessor; SQL remains in the data layer. The verifier accepts explicitly
encoded `pbkdf2_sha256$iterations$hex_digest` values with the separately stored UTF-8 salt, bounds
iterations to 100,000–1,000,000, compares in constant time, and persists escalating lockout after
five failures. No existing hashes are rewritten. Unknown/opaque formats stay locked and show
recovery guidance. New local profiles have no PIN; PIN provisioning is not supplied by this UI.
Confirm the deployed provisioning format before claiming compatibility with existing protected Pi
profiles. Do not treat the test format as proof of that deployment policy.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m tools.ui_smoke
```

`ui_smoke` uses a temporary real repository and the shipped sample question pack. It generates
24 800 × 480 previews and a contact sheet under `artifacts/ui-redesign`, without opening or changing
student data. Automated tests exercise real engine/repository transitions, restart/version pinning,
startup/recovery, settings navigation, touch bounds, long text, PIN lockout, background failure,
local diagnostics/support export, catalogue states and large question navigators.

Pi display/touch/GPIO, NetworkManager permissions, actual server pairing/sync/download,
release activation/restart and on-device performance require device acceptance testing.
No remote deployment or Pi test is implied by local previews or the headless entry-point tests.
