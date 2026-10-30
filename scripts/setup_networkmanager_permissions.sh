#!/usr/bin/env bash
set -euo pipefail

# Setup script for StudyBuddy Raspberry Pi NetworkManager polkit permissions
# Run once with sudo: sudo ./scripts/setup_networkmanager_permissions.sh [username]

TARGET_USER="${1:-${SUDO_USER:-aksh}}"
echo "Configuring NetworkManager permissions for user: ${TARGET_USER}"

# 1. Add user to netdev group
if getent group netdev > /dev/null 2>&1; then
    usermod -aG netdev "${TARGET_USER}"
    echo "Added ${TARGET_USER} to group netdev."
fi

# 2. Modern Polkit rules (Debian 12 Bookworm, polkit >= 0.106)
if [ -d /etc/polkit-1/rules.d ]; then
    cat << EOF > /etc/polkit-1/rules.d/10-studybuddy-networkmanager.rules
polkit.addRule(function(action, subject) {
    var allowedActions = [
        "org.freedesktop.NetworkManager.network-control",
        "org.freedesktop.NetworkManager.wifi.scan",
        "org.freedesktop.NetworkManager.wifi.share.protected",
        "org.freedesktop.NetworkManager.wifi.share.open",
        "org.freedesktop.NetworkManager.settings.modify.system",
        "org.freedesktop.NetworkManager.settings.modify.own",
        "org.freedesktop.NetworkManager.enable-disable-wifi"
    ];

    if (allowedActions.indexOf(action.id) >= 0) {
        if (subject.user === "${TARGET_USER}" || subject.isInGroup("netdev")) {
            return polkit.Result.YES;
        }
    }
});
EOF
    chmod 644 /etc/polkit-1/rules.d/10-studybuddy-networkmanager.rules
    echo "Installed /etc/polkit-1/rules.d/10-studybuddy-networkmanager.rules"
fi

# 3. Legacy Polkit PKLA (Debian 11 Bullseye, polkit <= 0.105)
mkdir -p /etc/polkit-1/localauthority/50-local.d/
cat << EOF > /etc/polkit-1/localauthority/50-local.d/10-studybuddy-networkmanager.pkla
[Allow aksh and netdev to control NetworkManager without password]
Identity=unix-user:${TARGET_USER};unix-group:netdev
Action=org.freedesktop.NetworkManager.network-control;org.freedesktop.NetworkManager.wifi.scan;org.freedesktop.NetworkManager.wifi.share.protected;org.freedesktop.NetworkManager.wifi.share.open;org.freedesktop.NetworkManager.settings.modify.system;org.freedesktop.NetworkManager.settings.modify.own;org.freedesktop.NetworkManager.enable-disable-wifi
ResultAny=yes
ResultInactive=yes
ResultActive=yes
EOF
chmod 644 /etc/polkit-1/localauthority/50-local.d/10-studybuddy-networkmanager.pkla
echo "Installed /etc/polkit-1/localauthority/50-local.d/10-studybuddy-networkmanager.pkla"

# 4. NetworkManager connectivity watchdog
mkdir -p /etc/NetworkManager/conf.d/
cat << 'EOF' > /etc/NetworkManager/conf.d/20-connectivity.conf
[connectivity]
uri=http://connectivitycheck.gstatic.com/generate_204
interval=60
EOF
chmod 644 /etc/NetworkManager/conf.d/20-connectivity.conf
echo "Installed /etc/NetworkManager/conf.d/20-connectivity.conf"

# 5. Reload NetworkManager if running
if systemctl is-active --quiet NetworkManager; then
    systemctl reload NetworkManager || true
    echo "Reloaded NetworkManager."
fi

echo "NetworkManager permissions configuration completed successfully."
