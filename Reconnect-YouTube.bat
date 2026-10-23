@echo off
rem Double-click if uploads stop (Google signs "Testing" apps out every 7 days).
cd /d "%~dp0"
del /q "secrets\youtube_token.json" 2>nul
"OpenMontage\.venv\Scripts\python.exe" pipeline\shorts.py auth
pause
