# NetworkManager Polkit Policy & Authorization Guide

## Overview

The Raspberry Pi Zero 2 W runs as an educational assessment appliance where the student application executes under the non-root user account (default: `aksh`). 

NetworkManager by default requires administrator authentication via Polkit for operations such as Wi-Fi scanning (`--rescan yes`), network connection activation/deactivation, and profile creation when executed from a non-interactive console or non-seat session.

**Crucial Security Constraints:**
1. Do **NOT** run the Qt application as root (`sudo python -m app.ui_qt.main` is strictly prohibited).
2. Do **NOT** grant blanket passwordless sudo or unrestricted root privileges to the user.
3. Configure narrowly scoped polkit rules specifically restricted to NetworkManager networking actions.

---

## Required NetworkManager Actions

The application requires authorization for the following Polkit actions:
- `org.freedesktop.NetworkManager.network-control`: Activate and deactivate connections.
- `org.freedesktop.NetworkManager.wifi.scan`: Request wireless network scans.
- `org.freedesktop.NetworkManager.wifi.share.protected`: Connect to WPA/WPA2 protected networks.
- `org.freedesktop.NetworkManager.wifi.share.open`: Connect to open Wi-Fi networks.
- `org.freedesktop.NetworkManager.settings.modify.system`: Add or edit system-wide Wi-Fi connections.
- `org.freedesktop.NetworkManager.settings.modify.own`: Manage own network connections.
- `org.freedesktop.NetworkManager.enable-disable-wifi`: Turn Wi-Fi radio on/off.

---

## System Configuration Files

### 1. Polkit JavaScript Rule (Debian 12 Bookworm / polkit >= 0.106)

File: `/etc/polkit-1/rules.d/10-studybuddy-networkmanager.rules`

```javascript
// Narrowly scoped polkit rule for StudyBuddy appliance user 'aksh' and group 'netdev'
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
        if (subject.user === "aksh" || subject.isInGroup("netdev")) {
            return polkit.Result.YES;
        }
    }
});
```

### 2. Polkit Local Authority PKLA (Debian 11 Bullseye / polkit <= 0.105)

File: `/etc/polkit-1/localauthority/50-local.d/10-studybuddy-networkmanager.pkla`

```ini
[Allow aksh and netdev to control NetworkManager without password]
Identity=unix-user:aksh;unix-group:netdev
Action=org.freedesktop.NetworkManager.network-control;org.freedesktop.NetworkManager.wifi.scan;org.freedesktop.NetworkManager.wifi.share.protected;org.freedesktop.NetworkManager.wifi.share.open;org.freedesktop.NetworkManager.settings.modify.system;org.freedesktop.NetworkManager.settings.modify.own;org.freedesktop.NetworkManager.enable-disable-wifi
ResultAny=yes
ResultInactive=yes
ResultActive=yes
```

### 3. NetworkManager Connectivity Check Configuration

File: `/etc/NetworkManager/conf.d/20-connectivity.conf`

```ini
[connectivity]
uri=http://connectivitycheck.gstatic.com/generate_204
interval=60
response=
```

This configuration enables NetworkManager's internal connectivity watchdog so that `nmcli -t -f CONNECTIVITY general status` correctly reports `full` when internet reachability is active, instead of permanently reporting `unknown`.

---

## Installation Commands (One-Time Setup as Administrator)

Run the following commands on the Raspberry Pi once during appliance provisioning:

```bash
# 1. Ensure the user is a member of the netdev group
sudo usermod -aG netdev aksh

# 2. Install Polkit JavaScript rules for modern polkit (Debian 12 Bookworm)
sudo tee /etc/polkit-1/rules.d/10-studybuddy-networkmanager.rules > /dev/null << 'EOF'
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
        if (subject.user === "aksh" || subject.isInGroup("netdev")) {
            return polkit.Result.YES;
        }
    }
});
EOF
sudo chmod 644 /etc/polkit-1/rules.d/10-studybuddy-networkmanager.rules

# 3. Install PKLA rule for legacy polkit compatibility (Debian 11 Bullseye)
sudo mkdir -p /etc/polkit-1/localauthority/50-local.d/
sudo tee /etc/polkit-1/localauthority/50-local.d/10-studybuddy-networkmanager.pkla > /dev/null << 'EOF'
[Allow aksh and netdev to control NetworkManager without password]
Identity=unix-user:aksh;unix-group:netdev
Action=org.freedesktop.NetworkManager.network-control;org.freedesktop.NetworkManager.wifi.scan;org.freedesktop.NetworkManager.wifi.share.protected;org.freedesktop.NetworkManager.wifi.share.open;org.freedesktop.NetworkManager.settings.modify.system;org.freedesktop.NetworkManager.settings.modify.own;org.freedesktop.NetworkManager.enable-disable-wifi
ResultAny=yes
ResultInactive=yes
ResultActive=yes
EOF
sudo chmod 644 /etc/polkit-1/localauthority/50-local.d/10-studybuddy-networkmanager.pkla

# 4. Install NetworkManager connectivity check config
sudo mkdir -p /etc/NetworkManager/conf.d/
sudo tee /etc/NetworkManager/conf.d/20-connectivity.conf > /dev/null << 'EOF'
[connectivity]
uri=http://connectivitycheck.gstatic.com/generate_204
interval=60
EOF

# 5. Reload NetworkManager
sudo systemctl reload NetworkManager
```

---

## Verification Commands (Run as Normal User `aksh`)

Verify as non-root user `aksh` without `sudo`:

```bash
# Verify NM general status and connectivity
nmcli general status

# Verify Wi-Fi radio status
nmcli radio wifi

# Verify device status
nmcli device status

# Verify scan capability without password prompt
nmcli device wifi list --rescan yes

# Verify connection listing
nmcli connection show
```

All commands must succeed without prompting for a password and without returning `Error: Not authorized to control networking`.
