# YoutubeShortsInc

Automated YouTube Shorts: Claude picks a topic and writes the script with the yt-* skills, OpenMontage's Remotion renders a 9:16 Short with an offline Piper voice and karaoke captions, and the YouTube Data API uploads it on a daily schedule.

## Folders

| Path | What |
|---|---|
| `pipeline/shorts.py` | The pipeline (commands below) |
| `pipeline/config.yaml` | Niche, voice, upload privacy, schedule time |
| `pipeline/voice.md` | Channel voice every script follows |
| `pipeline/prompts/` | What Claude is asked for each Short |
| `inbox/` | Drop your own clips here (AR demos etc.), optional `same-name.txt` notes |
| `jobs/<id>/` | One folder per Short: `job.json` (title, description, tags, status), `short.mp4` |
| `secrets/` | Your YouTube sign-in (never share or commit) |
| `logs/pipeline.log` | Everything the scheduler did |
| `research/`, `setup/` | Niche plan and tool notes |
| `OpenMontage/` | Video engine (the `ShortVertical` composition was added for this channel) |
| `youtube-agent-skill/` | Source of the yt-* skills (installed in `.claude/skills/`) |

## Commands

Run from this folder:

```powershell
$py = "OpenMontage\.venv\Scripts\python.exe"
& $py pipeline\shorts.py make            # make one auto Short (no upload)
& $py pipeline\shorts.py inbox           # package clips from inbox/
& $py pipeline\shorts.py list            # every Short and its status
& $py pipeline\shorts.py upload JOB_ID   # upload one (uses privacy from config.yaml)
& $py pipeline\shorts.py daily           # what the scheduler runs
```

## One-time YouTube sign-in

1. Go to https://console.cloud.google.com, create a project, and enable **YouTube Data API v3**.
2. Set up the **OAuth consent screen** (External, add your own Gmail as a test user).
3. Create **Credentials > OAuth client ID > Desktop app**, download the JSON, and save it as `secrets\client_secret.json`.
4. Run `& $py pipeline\shorts.py auth` and sign in to the channel in the browser window that opens.

Important: Google locks videos uploaded through a brand-new, unaudited API project to **private**. To post publicly from the pipeline, submit the YouTube API audit form for the project (free). Until then, Shorts upload as private and you flip them to Public in YouTube Studio.

## Schedule

```powershell
powershell -ExecutionPolicy Bypass -File pipeline\install_schedule.ps1 -Time 18:30
```

Each run: packages any inbox clips, makes a new auto Short if nothing is waiting, and uploads `per_run` Shorts. The PC needs to be on (or asleep, it will wake) at that time.
