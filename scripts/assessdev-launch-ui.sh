#!/bin/sh
set -eu
: "${ASSESS_APP_ROOT:?ASSESS_APP_ROOT is required by assessdev-ui.service}"
exec /usr/bin/xinit /usr/local/libexec/assessdev-kiosk-session -- /usr/bin/Xorg :0 vt1 -keeptty -nolisten tcp
