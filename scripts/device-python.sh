#!/bin/sh
# Load device configuration for interactive launches as well as background tools.
set -eu
APP_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$APP_ROOT"
if [ -n "${ASSESS_ENV_FILE:-}" ]; then
    config_file=$ASSESS_ENV_FILE
elif [ -f /etc/assessdev/device.env ]; then
    config_file=/etc/assessdev/device.env
else
    config_file=$APP_ROOT/.env
fi
if [ -f "$config_file" ]; then
    set -a
    . "$config_file"
    set +a
fi
exec "$APP_ROOT/.venv/bin/python" "$@"
