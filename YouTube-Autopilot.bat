@echo off
rem YouTube Autopilot: double-click any time. It checks the YouTube connection, makes today's
rem 5 Shorts + 1 long video if they are missing, uploads everything waiting, and shows a summary.
rem The first time, it also sets itself to run every day at 18:45 and 21:00.
cd /d "%~dp0"
schtasks /query /tn "YoutubeShortsInc Daily" /v /fo list | find "autopilot" >nul || powershell -ExecutionPolicy Bypass -File "%~dp0pipeline\install_schedule.ps1"
echo Running YouTube Autopilot, this can take about an hour if videos need making...
set AUTOPILOT_POPUP=0
"OpenMontage\.venv\Scripts\python.exe" "pipeline\shorts.py" autopilot
if errorlevel 2 (
  echo.
  echo Something needs attention: see the summary above.
  echo If YouTube is NOT CONNECTED, double-click Reconnect-YouTube.bat, then run this again.
)
pause
