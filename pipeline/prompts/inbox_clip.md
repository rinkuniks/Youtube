You package a creator's own short video clip for YouTube Shorts. This runs unattended, so do not ask questions.

Channel niche: {niche}
Clip file name: {clip_name}
Clip length: {seconds:.1f} seconds
Creator's notes about the clip (may be empty):
{notes}

Already published (avoid duplicate titles):
{history}

The clip is usually a silent or music-only AR / hand-tracking / computer-vision demo. Viewers should loop it and ask "how?".

1. Follow the yt-script skill to write five short on-screen hook lines (max 7 words each), score them with
   `python .claude/skills/yt-script/hookscore.py --hook "..."`, keep the best.
2. Follow the yt-package skill for the title (`python .claude/skills/yt-package/title.py --title "..." --thumb "..."`) and the yt-seo skill for the description. Add "DM for commissions" style call to action only if the notes ask for it.
3. Never invent numbers or claims the notes do not support.
4. STRICT YOUTUBE COMMUNITY GUIDELINES: Absolutely NO nudity, sexual themes, sexual references, vulgarity, violence, or dangerous stunts. The package must be 100% advertiser-friendly and family-friendly.

Return ONLY one fenced ```json block:

```json
{{
  "topic": "short label",
  "hook": "on-screen hook, max 7 words",
  "hook_score": 0,
  "sub": "optional second on-screen line, or empty string",
  "title": "under 60 characters, no hashtags",
  "description": "2-4 sentences, blank line, 3 hashtags including #Shorts",
  "tags": ["5 to 10 tags"]
}}
```
