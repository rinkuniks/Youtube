"""Community Syndication Generator for Organic Traffic.

Generates safe, high-conversion, policy-compliant community posts for:
- Telegram & WhatsApp Indian GK / UPSC / Study communities
- Reddit (r/geography, r/MapPorn, r/space, r/IndiaInPixels)
- Quora Q&A knowledge spaces
- X / Twitter educational threads

Follows pipeline/standing_rules.md:
- 100% Value-first knowledge sharing (Zero Sub4Sub / No spam)
- Attracts genuine viewers who watch the entire video to boost retention (AVP)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIPE = ROOT / "pipeline"
sys.path.insert(0, str(PIPE))
import shorts  # noqa: E402


def generate_syndication_packs(job: dict) -> dict:
    title = job.get("title") or job.get("topic") or "Mind-Blowing Fact"
    url = job.get("url") or (f"https://youtube.com/watch?v={job['video_id']}" if job.get("lane") == "long" else f"https://youtube.com/shorts/{job.get('video_id', '')}")
    category = job.get("category", "geography")
    lane = job.get("lane", "auto")
    desc = job.get("description", "")
    scenes = job.get("scenes", [])
    
    # Extract core facts from scenes
    facts = [s.get("narration", "") for s in scenes[:4] if s.get("narration")]
    bullets = "\n".join(f"• {f}" for f in facts)

    # 1. Telegram / WhatsApp India GK Format
    tg_post = f"""🇮🇳 *Interesting General Knowledge / Geography Fact* 🧠

*Topic:* {title}

{bullets}

👉 *Watch the full visual explanation here:*
{url}

_Share with your study group or friends who love real geography & science facts!_
"""

    # 2. Reddit Community Post Format
    if category == "geography" or "border" in title.lower() or "island" in title.lower():
        subreddits = "r/geography, r/MapPorn, r/IndiaInPixels"
        reddit_title = f"[Discussion/Fact] {title} — Did you know this exists?"
    elif category == "space":
        subreddits = "r/space, r/astronomy, r/mildlyinteresting"
        reddit_title = f"{title} (Real phenomenon explained)"
    else:
        subreddits = "r/mildlyinteresting, r/damnthatsinteresting, r/technology"
        reddit_title = f"Tested this phone camera trick: {title}"

    reddit_body = f"""**{title}**

Quick breakdown of what happens:
{bullets}

Source & full visual breakdown: {url}

What do you think about this? Have you ever visited or tested this yourself?"""

    # 3. Quora Q&A Format
    quora_q = f"What is the story behind {title}?"
    quora_a = f"""Here is the fascinating factual explanation:

{bullets}

I put together a complete visual breakdown demonstrating how this works in detail:
{url}"""

    # 4. Twitter / X Educational Hook
    x_post = f"""Mind-blowing {category} fact you probably didn't know existed 🧵👇

{title}

{facts[0] if facts else ''}
{facts[1] if len(facts) > 1 else ''}

Watch the quick visual breakdown here:
{url}"""

    return {
        "job_id": job.get("id"),
        "title": title,
        "category": category,
        "lane": lane,
        "url": url,
        "telegram_whatsapp": tg_post.strip(),
        "reddit": {
            "subreddits": subreddits,
            "title": reddit_title,
            "body": reddit_body.strip(),
        },
        "quora": {
            "suggested_question": quora_q,
            "answer": quora_a.strip(),
        },
        "twitter_x": x_post.strip(),
    }


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Generate community distribution posts for uploaded videos")
    ap.add_argument("--job", help="Specific job ID to generate for")
    ap.add_argument("--latest", type=int, default=3, help="Number of latest uploaded videos to generate for")
    args = ap.parse_args()

    jobs = shorts.all_jobs()
    uploaded = [j for j in jobs if j.get("video_id")]

    if args.job:
        target_jobs = [j for j in uploaded if j["id"] == args.job]
    else:
        target_jobs = uploaded[-args.latest:]

    if not target_jobs:
        print("No uploaded jobs found to syndicate.")
        return

    out_file = shorts.ROOT / "reports" / "community_share_packets.md"
    content_lines = ["# Organic Community Syndication Packets", 
                     "Use these safe, policy-compliant copy-paste templates to share in genuine student, geography, and science communities.\n"]

    for j in reversed(target_jobs):
        pack = generate_syndication_packs(j)
        print("=" * 70)
        print(f"PACKET: {pack['title']} ({pack['lane'].upper()})")
        print(f"URL: {pack['url']}")
        print("=" * 70)
        print("\n--- [1] TELEGRAM / WHATSAPP GK & STUDY GROUPS ---")
        print(pack["telegram_whatsapp"])
        print("\n--- [2] REDDIT (Target Subreddits: " + pack["reddit"]["subreddits"] + ") ---")
        print(f"Title: {pack['reddit']['title']}")
        print(pack["reddit"]["body"])
        print("\n--- [3] TWITTER / X THREAD HOOK ---")
        print(pack["twitter_x"])
        print("\n")

        content_lines.append(f"## {pack['title']} ({pack['lane'].upper()})")
        content_lines.append(f"**Video URL:** {pack['url']}\n")
        content_lines.append("### 1. Telegram / WhatsApp Student & GK Groups")
        content_lines.append("```text\n" + pack["telegram_whatsapp"] + "\n```\n")
        content_lines.append(f"### 2. Reddit ({pack['reddit']['subreddits']})")
        content_lines.append(f"**Post Title:** `{pack['reddit']['title']}`\n")
        content_lines.append("```text\n" + pack["reddit"]["body"] + "\n```\n")
        content_lines.append("### 3. Twitter / X")
        content_lines.append("```text\n" + pack["twitter_x"] + "\n```\n")
        content_lines.append("---\n")

    out_file.write_text("\n".join(content_lines), encoding="utf-8")
    print(f"[OK] Full syndication pack saved to: {out_file}\n")


if __name__ == "__main__":
    main()
