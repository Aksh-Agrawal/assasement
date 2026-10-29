# Raspberry Pi Prototype Setup

Status: laptop-prepared procedure; no Raspberry Pi result in this document is verified yet.

## Image the SD card

Use Raspberry Pi Imager and select **Raspberry Pi OS Lite**. Do not install the Desktop image. The open 32-bit versus 64-bit decision must be resolved from measurements, so record the exact image selected rather than assuming either architecture.

In Imager customization set:

- hostname: `assessdev-proto1`
- SSH: enabled, with an SSH public key preferred over password-only access
- timezone: `Asia/Kolkata`
- Wi-Fi: development network credentials only if needed for bring-up
- username: choose the development account deliberately; examples below use `assess`

Do not place production credentials or student data on the prototype image.

## First boot and inventory

Connect through SSH, then run and copy the actual output into `docs/measurements.md`:

```bash
cat /proc/device-tree/model
cat /etc/os-release
uname -a
uname -m
free -m
systemd-analyze
vcgencmd measure_temp
vcgencmd get_throttled
df -h
```

Record respectively: exact board model; OS name/version; kernel; architecture; total/used/available RAM; boot duration; temperature; current/historical throttle flags; and storage capacity/free space. A missing command is a finding, not a successful result.

## Deploy from the laptop

Recommended workflow:

```text
laptop edit → ruff → pytest → deploy → SSH → Pi diagnostic/smoke test
```

From Linux, macOS, or WSL at the repository root:

```bash
bash scripts/deploy_pi.sh assess@assessdev-proto1.local assessment-device
ssh assess@assessdev-proto1.local
cd ~/assessment-device
```

The script uses `rsync`, does not use remote deletion, and excludes virtual environments, Git metadata, caches, `var/`, and SQLite database files.

On Windows without `rsync`, prefer WSL plus the same script. Simple alternatives are a clean `git clone`/`git pull` on the Pi or `scp` of the repository while explicitly excluding/not copying `.venv`, `var`, and database files. Never overwrite a Pi test database during deployment.

## Python environment and software smoke test

On the Pi:

```bash
cd ~/assessment-device
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
python -m app.main
python -m tools.hardware.monitor_pi
```

If development dependencies fit and network/package access is available:

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest
```

Do not install Kivy, pygame, LVGL, or another GUI framework in Phase 6A. `gpiozero` is intentionally not a project dependency; install/configure it on the Pi only when physical-button testing begins.

## Display verification

Inspect the current DRM state before changing configuration:

```bash
for connector in /sys/class/drm/card*-*/status; do echo "$connector: $(cat "$connector")"; done
for modes in /sys/class/drm/card*-*/modes; do echo "== $modes =="; cat "$modes"; done
```

Record the connected DRM connector, supported modes, active/native resolution, and refresh rate where exposed. Confirm the entire console is visible without clipping. Do not assume 800×480 and do not add legacy `config.txt` HDMI overrides until an observed problem is documented.

## Touchscreen verification

Identify input devices:

```bash
ls -l /dev/input/
cat /proc/bus/input/devices
sudo apt update
sudo apt install evtest
sudo evtest
```

Select the touch controller event device. Touch top-left, top-right, bottom-left, bottom-right, and center. Record device name, `/dev/input/eventN`, X range, Y range, orientation, whether axes are swapped/inverted, and whether calibration is required. Do not infer touch coordinates from HDMI resolution.

## Power and thermal verification

Run before and during a sustained application/display workload:

```bash
vcgencmd measure_temp
vcgencmd get_throttled
python -m tools.hardware.monitor_pi --watch --interval 5
```

Record idle and maximum observed temperature and the complete throttle flag. Any non-zero `get_throttled` value requires investigation: it can describe current or historical undervoltage/frequency/thermal events. Do not debug unexplained software crashes while known undervoltage remains.

If a USB power meter is available, record voltage/current at Pi idle, Pi plus display, Pi plus display and touch, and observed peak. Otherwise leave current measurements `PENDING HARDWARE TEST`.

## GPIO verification — pending button arrival

Planned wiring uses BCM numbering, internal pull-ups, active-low switches to ground, and 40 ms software debounce. After wiring has been reviewed and `gpiozero` is available on the Pi:

```bash
python -m tools.hardware.test_buttons
```

Test A, B, C, D, PREV, NEXT, and MENU individually and record bounce, missed presses, duplicate presses, and pin correctness. The diagnostic is created but not hardware-verified. Keyboard simulation does not satisfy any GPIO acceptance item.

## Bring-up record

Put measured values in `docs/measurements.md` and check `docs/HARDWARE_ACCEPTANCE.md` only after observing each result on the physical prototype. Preserve command output for anomalies and label blockers before proceeding to GUI benchmarking.


## Independent device installation and configuration

Install `python -m pip install -e ".[gui]"` for pygame-ce. No cloud extra or Node
installation is required. The rsync deployment script excludes backend source,
cloud admin commands, generated runtime files and local secrets. It does not delete
files from an older Pi deployment; use a fresh destination for a device-only rollout.

Copy `.env.example` to `/etc/assessdev/device.env`, edit the paths/API origin, and
create the configured writable directories owned by the `assess` account. Shell
launches must export these variables; Python does not automatically read `.env`.
Import initial packs with `python -m tools.import_pack` (see `--help`) before using
them offline. Assessment reads SQLite rather than scanning the configured pack folder.

Run `python -m app.ui.app --fullscreen` from `/opt/assessment-device` under the Pi
user's graphical session. The existing UI needs the session's display/input access.
For background upload and heartbeat, install the example
`scripts/systemd/assessdev-sync.service` under `/etc/systemd/system`, then run
`sudo systemctl daemon-reload` and `sudo systemctl enable --now assessdev-sync`.
Adjust its account, install path and environment file to match the Pi. It does not
need a display. With no API URL/credential it remains idle. Heartbeat requires the
new endpoint described in DEVICE_CLOUD_CONTRACT.md to exist on the cloud.


## Phase 8 boot-to-app kiosk (prepared; physical verification pending)

Use the existing installed package and shared environment file described above. On the
Pi OS Lite X11 path, install display dependencies once as the operator:

```sh
sudo apt-get update
sudo apt-get install --no-install-recommends xserver-xorg xinit xserver-xorg-legacy
sudo chmod 755 /opt/assessment-device/scripts/kiosk-session.sh
sudo install -m 644 /opt/assessment-device/scripts/systemd/assessdev-ui.service /etc/systemd/system/assessdev-ui.service
sudo install -m 644 /opt/assessment-device/scripts/systemd/assessdev-sync.service /etc/systemd/system/assessdev-sync.service
sudo systemctl daemon-reload
sudo systemctl enable assessdev-ui assessdev-sync
sudo systemctl start assessdev-ui assessdev-sync
```

Confirm the assess account has local console/display/input access and a valid PAM/logind
session. The unit takes tty1 and conflicts with getty@tty1; Xorg uses vt1, no TCP listener,
and xinit execs pygame directly without a desktop menu. Do not loosen Xorg.wrap to
arbitrary users to work around a failed console session. Inspect the actual Pi's display
stack and adjust the reviewed unit if using Wayland instead; this unit is specifically
for X11 Pi OS Lite. Failure to start is an acceptance failure, not proof of compatibility.
No runtime network target is required: startup must work offline.

The normal use path after installation is power -> X11 -> app -> local profile/Home.
Unexpected exit restarts after 10 seconds, bounded to five starts per 120 seconds.
Operator maintenance exit: `sudo systemctl stop assessdev-ui` over SSH. After repair,
`sudo systemctl reset-failed assessdev-ui; sudo systemctl start assessdev-ui` recovers a
rate-limited service. Never make Escape a student shell shortcut. See ROLLBACK.md.

Physical boot-to-app, crash/reboot/resume and graphics/input permissions are NOT TESTED
in this workspace: assessdev-proto1.local did not resolve on 29 October 2026.
