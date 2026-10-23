@echo off
rem Double-click to refresh and open the video dashboard (scripts, made, uploaded, published).
cd /d "%~dp0"
"OpenMontage\.venv\Scripts\python.exe" "pipeline\dashboard.py" >nul
start "" "%~dp0Video-Dashboard.html"
