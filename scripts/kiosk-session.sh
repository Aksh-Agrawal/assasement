#!/bin/sh
set -eu
ASSESS_APP_ROOT=${ASSESS_APP_ROOT:-/opt/questraa-device}
cd "$ASSESS_APP_ROOT/current"
# Keep a minimal window manager for focus and screen handling. xinit exits when
# the app exits; systemd owns bounded restart and the SSH maintenance stop.
/usr/bin/openbox --sm-disable &
window_manager_pid=$!
trap 'kill "$window_manager_pid" 2>/dev/null || true; wait "$window_manager_pid" 2>/dev/null || true' EXIT
./.venv/bin/python -m app.ui_qt.main --fullscreen
