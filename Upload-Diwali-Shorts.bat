@echo off
rem Double-click to upload the 2 Diwali Shorts and make them public right away.
cd /d "%~dp0"
echo Uploading the 2 Diwali Shorts as public, please wait...
"OpenMontage\.venv\Scripts\python.exe" -c "import sys; sys.path.insert(0,'pipeline'); import shorts as s; c=s.cfg(); [print(s.upload(j, c, privacy='public')['url']) for j in ('20261017-2128-diwali-firework-colours-come-from-burnin','20261017-2131-diwali-date-is-set-by-the-new-moon')]"
pause
