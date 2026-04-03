[app]
title = RDP Glow
package.name = rdpglow
package.domain = com.rdpglow

source.dir = .
source.include_exts = py,png,jpg,kv,json,txt
version = 0.1

requirements = python3,kivy,plyer

orientation = portrait
fullscreen = 0

android.permissions = CAMERA,INTERNET,VIBRATE,WAKE_LOCK
android.api = 33
android.minapi = 24
android.ndk = 25b

[buildozer]
log_level = 2
warn_on_root = 1
