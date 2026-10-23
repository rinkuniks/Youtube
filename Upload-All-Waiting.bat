@echo off
rem Double-click to upload every rendered Short that is waiting (as private).
cd /d "%~dp0"
echo Uploading all waiting Shorts, please wait...
"OpenMontage\.venv\Scripts\python.exe" -c "import sys; sys.path.insert(0,'pipeline'); import shorts as s; r=[j for j in s.all_jobs() if j.get('status')=='rendered']; print('Nothing waiting to upload.') if not r else [s.upload(j['id'], s.cfg()) for j in r]"
pause
