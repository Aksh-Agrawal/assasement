#!/usr/bin/env bash
set -euo pipefail

target="${1:-assess@assessdev-proto1.local}"
destination="${2:-assessment-device}"

if ! command -v rsync >/dev/null 2>&1; then
  echo "rsync is required. On Windows, run this script in WSL or use the documented scp/git alternative." >&2
  exit 2
fi

echo "Deploying repository to ${target}:~/${destination}"
ssh "${target}" "mkdir -p ~/${destination}"
rsync -az --human-readable \
  --exclude='backend/' \
  --exclude='tools/approve_pairing.py' \
  --exclude='tools/revoke_device.py' \
  --include='.env.example' \
  --exclude='.env' \
  --exclude='.env.*' \
  --exclude='artifacts/' \
  --exclude='runtime/' \
  --exclude='*.pem' \
  --exclude='.git/' \
  --exclude='.venv/' \
  --exclude='venv/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='*.db' \
  --exclude='*.db-wal' \
  --exclude='*.db-shm' \
  --exclude='*.sqlite*' \
  --exclude='var/' \
  ./ "${target}:~/${destination}/"

echo "Deployment complete. Existing Pi database files were excluded and no remote delete was used."
