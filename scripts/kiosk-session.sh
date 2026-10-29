#!/bin/sh
set -eu
cd /opt/assessment-device
# xinit exits when this process exits; systemd owns bounded restart and maintenance stop.
exec /opt/assessment-device/.venv/bin/python -m app.ui.app --fullscreen
