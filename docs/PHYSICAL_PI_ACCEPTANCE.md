# Physical Raspberry Pi acceptance

Status: PENDING physical device verification. Host tests and offscreen screenshots are simulated verification, not Raspberry Pi test results.

Target hardware: Raspberry Pi Zero 2 W, 512 MB RAM, 800×480 display, Debian 13, Python 3.13.5.

## Before updating

Keep the Pi powered and connected to the same network as the development machine. From WSL/Linux at the target repository root, deploy the working tree with the existing script:

~~~sh
bash scripts/deploy_pi.sh assess@assessdev-proto1.local assessment-device
~~~

This script stages the app under ~/assessment-device on the Pi. It does not delete remote files and excludes virtual environments, runtime data and SQLite databases. For the prepared kiosk path at /opt/assessment-device, promote the staged code without deleting destination files:

~~~sh
ssh assess@assessdev-proto1.local
sudo rsync -a --exclude=.venv/ --exclude=var/ --exclude=runtime/ --exclude=.env --exclude='*.db' --exclude='*.db-wal' --exclude='*.db-shm' --exclude='*.sqlite*' ~/assessment-device/ /opt/assessment-device/
~~~

If your existing app uses another install path, use that path consistently instead of /opt/assessment-device. Do not reset SQLite, remove attempts, replace credentials, or re-pair the device.

If the repository is already installed on the Pi and is maintained by Git, update it without touching runtime data:

~~~sh
cd /opt/assessment-device
git status --short
git pull --ff-only
~~~

If the device directory is not a Git checkout, use the deploy script above from the laptop rather than initializing Git over the installed app.

## Install Qt dependencies and preserve the existing DB

On the Pi, from its installed app directory:

~~~sh
cd /opt/assessment-device
source .venv/bin/activate
python --version
python -m pip install --upgrade pip
python -m pip install -e '.[gui]'
~~~

The SQLite database and credentials are not reset by these commands. Startup applies only forward, versioned migrations as needed. Keep the configured database path from /etc/assessdev/device.env. Do not run a database deletion, reset, seed, or re-pair command.

If this Pi uses the prepared kiosk services, restart them after the application files are deployed:

~~~sh
sudo systemctl restart assessdev-sync
sudo systemctl restart assessdev-ui
sudo systemctl status --no-pager assessdev-sync assessdev-ui
~~~

## Launch Qt manually

For an interactive test in the existing graphical session:

~~~sh
cd /opt/assessment-device
source .venv/bin/activate
python -m app.ui_qt.main --fullscreen
~~~

If the service is stopped for manual launch, stop only the UI service first and restore it after the check:

~~~sh
sudo systemctl stop assessdev-ui
# Launch the command above from the Pi's graphical session.
sudo systemctl start assessdev-ui
~~~

## Main offline-to-cloud acceptance

1. Record model, OS, Python version, memory and display mode.
2. Confirm an already-paired local profile and existing attempts remain present.
3. Confirm a current memory-based MCQ pack is downloaded through authenticated profile delivery before disconnecting.
4. Disconnect Wi-Fi. Open the downloaded pack, choose filters, answer, set confidence, skip an item, save/exit and resume.
5. Submit offline. Check that the result is recorded locally and the attempt is visibly pending synchronization.
6. Reconnect Wi-Fi. Confirm the normal sync process uploads once, reports acknowledged/synced, and a retry does not create a duplicate.
7. In cloud History, select the same StudyProfile and confirm the Pi attempt appears with source Raspberry Pi, correct pack version, answers/result and timestamp.
8. Check Analytics endpoint/UI separately: the reference contract currently says not_available and metrics=[]. Record this as a cloud API limitation rather than treating an empty dashboard as failed device upload.
9. Confirm recovery content sent to that same profile is delivered through the normal catalog and can be practiced offline.
10. Confirm QR Quick Add remains available and existing content sync still works after update.
11. Reboot the Pi and confirm offline launch, local profile selection, saved attempt and completed History remain present.

## Capture actual hardware evidence

Record exact OS image/architecture, python version, active resolution/rotation, available memory at idle and while running, temperature/throttle state, startup time, display clipping, keyboard/touch input, service status and sync logs. Capture a photo/screenshot from the physical display and label it separately from ../artifacts/pi-ui-verification/ host-rendered PNGs.

Physical acceptance remains open until the above run is performed on the actual Pi and cloud History confirms the same profile-owned uploaded attempt.
