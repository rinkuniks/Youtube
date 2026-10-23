@echo off
rem Double-click to schedule: 18:45 make 5 Shorts + 1 long video, 21:00 upload them. Safe to run again.
powershell -ExecutionPolicy Bypass -File "%~dp0pipeline\install_schedule.ps1"
pause
