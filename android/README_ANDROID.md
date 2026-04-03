# RDP Glow Android Build Guide

This folder contains the Android version of your app:
- `main.py`: Kivy mobile app
- `engine_mobile.py`: daily logic, tasks, proof rules, reminders config
- `vision_mobile.py`: camera proof capture
- `buildozer.spec`: APK build config

## What this Android build supports
- Mandatory task completion by photo proof (no on/off toggle)
- 30-day daily plan with 2-3 abs/fat-loss exercises per day
- Reminder popups + notifications by task time
- Weather check for 5AM walk/jog (with offline fallback)
- Sleep lock overlay window from configured lock hours
- Tabs: Home, Routine, Guard, Vault, Settings
- Splash/loading animation and smooth transitions

## Important Android limitation
Android apps cannot reliably kill other apps without special device-owner/kiosk setup.
This build uses strict reminders and lock overlays, but not process-kill lockout.

## Build APK (WSL Ubuntu recommended)
Run these inside WSL Ubuntu terminal:

```bash
cd "/mnt/c/Users/rixon/Documents/RDP Glow/android"
sudo apt update
sudo apt install -y python3-pip python3-venv git zip unzip openjdk-17-jdk autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev
python3 -m pip install --user --upgrade pip
python3 -m pip install --user buildozer cython
```

Then build:

```bash
cd "/mnt/c/Users/rixon/Documents/RDP Glow/android"
~/.local/bin/buildozer android debug
```

APK output:

```bash
bin/*.apk
```

Install to phone:

```bash
adb install -r bin/*.apk
```
