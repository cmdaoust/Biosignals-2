@echo off
rem Double-click (or use the desktop shortcut) to back up this PC's Biosignals 2 data to Box.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0backup_to_box.ps1"
