# Eutuber Autopilot and Dashboard Plan

Updated 19 Oct 2026 · Matangi · Live version: https://claude.ai/code/artifact/7548ceaf-7686-43f6-a9be-25a37614420a

## How to resume

This doc holds everything needed to continue the Eutuber pipeline if a chat runs out of limit. Paste this doc's link into any new Claude chat in the YoutubeShorts project and say what you want next.

- **Pipeline folder (your PC):** `C:\Users\Neha\Documents\AI\YoutubeShortsInc` (OpenMontage + yt-* skills)
- **To finish scripts:** say "finish the long scripts" (see Script batch below)
- **To see every video's status:** double-click Open-Dashboard.bat in the pipeline folder
- **Thread with the full history:** [Channel analytics check](https://claude.ai/code/project/chan_01HXmkynjg58gcxy3GyhUFB5?thread=cmsg_01HXmkynjg58gcxy3GyhUFB5No4TmC9ReXj4TWfq8U5Yzw)

## Video tracking dashboard

The dashboard is one local HTML page on the PC that lists every video from script to publish. It is built: double-click Open-Dashboard.bat in the YoutubeShortsInc folder to open it.

- **Where:** an HTML file in the YoutubeShortsInc folder, plus a desktop shortcut to open it
- **Refresh:** `YouTube-Autopilot.bat` regenerates it on every run from the saved scripts, render outputs and upload log, so it works without Claude
- **One row per video:** date, Short or long, title, the full script text, YouTube link once uploaded, and status
- **Statuses, in order:**

| Status | Meaning |
| --- | --- |
| Pending | Planned date, no script saved yet |
| Script ready | Script, title and description saved |
| Created | Video rendered, waiting to upload |
| Uploaded | On YouTube, scheduled but not public |
| Public / done | Live on the channel |
| Failed | Render or upload error; reason shown |

## Daily plan (from 18 Oct)

Every day the PC makes 5 Shorts and one ~7-minute landscape video, all ready by 21:00 IST.

| Time (IST) | What happens |
| --- | --- |
| 18:45 | Autopilot makes the 5 Shorts and the long video (about 1 hour) |
| 21:00 | Autopilot uploads the long video first, then the 5 Shorts |
| Staggered slots | Each Short goes public at its own time; never switch to Public by hand |
| 19:30 next day | Long video goes public |

- **Long-video series alternate:** "7 Borders That Make No Sense" style on 18, 20, 22 Oct and so on; "Why India Is Stranger Than You Think" style on 19, 21, 23 Oct and so on. Each day gets a fresh topic in that format.
- **Long video format:** 16:9, 1920×1080, same look as the Shorts, chapters added to the description automatically.
- **Festive:** 2 in-niche festive Shorts per day when a festival is on.
- **PC must be on and plugged in from 18:45 to about 21:30.**

## Autopilot setup

`YouTube-Autopilot.bat` runs the whole day without Claude, using only the saved scripts.

1. Checks the YouTube connection; if the login expired, a popup says to run `Reconnect-YouTube.bat`.
2. Makes today's 5 Shorts and long video if they are missing.
3. Uploads anything waiting, oldest first, and shows a summary.
4. On the first double-click it schedules itself for 18:45 and 21:00 every day.

**Things to know**

- Run `Reconnect-YouTube.bat` once a week; the Google app stays in Testing mode, so logins expire.
- YouTube allows this app about 6 uploads a day, resetting at 12:30 IST. 5 + 1 uses all of it, so a failed upload waits for the next day.
- Windows wake timers are off and the PC sleeps after 60 minutes idle. A sleeping PC misses the run until it is opened.
- Claude sessions cannot publish to YouTube; only the .bat files you run can.
- Visuals come free from NASA, Mixkit and Wikimedia Commons. Voice is Microsoft Edge voices (free).
- Tracking lives in `reports\shorts_tracker.csv`; the YouTube Analytics API is enabled.
- Status 19 Oct: Autopilot is installed and runs daily at 18:45 and 21:00. The 18 Oct upload succeeded at 21:01.

## Script batch progress

As of 19 Oct, all 300 Shorts scripts are saved and the long-video scripts run to 4 Nov; the rest of the long scripts are being written.

| Type | Target | Saved | Covers | Left |
| --- | --- | --- | --- | --- |
| Shorts | 300 | 300 | 18 Oct to 16 Dec | 0 |
| Long videos | 60 | 18 | 18 Oct to 4 Nov | 42 |

- Long scripts from 20 Oct are written to run about 7 minutes.
- Each saved item has script, title, description and comment question, stored by date. Writing more never erases what is already saved.
- If a later session needs to pick this up, say "finish the long scripts".

## Strategy and latest stats

Geography is the channel's strongest topic; the next strategy checkpoint is 22 Oct.

- **Topic mix:** geography 1.5, space 1.0, technology cut to 0.5. Tech only when the payoff is visible on a phone screen.
- **Length:** 30 seconds maximum.
- **Hooks:** open with something viewers can try or see in the first 3 seconds; no question or hype hooks. India-relevant places (68% of viewers are in India).
- **Template:** MrBeast style with a true clickbait sticker, Like sticker, end card and WATCH IT AGAIN.
- **Rules:** true clickbait only, no invented numbers, reports never estimate figures. Standing rules live in `pipeline/standing_rules.md`.
- **Publishing:** staggered auto-public times; one batch going public at once cannibalises views.
- **Backup if Claude lapses:** only script writing needs Claude. Options were the Claude API (about $30–45 a month, estimate), a cheaper model, or a free AI; the 60-day pre-written batch was chosen instead.

**Stats on 17 Oct, 21:26 IST (YouTube API):** 34 Shorts public, 9,256 views, 93 likes, 1 comment, 13 subscribers. Top Shorts: Front Door 1,216 views, remote-through-camera 1,214, Earth's 0,0 1,086.
