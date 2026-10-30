# Raspberry Pi Zero 2 W Production Autostart Guide

This document specifies the target autostart boot flow, environment configuration, and service setup for the PySide6 / Qt Quick educational assessment appliance on Raspberry Pi OS (Bookworm / 64-bit Lite or Desktop with minimal X11/Openbox).

---

## 1. Target Boot Flow

The user experience must be a dedicated appliance:

```text
Raspberry Pi Power-on
      │
      ▼
Linux Kernel Boot (quiet, no terminal cursor, splash screen)
      │
      ▼
Minimal Graphical / Display Environment (X11 + Openbox)
      │
      ▼
Qt Quick Assessment Application Launches in Fullscreen (800×480)
      │
      ▼
Profile Selection
      │
      ▼
Student Home Dashboard
```

The student should **never** see a Linux desktop, terminal, file manager, browser, or taskbar.

---

## 2. Display Environment Configuration

The prototype display is a **5-inch 800 × 480 DSI / HDMI capacitive touchscreen**.

### `/boot/firmware/config.txt` Display Settings:
```ini
# DSI / Touchscreen Configuration (example for standard 5" 800x480 DSI panel)
dtoverlay=vc4-kms-v3d
dtoverlay=goodix-touch,interrupt=4

# HDMI Fallback (if using 800x480 HDMI backpack):
# hdmi_group=2
# hdmi_mode=87
# hdmi_cvt=800 480 60 6 0 0 0
# hdmi_drive=1
```

---

## 3. Required Linux / Raspberry Pi System Packages

Qt 6.5+ XCB platform plugin dynamically links against `libxcb-cursor.so.0`. On Debian Bookworm / Raspberry Pi OS Lite / Desktop, install the required XCB and font libraries:

```bash
sudo apt-get update
sudo apt-get install -y libxcb-cursor0 libxkbcommon-x11-0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xfixes0 libxcb-sync1 libxcb-xinerama0 fonts-dejavu-core
```

---

## 4. Recommended Production Autostart (Openbox / X11 Session)

The existing Raspberry Pi software environment already supports X11 and Openbox. To ensure high stability on the Raspberry Pi Zero 2 W with 512 MB RAM, we configure Openbox to launch the Qt Quick application directly as the primary window without desktop panels or window borders.

### 3.1 Autostart Configuration: `~/.config/openbox/autostart`

Create or update `/home/pi/.config/openbox/autostart`:

```bash
#!/bin/bash
# Disable screen blanking, screensaver, and energy star features
xset s off
xset s noblank
xset -dpms

# Hide the mouse cursor when idle (useful for touchscreens)
unclutter -idle 1 -root &

# Environment settings for Qt Quick on Pi Zero 2 W
export DISPLAY=:0
export QT_QPA_PLATFORM=xcb
# Qt Quick Scene Graph software renderer or OpenGL ES
export QSG_RENDER_LOOP=basic
export QT_QUICK_CONTROLS_STYLE=Basic

# Launch the Assessment Device Qt Application
cd /home/pi/startup
exec /home/pi/startup/.venv/bin/python -m app.ui_qt.main --fullscreen
```

Make it executable:
```bash
chmod +x ~/.config/openbox/autostart
```

---

## 4. Systemd Kiosk Service

For a headless boot setup that automatically starts X11 and Openbox into the assessment application:

Create `/etc/systemd/system/assessment-device.service`:

```ini
[Unit]
Description=Offline Assessment Appliance Kiosk
After=systemd-user-sessions.service network.target

[Service]
User=pi
Group=pi
Type=simple
PAMName=login
WorkingDirectory=/home/pi/startup
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority
ExecStart=/usr/bin/xinit /usr/bin/openbox-session -- :0 vt7 -nocursor
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Enable the service (on physical Raspberry Pi only):
```bash
sudo systemctl daemon-reload
sudo systemctl enable assessment-device.service
```

---

## 5. Development Launch Commands

### Windows / Linux Development Machine:
```bash
python -m app.ui_qt.main
```

### Headless / CI Smoke Test Mode (Offscreen Platform):
```bash
QT_QPA_PLATFORM=offscreen python -m app.ui_qt.main --smoke-test
```

### Raspberry Pi X11 Session:
```bash
DISPLAY=:0 python -m app.ui_qt.main --fullscreen
```

---

## 6. Future EGLFS / KMS Migration Note

Do **not** force EGLFS or direct KMS DRM migration until physical hardware validation proves touch input and memory overhead are superior to X11/Openbox. X11/Openbox provides proven compatibility for touch event mapping and multi-touch calibration on the Pi Zero 2 W.
