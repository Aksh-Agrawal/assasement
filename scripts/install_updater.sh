#!/bin/sh
set -eu

# The privileged active-release tree is separate from the user's writable
# legacy checkout. Both roots are configurable after path inspection.
APP_ROOT=${ASSESS_APP_ROOT:-/opt/questraa-device}
SERVICE_USER=${ASSESS_SERVICE_USER:-aksh}
SERVICE_GROUP=${ASSESS_SERVICE_GROUP:-$SERVICE_USER}
CONFIG_DIR=${ASSESS_CONFIG_DIR:-/etc/assessdev}
DEVICE_ENV=$CONFIG_DIR/device.env
UPDATER_ENV=$CONFIG_DIR/updater.env
SOURCE_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
LEGACY_ROOT=${ASSESS_LEGACY_APP_ROOT:-$SOURCE_ROOT}

if [ "$(id -u)" -ne 0 ]; then
  echo "Run with sudo: sudo sh scripts/install_updater.sh" >&2
  exit 1
fi
for value in "$APP_ROOT" "$LEGACY_ROOT" "$CONFIG_DIR"; do
  case "$value" in *[!A-Za-z0-9_./-]*) echo "Install paths may contain only letters, digits, slash, dot, underscore and dash" >&2; exit 1 ;; esac
done
case "$APP_ROOT" in /*) ;; *) echo "ASSESS_APP_ROOT must be absolute" >&2; exit 1 ;; esac
case "$LEGACY_ROOT" in /*) ;; *) echo "ASSESS_LEGACY_APP_ROOT must be absolute" >&2; exit 1 ;; esac
case "$CONFIG_DIR" in /*) ;; *) echo "ASSESS_CONFIG_DIR must be absolute" >&2; exit 1 ;; esac
case "$SERVICE_USER:$SERVICE_GROUP" in *[!A-Za-z0-9_:-]*) echo "Invalid service account/group" >&2; exit 1 ;; esac
id "$SERVICE_USER" >/dev/null 2>&1 || { echo "Missing service user: $SERVICE_USER" >&2; exit 1; }
getent group "$SERVICE_GROUP" >/dev/null || { echo "Missing service group: $SERVICE_GROUP" >&2; exit 1; }
if [ ! -d "$LEGACY_ROOT/app" ] || [ ! -f "$LEGACY_ROOT/pyproject.toml" ]; then
  echo "Expected the existing application checkout at $LEGACY_ROOT" >&2
  exit 1
fi
if [ ! -s "$CONFIG_DIR/update-public.pem" ]; then
  echo "Install the trusted Ed25519 public key at $CONFIG_DIR/update-public.pem first." >&2
  exit 1
fi

read_setting() {
  file=$1 key=$2
  if [ -f "$file" ]; then
    sed -n "s/^${key}=//p" "$file" | tail -n 1 | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//"
  fi
}

# The old app's effective values win unless the operator explicitly supplies
# replacements. The default reflects its historical cwd-relative var/ paths.
OLD_DATA_DIR=${ASSESS_LEGACY_DATA_DIR:-$(read_setting "$DEVICE_ENV" ASSESS_DATA_DIR)}
OLD_DATA_DIR=${OLD_DATA_DIR:-$LEGACY_ROOT/var}
LEGACY_DB=${ASSESS_LEGACY_SQLITE_PATH:-$(read_setting "$DEVICE_ENV" ASSESS_SQLITE_PATH)}
LEGACY_DB=${LEGACY_DB:-$OLD_DATA_DIR/assessment-device.db}
LEGACY_CREDENTIALS=${ASSESS_LEGACY_CREDENTIAL_PATH:-$(read_setting "$DEVICE_ENV" ASSESS_CREDENTIAL_PATH)}
LEGACY_CREDENTIALS=${LEGACY_CREDENTIALS:-$OLD_DATA_DIR/device_credentials.json}
DATA_ROOT=${ASSESS_DATA_DIR:-/var/lib/assessdev}
DB_PATH=$DATA_ROOT/assessment-device.db
CREDENTIAL_PATH=$DATA_ROOT/device_credentials.json
UPDATE_ROOT=$DATA_ROOT/update
UPDATE_INBOX=$UPDATE_ROOT/inbox
PACK_DIR=${ASSESS_PACK_DIR:-$(read_setting "$DEVICE_ENV" ASSESS_PACK_DIR)}
PACK_DIR=${PACK_DIR:-$LEGACY_ROOT/content}
MEDIA_DIR=${ASSESS_MEDIA_DIR:-$(read_setting "$DEVICE_ENV" ASSESS_MEDIA_DIR)}
MEDIA_DIR=${MEDIA_DIR:-$LEGACY_ROOT/media}
DOWNLOAD_DIR=${ASSESS_DOWNLOAD_DIR:-$(read_setting "$DEVICE_ENV" ASSESS_DOWNLOAD_DIR)}
DOWNLOAD_DIR=${DOWNLOAD_DIR:-$LEGACY_ROOT/runtime/content-downloads/tmp}
LOG_DIR=${ASSESS_LOG_DIR:-$(read_setting "$DEVICE_ENV" ASSESS_LOG_DIR)}
LOG_DIR=${LOG_DIR:-$DATA_ROOT/log}

to_absolute() {
  case "$1" in /*) printf '%s\n' "$1" ;; *) printf '%s/%s\n' "$LEGACY_ROOT" "$1" ;; esac
}
PACK_DIR=$(to_absolute "$PACK_DIR")
MEDIA_DIR=$(to_absolute "$MEDIA_DIR")
DOWNLOAD_DIR=$(to_absolute "$DOWNLOAD_DIR")
LOG_DIR=$(to_absolute "$LOG_DIR")
for value in "$DATA_ROOT" "$LEGACY_DB" "$LEGACY_CREDENTIALS" "$PACK_DIR" "$MEDIA_DIR" "$DOWNLOAD_DIR" "$LOG_DIR"; do
  case "$value" in /*) ;; *) echo "Configured data/content paths must be absolute: $value" >&2; exit 1 ;; esac
  case "$value" in *[!A-Za-z0-9_./-]*) echo "Unsafe characters in configured path: $value" >&2; exit 1 ;; esac
done
if [ ! -f "$LEGACY_DB" ]; then
  echo "Existing database was not found at $LEGACY_DB. Set ASSESS_LEGACY_SQLITE_PATH to the live app's actual database; no state was changed." >&2
  exit 1
fi

# Validate configuration and check the old database before stopping the kiosk.
PYTHONPATH="$SOURCE_ROOT${PYTHONPATH:+:$PYTHONPATH}" python3 - "$APP_ROOT" "$DATA_ROOT" "$LEGACY_DB" "$LEGACY_CREDENTIALS" "$DB_PATH" "$CREDENTIAL_PATH" <<'PY'
import os, pwd, grp, sys
from pathlib import Path
from app.update.layout import configured_installation_paths, validate_existing_database, validate_trusted_app_root

app_root, data_root, source_db, source_credentials, target_db, target_credentials = map(Path, sys.argv[1:])
configured_installation_paths({
    "ASSESS_APP_ROOT": str(app_root), "ASSESS_DATA_DIR": str(data_root),
    "ASSESS_SQLITE_PATH": str(target_db), "ASSESS_CREDENTIAL_PATH": str(target_credentials),
})
service_user = os.environ.get("ASSESS_SERVICE_USER", "aksh")
service_group = os.environ.get("ASSESS_SERVICE_GROUP", service_user)
validate_trusted_app_root(
    app_root, pwd.getpwnam(service_user).pw_uid,
    set(os.getgrouplist(service_user, grp.getgrnam(service_group).gr_gid)),
)
validate_existing_database(source_db)
if source_db.resolve() != target_db.resolve() and target_db.exists():
    raise FileExistsError(f"Refusing to overwrite existing database: {target_db}")
if source_credentials.is_file() and source_credentials.resolve() != target_credentials.resolve() and target_credentials.exists():
    raise FileExistsError(f"Refusing to overwrite existing credentials: {target_credentials}")
print(f"Validated existing SQLite state at {source_db}; target will be {target_db}")
PY

systemctl stop assessdev-ui.service 2>/dev/null || true
systemctl disable --now assessdev-sync.service 2>/dev/null || true
if pgrep -f '[p]ython.*app\.ui_qt\.main' >/dev/null 2>&1 \
  || pgrep -f '[p]ython.*app\.sync\.service' >/dev/null 2>&1; then
  echo "Questraa is still running as $SERVICE_USER. Exit the app before continuing; the database was not modified." >&2
  exit 1
fi

# Copy only after the old process has exited, so no attempts can be written to
# the source after the snapshot. Destination creation is exclusive; source is
# retained unchanged as a recovery copy.
PYTHONPATH="$SOURCE_ROOT${PYTHONPATH:+:$PYTHONPATH}" python3 - "$LEGACY_DB" "$LEGACY_CREDENTIALS" "$DB_PATH" "$CREDENTIAL_PATH" <<'PY'
import sys
from pathlib import Path
from app.update.layout import migrate_existing_state

source_db, source_credentials, target_db, target_credentials = map(Path, sys.argv[1:])
migrate_existing_state(source_db, target_db, source_credentials, target_credentials)
print(f"Migrated verified device data to {target_db}; legacy files remain in place")
PY

install -d -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 0750 "$DATA_ROOT" "$LOG_DIR" \
  "$UPDATE_ROOT" "$UPDATE_INBOX" \
  "$UPDATE_ROOT/downloads" "$UPDATE_ROOT/staged"
install -d -o root -g root -m 0755 "$APP_ROOT" "$APP_ROOT/releases"
install -d -o root -g root -m 0755 "$CONFIG_DIR" /usr/local/libexec
chown "$SERVICE_USER:$SERVICE_GROUP" "$DB_PATH"
chmod 0640 "$DB_PATH"
if [ -f "$CREDENTIAL_PATH" ]; then
  chown "$SERVICE_USER:$SERVICE_GROUP" "$CREDENTIAL_PATH"
  chmod 0600 "$CREDENTIAL_PATH"
fi
chown "root:$SERVICE_GROUP" "$CONFIG_DIR/update-public.pem"
chmod 0640 "$CONFIG_DIR/update-public.pem"

if [ ! -e "$APP_ROOT/current" ]; then
  VERSION=$(sed -n 's/^__version__[[:space:]]*=[[:space:]]*"\([0-9.]*\)".*/\1/p' "$LEGACY_ROOT/app/version.py")
  case "$VERSION" in *.*.*) ;; *) echo "Could not read app version" >&2; exit 1 ;; esac
  RELEASE="$APP_ROOT/releases/$VERSION"
  if [ -e "$RELEASE" ]; then
    echo "Refusing to replace existing release directory: $RELEASE" >&2
    exit 1
  fi
  install -d -o root -g "$SERVICE_GROUP" -m 0755 "$RELEASE"
  cp -a "$LEGACY_ROOT/app" "$LEGACY_ROOT/schemas" "$LEGACY_ROOT/tools" "$RELEASE/"
  cp -a "$LEGACY_ROOT/pyproject.toml" "$LEGACY_ROOT/setup.py" "$LEGACY_ROOT/README.md" "$RELEASE/"
  printf '{"version":"%s"}\n' "$VERSION" > "$RELEASE/release.json"
  python3 -m venv "$RELEASE/.venv"
  "$RELEASE/.venv/bin/python" -m pip install --disable-pip-version-check "$RELEASE[gui]"
  chown -R "root:$SERVICE_GROUP" "$RELEASE"
  ln -s "releases/$VERSION" "$APP_ROOT/current"
elif [ ! -L "$APP_ROOT/current" ] || [ ! -d "$APP_ROOT/current" ]; then
  echo "Refusing unexpected existing current path: $APP_ROOT/current" >&2
  exit 1
else
  ACTIVE_RELEASE=$(readlink -f "$APP_ROOT/current")
  case "$ACTIVE_RELEASE" in "$APP_ROOT"/releases/*) ;; *) echo "Current points outside the managed release directory: $ACTIVE_RELEASE" >&2; exit 1 ;; esac
  if [ ! -f "$ACTIVE_RELEASE/release.json" ]; then
    echo "Current target is missing release metadata: $ACTIVE_RELEASE/release.json" >&2
    exit 1
  fi
fi

if [ ! -f "$DEVICE_ENV" ]; then
  install -o root -g "$SERVICE_GROUP" -m 0640 /dev/null "$DEVICE_ENV"
fi
set_setting() {
  key=$1 value=$2
  temp=$(mktemp "$CONFIG_DIR/device.env.XXXXXX")
  if [ -f "$DEVICE_ENV" ]; then sed "/^${key}=/d" "$DEVICE_ENV" > "$temp"; fi
  printf '%s=%s\n' "$key" "$value" >> "$temp"
  chown "root:$SERVICE_GROUP" "$temp"
  chmod 0640 "$temp"
  mv "$temp" "$DEVICE_ENV"
}
set_setting ASSESS_APP_ROOT "$APP_ROOT"
set_setting ASSESS_DATA_DIR "$DATA_ROOT"
set_setting ASSESS_SQLITE_PATH "$DB_PATH"
set_setting ASSESS_CREDENTIAL_PATH "$CREDENTIAL_PATH"
set_setting ASSESS_PACK_DIR "$PACK_DIR"
set_setting ASSESS_MEDIA_DIR "$MEDIA_DIR"
set_setting ASSESS_DOWNLOAD_DIR "$DOWNLOAD_DIR"
set_setting ASSESS_LOG_DIR "$LOG_DIR"
set_setting ASSESS_UPDATE_DIR "$UPDATE_ROOT"
set_setting ASSESS_UPDATE_INBOX "$UPDATE_INBOX"
set_setting ASSESS_UPDATE_PUBLIC_KEY "$CONFIG_DIR/update-public.pem"
set_setting ASSESS_UPDATE_PLATFORM linux
set_setting ASSESS_UPDATE_ARCH aarch64
set_setting ASSESS_UPDATE_KEY_ID questraa-stable-1

cat > "$UPDATER_ENV" <<EOF
ASSESS_APP_ROOT=$APP_ROOT
ASSESS_DATA_DIR=$DATA_ROOT
ASSESS_UPDATE_DIR=$UPDATE_ROOT
ASSESS_UPDATE_INBOX=$UPDATE_INBOX
ASSESS_UI_UNIT=assessdev-ui.service
ASSESS_SERVICE_USER=$SERVICE_USER
ASSESS_SERVICE_GROUP=$SERVICE_GROUP
EOF
chown root:root "$UPDATER_ENV"
chmod 0600 "$UPDATER_ENV"

install -o root -g root -m 0755 "$SOURCE_ROOT/tools/updater_service.py" /usr/local/libexec/assessdev-updater.py
install -o root -g root -m 0755 "$SOURCE_ROOT/scripts/assessdev-launch-ui.sh" /usr/local/libexec/assessdev-launch-ui
install -o root -g root -m 0755 "$SOURCE_ROOT/scripts/assessdev-run-updater.sh" /usr/local/libexec/assessdev-run-updater
install -o root -g root -m 0755 "$SOURCE_ROOT/scripts/assessdev-run-sync.sh" /usr/local/libexec/assessdev-run-sync
install -o root -g root -m 0755 "$SOURCE_ROOT/scripts/kiosk-session.sh" /usr/local/libexec/assessdev-kiosk-session
render_unit() {
  source=$1 target=$2
  sed -e "s|@SERVICE_USER@|$SERVICE_USER|g" -e "s|@SERVICE_GROUP@|$SERVICE_GROUP|g" \
      -e "s|@APP_ROOT@|$APP_ROOT|g" -e "s|@DATA_ROOT@|$DATA_ROOT|g" "$source" > "$target"
  chown root:root "$target"
  chmod 0644 "$target"
}
render_unit "$SOURCE_ROOT/scripts/systemd/assessdev-ui.service" /etc/systemd/system/assessdev-ui.service
render_unit "$SOURCE_ROOT/scripts/systemd/assessdev-update.service" /etc/systemd/system/assessdev-update.service
render_unit "$SOURCE_ROOT/scripts/systemd/assessdev-recover.service" /etc/systemd/system/assessdev-recover.service
render_unit "$SOURCE_ROOT/scripts/systemd/assessdev-sync.service" /etc/systemd/system/assessdev-sync.service
printf '%s ALL=(root) NOPASSWD: /usr/bin/systemctl --no-block start assessdev-update.service\n' "$SERVICE_USER" \
  > /etc/sudoers.d/assessdev-update
chmod 0440 /etc/sudoers.d/assessdev-update
visudo -cf /etc/sudoers.d/assessdev-update
systemctl daemon-reload
systemctl enable assessdev-recover.service assessdev-ui.service
systemctl start assessdev-ui.service
echo "Questraa updater installed for $SERVICE_USER at $APP_ROOT; existing data is retained at $DB_PATH"
