#!/bin/sh
set -eu
cd /opt/assessment-device
# Keep a minimal window manager for focus and screen handling. xinit exits when
# the app exits; systemd owns bounded restart and the SSH maintenance stop.
/usr/bin/openbox --sm-disable &
window_manager_pid=$!
trap 'kill "$window_manager_pid" 2>/dev/null || true; wait "$window_manager_pid" 2>/dev/null || true' EXIT
/opt/assessment-device/.venv/bin/python -m app.ui_qt.main --fullscreen
