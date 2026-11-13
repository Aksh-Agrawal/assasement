#!/bin/sh
set -eu
: "${ASSESS_APP_ROOT:?ASSESS_APP_ROOT is required by updater services}"
exec "$ASSESS_APP_ROOT/current/.venv/bin/python" /usr/local/libexec/assessdev-updater.py "$@"
