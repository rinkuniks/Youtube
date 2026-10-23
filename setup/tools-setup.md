# Shorts toolkit: OpenMontage + YouTube agent skills

Set up 2026-10-12 in a cloud session. Both repos are public and cloned read-only. Nothing was modified, published or pushed.

## 1. OpenMontage (makes the videos)
Repo: https://github.com/calesthio/OpenMontage (license: AGPLv3)

An agentic video production system that you drive from Claude Code. You describe a video in plain language, and the agent researches it, writes the script, narrates it, gathers or generates visuals, adds music and word-level captions, renders with Remotion/FFmpeg, and self-checks the result. It pauses for your approval at script and storyboard. It also accepts a reference Short ("make something like this, but about X").

**Status:** `make setup` passed (Python deps, Remotion, Piper offline TTS, HyperFrames). A zero-key demo rendered fine: `openmontage-demo.mp4` (1920x1080, 23s).

**Sandbox note:** the cloud container needed a small Chromium wrapper to route Remotion through the session proxy. That's a quirk of this container only. It isn't needed on a normal machine.

**What it costs and needs:**
| Tier | Keys | What you get |
|---|---|---|
| Free | none | Piper narration, Remotion motion graphics, Archive.org/NASA/Wikimedia footage |
| Free keys | PEXELS_API_KEY, PIXABAY_API_KEY, UNSPLASH_ACCESS_KEY | Lots of free stock footage for faceless Shorts |
| Paid (about $1 to $5 per Short) | FAL_KEY (Kling/Veo etc.), ELEVENLABS_API_KEY or GOOGLE_API_KEY, OPENAI_API_KEY | AI-generated clips and premium voices |

Keys go in `OpenMontage/.env`. Budget defaults: $10 total, with approval required for any action over $0.50 (`config.yaml`). Change the default 1920x1080 to 1080x1920 for Shorts, or ask for vertical in the prompt.

## 2. youtube-agent-skill (decides what to make and how to package it)
Repo: https://github.com/Jakeschincariol/youtube-agent-skill (license: MIT)

There are 11 Claude skills plus 6 dependency-free Python tools. No API key or account is needed, and nothing gets published.
- `/yt-viral`: finds outlier videos in your niche, ranked by how far each one beat its own channel
- `/yt-script`: writes 5 hooks from 21 formulas, scores them, then writes the script
- `/yt-package`: lints the title and thumbnail together
- `/yt-shorts`: cuts a long video into Shorts
- `/yt-plan`, `/yt-seo`, `/yt-chapters`, `/yt-comment`, `/yt-edit`, `/yt-retention`, `/yt-audit`

**Status:** installed into Claude's skills folder in this session. I tested `hookscore.py` and `title.py` and both work.
**Setup to do once:** fill in `templates/voice.md` (your tone/persona). Every skill reads it.

## How they fit together for Shorts income
`/yt-viral` (find a proven topic in a niche) → `/yt-script` (hook + 45s script) → OpenMontage (render vertical 9:16 Short with captions) → `/yt-package` + `/yt-seo` (title, description) → **you upload**. After 1–2 weeks, run `/yt-retention` on the YouTube Studio CSV.

## What you need to provide
1. A niche (or let `/yt-viral` help choose).
2. Your voice.md answers (persona, tone).
3. Optional free keys: Pexels, Pixabay (and Unsplash).
4. Optional paid keys if you want AI-generated clips or premium voices, plus a spending cap.
5. A YouTube channel. Uploading stays manual: neither tool publishes.
