#!/bin/sh
set -eu
: "${ASSESS_APP_ROOT:?ASSESS_APP_ROOT is required by assessdev-sync.service}"
cd "$ASSESS_APP_ROOT/current"
exec ./.venv/bin/python -m app.sync.service
