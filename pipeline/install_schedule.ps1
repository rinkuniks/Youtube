# Installs (or replaces) the Windows scheduled task that runs the YouTube autopilot.
# Each run: checks the YouTube connection, makes today's 5 Shorts + 1 long video if they are missing,
# then uploads everything waiting. Runs at 18:45 (so all videos are ready by 21:00) and again at 21:00
# as a catch-up; running twice is safe.
# Usage:  powershell -ExecutionPolicy Bypass -File pipeline\install_schedule.ps1 [-Times 18:45,21:00]
# Remove: Unregister-ScheduledTask -TaskName "YoutubeShortsInc Daily" -Confirm:$false
param([string[]]$Times = @("18:45", "21:00"))

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root "OpenMontage\.venv\Scripts\python.exe"
$script = Join-Path $root "pipeline\shorts.py"

$action = New-ScheduledTaskAction -Execute $python -Argument "`"$script`" autopilot" -WorkingDirectory $root
$triggers = $Times | ForEach-Object { New-ScheduledTaskTrigger -Daily -At $_ }
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 3)
Register-ScheduledTask -TaskName "YoutubeShortsInc Daily" -Action $action -Trigger $triggers -Settings $settings -Force | Out-Null
Unregister-ScheduledTask -TaskName "YoutubeShortsInc Prepare" -Confirm:$false -ErrorAction SilentlyContinue
Write-Host "Scheduled 'YoutubeShortsInc Daily' (autopilot) at $($Times -join ', ') every day."
