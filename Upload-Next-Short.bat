@echo off
rem Double-click to upload the oldest rendered (not yet uploaded) Short, as private.
cd /d "%~dp0"
echo Uploading the next Short, please wait...
"OpenMontage\.venv\Scripts\python.exe" -c "import sys; sys.path.insert(0,'pipeline'); import shorts as s; r=[j for j in s.all_jobs() if j.get('status')=='rendered']; print('Nothing waiting to upload.') if not r else s.upload(r[0]['id'], s.cfg())"
pause
