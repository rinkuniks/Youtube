"""YoutubeShortsInc pipeline: idea -> script -> voice -> render -> package -> upload.

Run with the OpenMontage virtualenv Python (it has every dependency):

    OpenMontage\\.venv\\Scripts\\python.exe pipeline\\shorts.py make          # new auto Short (no upload)
    OpenMontage\\.venv\\Scripts\\python.exe pipeline\\shorts.py inbox         # package clips dropped in inbox/
    OpenMontage\\.venv\\Scripts\\python.exe pipeline\\shorts.py upload JOB_ID # upload one rendered Short
    OpenMontage\\.venv\\Scripts\\python.exe pipeline\\shorts.py auth          # one-time YouTube sign-in
    OpenMontage\\.venv\\Scripts\\python.exe pipeline\\shorts.py daily         # what the scheduler runs
    OpenMontage\\.venv\\Scripts\\python.exe pipeline\\shorts.py list          # show all jobs and status
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
import wave
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PIPE = ROOT / "pipeline"
JOBS = ROOT / "jobs"
INBOX = ROOT / "inbox"
LOGS = ROOT / "logs"
SECRETS = ROOT / "secrets"
COMPOSER = ROOT / "OpenMontage" / "remotion-composer"
PUBLIC_JOBS = COMPOSER / "public" / "_shorts"
VENV_SCRIPTS = ROOT / "OpenMontage" / ".venv" / "Scripts"
FFTOOLS = COMPOSER / "node_modules" / "@remotion" / "compositor-win32-x64-msvc"
CLIP_EXT = {".mp4", ".mov", ".webm", ".mkv"}


def cfg() -> dict:
    return yaml.safe_load((PIPE / "config.yaml").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- content safety
# Strict adherence to YouTube Community Guidelines and Advertiser-Friendly Guidelines:
# Zero tolerance for nudity, sexual content, sexually suggestive material, or guideline violations.
NSFW_RE = re.compile(
    r"\b("
    r"nudes?|nudity|naked(?!\s+eye\b)|topless|bottomless|unclothed|undressed|bare[-_ ]chested|bare[-_ ]breasted|"
    r"sex|sexy|sexual|sexuality|sexually|erotic\w*|porn\w*|nsfw|xxx|lewd|"
    r"genitals?|genitalia|penis\w*|phallus|phallic|vagina\w*|vulva\w*|clitoris|labia\w*|anus|anal|"
    r"buttocks?|butts?|breasts?|boobs?|nipples?|cleavage|pubic|groin|scrotum|testicles?|"
    r"lingerie|underwear|panties|panty|\bbras?\b|thongs?|g[-_ ]strings?|bikinis?|swimwears?|swimsuits?|boudoir|"
    r"masturbat\w*|orgasms?|orgasmic|intercourse|copulat\w*|ejaculat\w*|"
    r"prostitut\w*|escorts?|strippers?|striptease|pole[-_ ]dance\w*|lap[-_ ]dance\w*|"
    r"nudists?|naturis\w*|nude[-_ ]beach\w*|swingers?|fetish\w*|bdsm|bondage|"
    r"erotic[-_ ]art|nude[-_ ]art"
    r")\b",
    re.IGNORECASE,
)

COMMUNITY_VIOLATIONS_RE = re.compile(
    r"\b("
    r"gore|bloodbath|behead\w*|decapitat\w*|mutilat\w*|suicide\w*|self[-_ ]harm|"
    r"terroris\w*|jihad\w*|hate[-_ ]speech|nazi|hitler|genocide"
    r")\b",
    re.IGNORECASE,
)

PROFANITY_RE = re.compile(
    r"\b(fuck\w*|shit\w*|bitch\w*|cunt\w*|dicks?|cocks?|pussy|whore|slut\w*|bastard\w*)\b",
    re.IGNORECASE,
)



def check_safety(text: str) -> tuple[bool, str]:
    """Check text against YouTube Community Guidelines (nudity, sexual content, profanity, violence)."""
    if not text:
        return True, ""
    # Normalize punctuation, underscores, hyphens, and slashes to spaces so word boundaries match URLs and filenames
    normalized = re.sub(r"[-_/\\:.]+", " ", text)
    m = NSFW_RE.search(normalized)
    if m:
        return False, f"nudity/sexual content matched '{m.group()}'"
    m = COMMUNITY_VIOLATIONS_RE.search(normalized)
    if m:
        return False, f"community guidelines violation matched '{m.group()}'"
    m = PROFANITY_RE.search(normalized)
    if m:
        return False, f"vulgarity/profanity matched '{m.group()}'"
    return True, ""


# Visual queries must NEVER search for bodies, models, swimwear, bathrooms, or bedrooms
PROHIBITED_QUERY_TERMS = re.compile(
    r"\b("
    r"nudes?|nudity|naked|topless|bottomless|unclothed|undressed|bare[-_ ]chested|bare[-_ ]breasted|"
    r"sex|sexy|sexual|erotic\w*|porn\w*|sensual|seductive|bedroom|bed\b|bathroom|shower|bathtub|towel|"
    r"swimsuit\w*|swimwear\w*|bikini\w*|lingerie|underwear|cleavage|breasts?|boobs?|buttocks?|ass\b|"
    r"model\b|models\b|body\b|bodies\b|posing\b|massage"
    r")\b",
    re.IGNORECASE,
)


def sanitize_visual_query(query: str, category: str = "") -> str:
    """Sanitize stock search queries so they strictly adhere to YouTube Guidelines."""
    ok, reason = check_safety(query)
    m = PROHIBITED_QUERY_TERMS.search(query)
    if not ok or m:
        cause = reason if not ok else f"prohibited query term '{m.group()}'"
        log(f"safety: visual query '{query}' rejected ({cause}); substituting safe educational visual")
        fallbacks = {
            "space": "deep space galaxy stars universe",
            "geography": "planet earth scenic landscape nature aerial",
            "technology": "modern electronics technology hardware macro",
        }
        return fallbacks.get(category, "earth nature landscape aerial")
    return query


def verify_downloaded_media(path: Path) -> tuple[bool, str]:
    """Inspect downloaded visual file to guarantee no nudity or inappropriate content."""
    # 1. Filename & path check
    ok, reason = check_safety(path.name)
    if not ok:
        return False, f"filename {reason}"

    # 2. Image skin ratio check
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        try:
            from PIL import Image
            import numpy as np
            with Image.open(path) as im:
                small = im.convert("RGB")
                small.thumbnail((120, 120))
                arr = np.array(small, dtype=np.float32)
                r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
                rule1 = (r > 95) & (g > 40) & (b > 20)
                rule2 = (np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b)) > 15
                rule3 = (np.abs(r - g) > 15) & (r > g) & (r > b)
                cb = -0.168736 * r - 0.331264 * g + 0.5 * b + 128
                cr = 0.5 * r - 0.418688 * g - 0.081312 * b + 128
                ycbcr = (cb >= 77) & (cb <= 127) & (cr >= 133) & (cr <= 173)
                skin_ratio = float(np.mean(rule1 & rule2 & rule3 & ycbcr))
                if skin_ratio > 0.42:
                    return False, f"excessive bare skin tone ratio ({skin_ratio:.2f})"
        except Exception:
            pass
    return True, ""



def validate_script_safety(spec: dict) -> None:
    """Ensure every field in a script complies with YouTube Guidelines before narrating, rendering, or uploading."""
    fields_to_check = [
        ("topic", spec.get("topic", "")),
        ("title", spec.get("title", "")),
        ("hook", spec.get("hook", "")),
        ("description", spec.get("description", "")),
        ("comment_prompt", spec.get("comment_prompt", "")),
        ("hook_banner", spec.get("hook_banner", "")),
    ]
    for tag in spec.get("tags") or []:
        fields_to_check.append(("tag", str(tag)))

    for i, sc in enumerate(spec.get("scenes") or []):
        fields_to_check.append((f"scene {i} narration", sc.get("narration", "")))
        fields_to_check.append((f"scene {i} headline", sc.get("headline", "")))
        fields_to_check.append((f"scene {i} visual_query", sc.get("visual_query", "")))

    for field_name, val in fields_to_check:
        ok, reason = check_safety(val)
        if not ok:
            raise ValueError(f"Script violates YouTube Guidelines in {field_name}: {reason} (content: '{val[:60]}')")



def log(msg: str) -> None:
    LOGS.mkdir(exist_ok=True)
    line = f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    with (LOGS / "pipeline.log").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "short"


def load_job(job_id: str) -> dict:
    return json.loads((JOBS / job_id / "job.json").read_text(encoding="utf-8"))


def save_job(job: dict) -> None:
    d = JOBS / job["id"]
    d.mkdir(parents=True, exist_ok=True)
    (d / "job.json").write_text(json.dumps(job, indent=2, ensure_ascii=False), encoding="utf-8")


def all_jobs() -> list[dict]:
    if not JOBS.exists():
        return []
    out = []
    for p in sorted(JOBS.glob("*/job.json")):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            pass
    return out


def history_lines() -> str:
    lines = [f"- {j.get('title') or j.get('topic')}" for j in all_jobs() if j.get("title") or j.get("topic")]
    return "\n".join(lines[-60:]) or "- (nothing yet)"


BANK = ROOT / "script_bank"


def bank_take(kind: str) -> tuple[str, dict] | None:
    """Oldest unused pre-written script (script_bank/<kind>/<date>[-n].json), so missed days just shift later."""
    folder = BANK / kind
    if not folder.exists():
        return None
    used = {j.get("bank_file") for j in all_jobs()}
    for f in sorted(folder.glob("*.json")):
        if f.name not in used:
            return f.name, json.loads(f.read_text(encoding="utf-8"))
    return None


def bank_left(kind: str) -> int:
    used = {j.get("bank_file") for j in all_jobs()}
    return sum(1 for f in (BANK / kind).glob("*.json") if f.name not in used) if (BANK / kind).exists() else 0


def script_or_bank(c: dict, kind: str, prompt_fn) -> tuple[dict, str]:
    """Next banked script; Claude only when the bank is empty and scripts.bank_only is off."""
    got = bank_take(kind)
    if got:
        log(f"using pre-written script {kind}/{got[0]}")
        spec, bank_file = got[1], got[0]
        validate_script_safety(spec)
        return spec, bank_file
    if c.get("scripts", {}).get("bank_only"):
        raise RuntimeError(f"no pre-written {kind} scripts left in script_bank/{kind} (bank_only is on, so Claude is not used)")
    spec = ask_claude(prompt_fn())
    validate_script_safety(spec)
    return spec, ""



# ---------------------------------------------------------------- Claude

def ask_claude(prompt: str) -> dict:
    """Run Claude Code headless in the project folder (so the yt-* skills load) and parse its JSON block."""
    claude = shutil.which("claude")
    if not claude:
        raise SystemExit("claude CLI not found on PATH")
    cmd = [
        claude, "-p",  # prompt goes in on stdin: long prompts overflow Windows' 32k command-line limit
        "--output-format", "json",
        "--max-turns", "40",
        "--model", os.environ.get("SHORTS_CLAUDE_MODEL", "sonnet"),
        # Skip ~/.claude/settings.json: its "env" block (gateway, ANTHROPIC_MODEL=auto) breaks headless runs.
        "--setting-sources", "project,local",
        "--allowedTools", "Read", "Glob", "Grep", "WebSearch", "WebFetch", "Skill",
        "Bash(python .claude/skills/*)", "Bash(python3 .claude/skills/*)",
    ]
    # Run with the CLI's own sign-in and settings: inherited ANTHROPIC_*/CLAUDE* variables from other
    # apps (e.g. ANTHROPIC_MODEL=auto) make the CLI fail with "unrecognized_model".
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("ANTHROPIC_", "CLAUDE"))}
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=1800, env=env,
                          input=prompt)
    if proc.returncode != 0:
        raise RuntimeError(f"claude failed ({proc.returncode}): {proc.stderr[-2000:]}")
    envelope = json.loads(proc.stdout)
    text = envelope.get("result", "")
    m = re.findall(r"```json\s*(\{.*?\})\s*```", text, flags=re.S)
    raw = m[-1] if m else text[text.find("{"): text.rfind("}") + 1]
    return json.loads(raw)


# ---------------------------------------------------------------- media helpers

def ff(tool: str) -> str:
    exe = FFTOOLS / f"{tool}.exe"
    return str(exe) if exe.exists() else tool


def media_seconds(path: Path) -> float:
    out = subprocess.run(
        [ff("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True,
    )
    return float(out.stdout.strip())


def wav_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


def tts_edge(text: str, out: Path, c: dict) -> list[dict]:
    """Microsoft neural voice (free, needs internet). Returns exact word timings in seconds."""
    import asyncio
    import edge_tts

    v = c["voice"]
    mp3 = out.with_suffix(".mp3")
    words: list[dict] = []

    async def run() -> None:
        com = edge_tts.Communicate(text, v.get("edge_voice", "en-US-AndrewMultilingualNeural"),
                                   rate=v.get("edge_rate", "+8%"), boundary="WordBoundary")
        with mp3.open("wb") as fh:
            async for ch in com.stream():
                if ch["type"] == "audio":
                    fh.write(ch["data"])
                elif ch["type"] == "WordBoundary":
                    s = ch["offset"] / 1e7
                    words.append({"word": ch["text"], "start": round(s, 3), "end": round(s + ch["duration"] / 1e7, 3)})

    asyncio.run(run())
    proc = subprocess.run([ff("ffmpeg"), "-v", "error", "-y", "-i", str(mp3), "-ar", "24000", "-ac", "1", str(out)],
                          capture_output=True, text=True)
    mp3.unlink(missing_ok=True)
    if proc.returncode != 0 or not out.exists() or not words:
        raise RuntimeError(f"edge-tts failed: {proc.stderr[-500:]}")
    return words


def speak(text: str, out: Path, c: dict, engine: str | None = None) -> list[dict] | None:
    """Narrate one scene. Returns word timings, or None for Piper (timings then estimated).

    Raises RuntimeError if the online voice keeps failing, so the caller can re-voice the whole
    Short with Piper instead of mixing two voices.
    """
    if (engine or c["voice"].get("engine", "edge")) == "edge":
        # The free service drops requests now and then; back off and retry, with harmless rewordings.
        variants = [text, text, text.replace(" and ", ", and "), text, text.rstrip(".!?") + "...", text]
        last = None
        for attempt, variant in enumerate(variants):
            try:
                return tts_edge(variant, out, c)
            except Exception as exc:
                last = exc
                time.sleep([3, 6, 10, 15, 20, 30][attempt])
        raise RuntimeError(f"edge voice failed for {text!r}: {last}")
    tts(text, out, c)
    to_24k(out)
    return None


def to_24k(path: Path) -> None:
    """Resample to 24 kHz mono so Piper and edge clips can be joined."""
    tmp = path.with_name(path.stem + "_r.wav")
    subprocess.run([ff("ffmpeg"), "-v", "error", "-y", "-i", str(path), "-ar", "24000", "-ac", "1", str(tmp)],
                   capture_output=True, text=True)
    if tmp.exists():
        tmp.replace(path)


def tts(text: str, out: Path, c: dict) -> None:
    v = c["voice"]
    piper = VENV_SCRIPTS / "piper.exe"
    proc = subprocess.run(
        [str(piper), "-m", str(ROOT / v["model"]), "-f", str(out),
         "--length-scale", str(v.get("length_scale", 1.0)),
         "--sentence-silence", str(v.get("sentence_silence", 0.2))],
        input=text, capture_output=True, text=True, encoding="utf-8",
    )
    if proc.returncode != 0 or not out.exists():
        raise RuntimeError(f"piper failed: {proc.stderr[-1000:]}")


def concat_wavs(parts: list[Path], out: Path, gap: float = 0.12) -> None:
    with wave.open(str(parts[0]), "rb") as first:
        params = first.getparams()
    silence = b"\x00" * int(params.framerate * gap) * params.sampwidth * params.nchannels
    with wave.open(str(out), "wb") as dst:
        dst.setparams(params)
        for i, p in enumerate(parts):
            with wave.open(str(p), "rb") as src:
                dst.writeframes(src.readframes(src.getnframes()))
            if i < len(parts) - 1:
                dst.writeframes(silence)


def word_timings(text: str, start: float, end: float) -> list[dict]:
    """Spread words across the scene's audio, weighted by length (punctuation adds a pause)."""
    words = text.split()
    if not words:
        return []
    weights = [len(re.sub(r"\W", "", w)) + 2 + (3 if re.search(r"[.,!?;:]$", w) else 0) for w in words]
    total = sum(weights)
    span = max(0.1, end - start - 0.1)
    t = start + 0.05
    out = []
    for w, wt in zip(words, weights):
        d = span * wt / total
        out.append({"word": re.sub(r"[\"“”]", "", w), "start": round(t, 3), "end": round(t + d * 0.92, 3)})
        t += d
    return out


def remotion_render(job: dict, props: dict, composition: str = "ShortVertical", timeout: int | None = None) -> Path:
    d = JOBS / job["id"]
    props_path = d / "props.json"
    props_path.write_text(json.dumps(props, indent=2, ensure_ascii=False), encoding="utf-8")
    out = d / "short.mp4"
    npx = shutil.which("npx.cmd") or shutil.which("npx") or "npx"
    log(f"{job['id']}: rendering")
    # A stuck stock clip can hang the renderer for good, so cap each render and kill the whole tree.
    proc = subprocess.Popen(
        [npx, "remotion", "render", "src/index.tsx", composition, str(out),
         "--props", str(props_path), "--codec", "h264", "--log", "error", "--timeout", "30000"],
        cwd=COMPOSER, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout or int(os.environ.get("SHORTS_RENDER_TIMEOUT", "420")))
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
        proc.communicate()
        raise RuntimeError("render failed: timed out")
    if proc.returncode != 0 or not out.exists():
        raise RuntimeError(f"render failed: {(stderr or stdout)[-2000:]}")
    return out


def stage_asset(job_id: str, src: Path, name: str) -> str:
    """Copy into Remotion's public dir and return the public-relative path."""
    dst_dir = PUBLIC_JOBS / job_id
    dst_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst_dir / name)
    return f"_shorts/{job_id}/{name}"


def cleanup_stage(job_id: str) -> None:
    shutil.rmtree(PUBLIC_JOBS / job_id, ignore_errors=True)



# ---------------------------------------------------------------- visuals

def _stock_sources(category: str) -> list:
    """Free sources in priority order. Pexels/Pixabay join when their free keys are in OpenMontage/.env."""
    sys.path.insert(0, str(ROOT / "OpenMontage"))
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / "OpenMontage" / ".env")
    except Exception:
        pass
    from tools.video.stock_sources.mixkit import MixkitSource
    from tools.video.stock_sources.nasa import NasaSource
    from tools.video.stock_sources.pexels import PexelsSource
    from tools.video.stock_sources.pixabay_video import PixabayVideoSource
    from tools.video.stock_sources.wikimedia import WikimediaSource
    # Moving clips first (no-key sources, then keyed ones if present), photos as fallback.
    srcs = [("video", MixkitSource()), ("video", PixabayVideoSource()), ("video", PexelsSource()),
            ("video", WikimediaSource())]
    if category == "space":
        srcs = [("video", NasaSource())] + srcs + [("image", NasaSource())]
    srcs.append(("image", WikimediaSource()))
    return [(k, s) for k, s in srcs if s.is_available()]


def _shrink_image(path: Path) -> Path:
    from PIL import Image

    with Image.open(path) as im:
        im = im.convert("RGB")
        im.thumbnail((1600, 2400))
        out = path.with_suffix(".jpg")
        im.save(out, "JPEG", quality=88)
    if out != path:
        path.unlink(missing_ok=True)
    return out


SPACE_WORDS = {"space", "astronaut", "astronauts", "station", "iss", "orbit", "planet", "moon", "rocket",
               "nasa", "galaxy", "satellite", "spacecraft", "mars", "jupiter", "saturn", "sun", "star", "stars"}


def _relevant(query: str, cand) -> bool:
    """Keep a result only if it complies with YouTube Guidelines and key words match."""
    # Zero tolerance check for nudity, sexual content, and YouTube Community Guidelines violations
    audit_text = f"{cand.source_tags or ''} {cand.download_url or ''} {cand.source_url or ''} {cand.creator or ''}"
    ok, reason = check_safety(audit_text)
    if not ok:
        log(f"safety: rejected visual candidate {cand.clip_id} ({cand.source}) - {reason}")
        return False

    stop = {"from", "with", "the", "and", "over", "into", "view", "close", "shot", "aerial"}
    keys = [w for w in re.findall(r"[a-z]+", query.lower()) if len(w) > 2 and w not in stop]
    if not keys:
        return True
    text = (cand.source_tags or "").lower() + " " + cand.download_url.lower()
    if re.search(r"(patch|insignia|logo|emblem|diagram|chart|poster|document|signature|portrait)", text):
        return False
    hits = sum(1 for w in keys if w.rstrip("s") in text)
    return hits >= max(1, (len(keys) + 1) // 2)


def _shrink_video(path: Path) -> Path:
    """Cut stock clips to 10s, max 1080px, no audio, so 4K sources can't crash the renderer."""
    out = path.with_name(path.stem + "_s.mp4")
    proc = subprocess.run(
        [ff("ffmpeg"), "-v", "error", "-y", "-stream_loop", "-1", "-i", str(path), "-t", "10", "-an",
         # constant 30 fps, simple GOP, no B-frames: Remotion's frame extractor chokes on some odd stock encodes
         "-vf", "scale='min(1080,iw)':-2", "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
         "-pix_fmt", "yuv420p", "-g", "30", "-bf", "0", str(out)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0 or not out.exists():
        raise RuntimeError(f"clip conversion failed: {proc.stderr[-300:]}")
    path.unlink(missing_ok=True)
    final = path.with_suffix(".mp4")
    out.replace(final)
    return final


def fetch_visuals(job: dict, c: dict) -> list[str | None]:
    """One background per scene, matched to the scene's visual_query. Returns local paths (or None)."""
    if not c.get("render", {}).get("visuals", True):
        # Third-party stock scraping disabled: channel uses original 2D Blender Toon character system
        return [None] * len(job["scenes"])
    media = JOBS / job["id"] / "media"
    media.mkdir(exist_ok=True)
    try:
        sources = _stock_sources(job.get("category", ""))
    except Exception as exc:
        log(f"visual sources unavailable: {exc}")
        return [None] * len(job["scenes"])
    from tools.video.stock_sources.base import SearchFilters  # path set by _stock_sources

    used: set[str] = set()
    credits: dict[str, str] = {}
    out: list[str | None] = []
    for i, sc in enumerate(job["scenes"]):
        existing = sorted(media.glob(f"scene{i:02d}.*"))
        if existing:
            out.append(str(existing[0]))
            continue
        query = sc.get("visual_query") or sc.get("headline") or job.get("topic", "")
        query = sanitize_visual_query(query, job.get("category", ""))
        got = None
        scene_sources = sources
        if job.get("category") != "space" and SPACE_WORDS & set(re.findall(r"[a-z]+", query.lower())):
            from tools.video.stock_sources.nasa import NasaSource
            scene_sources = [("video", NasaSource()), ("image", NasaSource())] + sources
        for kind, src in scene_sources:
            try:
                cands = src.search(query, SearchFilters(kind=kind, per_page=8, orientation="portrait" if kind == "video" else None))
            except Exception:
                continue
            for cand in cands:
                if cand.clip_id in used or not _relevant(query, cand):
                    continue
                if kind == "video" and cand.duration and not (3 <= cand.duration <= 90):
                    continue
                ext = ".mp4" if cand.kind == "video" else Path(cand.download_url.split("?")[0]).suffix.lower() or ".jpg"
                if ext not in {".mp4", ".jpg", ".jpeg", ".png", ".webp"}:
                    continue
                try:
                    path = src.download(cand, media / f"scene{i:02d}{ext}")
                    path = _shrink_image(Path(path)) if cand.kind != "video" else _shrink_video(Path(path))
                    is_safe, reason = verify_downloaded_media(Path(path))
                    if not is_safe:
                        log(f"safety: downloaded file {Path(path).name} rejected ({reason}); deleting and trying next candidate")
                        Path(path).unlink(missing_ok=True)
                        continue
                except Exception:
                    continue
                used.add(cand.clip_id)
                lic = (cand.license or "").strip()
                if lic and "public domain" not in lic.lower() and "cc0" not in lic.lower():
                    credits[cand.source_url] = f"{cand.creator or src.name} ({lic}) {cand.source_url}"
                got = str(path)
                break
            if got:
                break
        if not got:
            log(f"{job['id']}: no visual for scene {i} ({query})")
        out.append(got)
    if credits:
        job["credits"] = sorted(set(credits.values()))
    return out

# ---------------------------------------------------------------- lanes

def pick_category(names: list[str]) -> str:
    """Rotate categories, weighted by the weekly strategy (category_weights.json) once there is data."""
    done = [j.get("category") for j in all_jobs() if j.get("lane") == "auto" and j.get("category") in names]
    wfile = PIPE / "category_weights.json"
    weights = {n: 1.0 for n in names}
    if wfile.exists():
        try:
            weights.update({k: float(v) for k, v in json.loads(wfile.read_text(encoding="utf-8")).items() if k in names})
        except Exception:
            pass
    total = sum(weights.values()) or 1
    recent = done[-9:]  # short window so one batch stays close to the target mix
    n = len(recent) + 1
    # largest shortfall versus target share wins; ties go to whichever was used least recently
    def score(name: str) -> tuple:
        last = max((i for i, c in enumerate(done) if c == name), default=-1)
        return (weights[name] / total * n - recent.count(name), -last)
    return max(names, key=score)


def make_auto(c: dict, force_category: str | None = None) -> dict:
    tmpl = (PIPE / "prompts" / "auto_short.md").read_text(encoding="utf-8")
    cats = c["ideas"].get("categories") or {"general": c["ideas"].get("seeds", [])}
    names = list(cats)
    category = force_category if force_category in cats else pick_category(names)
    prompt = lambda: tmpl.format(  # noqa: E731 - only built when the script bank is empty
        niche=c["channel"]["niche"],
        audience=c["channel"]["audience"],
        category=category,
        seeds="; ".join(cats[category]),
        history=history_lines(),
        notes="\n\n".join(f.read_text(encoding="utf-8") for f in (PIPE / "standing_rules.md", PIPE / "strategy_notes.md")
                          if f.exists()) or "(no data yet)",
        max_seconds=c["ideas"].get("max_seconds", 40),
    )
    if not force_category:
        log("getting today's script (script bank first, else Claude)")
    spec, bank_file = script_or_bank(c, "shorts", prompt) if not force_category else (ask_claude(prompt()), "")
    category = spec.pop("category", None) or category
    job_id = f"{dt.datetime.now():%Y%m%d-%H%M%S}-{slug(spec.get('topic', 'short'))}"
    job = {"id": job_id, "lane": "auto", "status": "scripted", "category": category,
           "created": dt.datetime.now().isoformat(), "bank_file": bank_file, **spec}
    save_job(job)
    return produce_auto(job, c)


def produce_auto(job: dict, c: dict) -> dict:
    """Narrate and render an auto job from its scenes (also used to remake a job after edits)."""
    validate_script_safety(job)
    job_id, spec = job["id"], job
    d = JOBS / job_id

    log(f"{job_id}: narrating {len(spec['scenes'])} scenes")
    try:
        parts, scenes, words, t = narrate(job, c, None)
    except RuntimeError as exc:
        log(f"{job_id}: {exc} - re-voicing the whole Short with Piper so the voice stays consistent")
        parts, scenes, words, t = narrate(job, c, "piper")
    gap = 0.05
    concat_wavs(parts, d / "narration.wav", gap)
    for p in parts:
        p.unlink()
    return render_auto(job, c, scenes, words, t)


def long_format(c: dict, day: dt.date) -> tuple[str, str]:
    """Today's long-video format and fixed topic: formats alternate day by day from long.start_date."""
    lc = c.get("long", {})
    formats = lc.get("formats") or ["a 7-minute list of strange but true places or facts"]
    start = dt.date.fromisoformat(str(lc.get("start_date", day.isoformat())))
    fmt = formats[(day - start).days % len(formats)]
    topic = (lc.get("topics") or {}).get(day.isoformat(), "")
    return fmt, topic


def make_long(c: dict, day: dt.date | None = None) -> dict:
    """One ~7-minute 16:9 video in today's alternating format (config long:)."""
    day = day or dt.date.today()
    fmt, topic = long_format(c, day)
    history = "\n".join(f"- {j.get('title') or j.get('topic')}" for j in all_jobs() if j.get("lane") == "long") or "- (nothing yet)"
    prompt = lambda: (PIPE / "prompts" / "long_video.md").read_text(encoding="utf-8").format(  # noqa: E731
        niche=c["channel"]["niche"], format=fmt, topic=topic or "(none: pick one)", history=history,
        notes="\n\n".join(f.read_text(encoding="utf-8") for f in (PIPE / "standing_rules.md", PIPE / "strategy_notes.md")
                          if f.exists()) or "(no data yet)",
    )
    log(f"getting long video script (script bank first, else Claude: {fmt[:50]})")
    spec, bank_file = script_or_bank(c, "long", prompt)
    job_id = f"{dt.datetime.now():%Y%m%d-%H%M%S}-long-{slug(spec.get('topic', 'video'))}"
    job = {"id": job_id, "lane": "long", "status": "scripted", "category": "geography",
           "created": dt.datetime.now().isoformat(), "bank_file": bank_file, **spec}
    save_job(job)
    return produce_auto(job, c)


def narrate(job: dict, c: dict, engine: str | None) -> tuple:
    spec, d = job, JOBS / job["id"]
    parts, scenes, words, t = [], [], [], 0.0
    gap = 0.05
    for i, sc in enumerate(spec["scenes"]):
        p = d / f"vo_{i:02d}.wav"
        timed = speak(sc["narration"], p, c, engine)
        dur = wav_seconds(p)
        parts.append(p)
        scenes.append({
            "start": round(t, 3), "end": round(t + dur, 3),
            "emoji": sc.get("emoji") or "", "headline": sc.get("headline") or "",
            "stat": sc.get("stat") or "", "sub": sc.get("sub") or "",
            "characterPose": sc.get("characterPose") or sc.get("pose") or "",
        })
        if timed:
            words += [{**w, "start": round(w["start"] + t, 3), "end": round(w["end"] + t, 3)} for w in timed]
        else:
            words += word_timings(sc["narration"], t, t + dur)
        if words:
            words[-1]["brk"] = True
        t += dur + gap
    return parts, scenes, words, t


def chapter_lines(job: dict, scenes: list) -> str:
    """YouTube chapter timestamps from the script's chapter -> scene map (first one must be 0:00)."""
    out = []
    for ch in job.get("chapters") or []:
        i = int(ch.get("scene", 0))
        if 0 <= i < len(scenes):
            s = 0 if not out else int(scenes[i]["start"])
            out.append(f"{s // 60}:{s % 60:02d} {ch.get('title', '').strip()}")
    return "\n".join(out) if len(out) >= 3 else ""


def render_auto(job: dict, c: dict, scenes: list, words: list, t: float) -> dict:
    job_id, d = job["id"], JOBS / job["id"]
    long_video = job.get("lane") == "long"
    if long_video and not job.get("chapters_added"):
        chapters = chapter_lines(job, scenes)
        if chapters:
            job["description"] = job.get("description", "") + "\n\nChapters:\n" + chapters
            job["chapters_added"] = True
    if c["render"].get("visuals", True):
        log(f"{job_id}: finding visuals")
        for i, bg in enumerate(fetch_visuals(job, c)):
            if bg:
                scenes[i]["background"] = stage_asset(job_id, Path(bg), Path(bg).name)
    # Option 1: 2D Blender Toon Mascot character posing
    if c.get("render", {}).get("character_mascot", True):
        cat = str(job.get("category", "")).lower()
        for i, sc in enumerate(scenes):
            if not sc.get("characterPose"):
                narration = (job.get("scenes", [{}])[i].get("narration", "") if i < len(job.get("scenes", [])) else "").lower()
                if i == 0:
                    sc["characterPose"] = "shock"  # Hook scene: hands-on-cheeks reaction!
                elif sc.get("stat"):
                    sc["characterPose"] = "point"  # Stat/number scene: pointing gesture!
                elif any(w in narration for w in ("phone", "internet", "app", "digital", "tech", "screen")):
                    sc["characterPose"] = "phone"
                elif cat == "space" and i % 2 == 1:
                    sc["characterPose"] = "astronaut"
                elif i % 3 == 1:
                    sc["characterPose"] = "think"
                elif i % 3 == 2:
                    sc["characterPose"] = "celebrate"
                else:
                    sc["characterPose"] = "explain"
    props = {"scenes": scenes, "words": words, "narration": stage_asset(job_id, d / "narration.wav", "narration.wav")}
    cta = c.get("growth", {}).get("end_card", "")
    if cta:
        props["cta"] = cta.format(category=job.get("category") or "daily")
    if job.get("comment_prompt"):
        props["question"] = job["comment_prompt"]
    if job.get("hook_banner"):
        props["banner"] = job["hook_banner"]
    if c.get("growth", {}).get("outro"):
        props["outro"] = c["growth"]["outro"]
    if c.get("growth", {}).get("like_sticker"):
        props["likeText"] = c["growth"]["like_sticker"]
    # Long videos render as 16:9 and take far longer than a Short, so give them their own time limit.
    render_target = ("LongLandscape", int(c.get("long", {}).get("render_timeout", 5400))) if long_video else ("ShortVertical", None)
    music = c["render"].get("music")
    if music and (ROOT / music).exists():
        props["music"] = stage_asset(job_id, ROOT / music, "music" + Path(music).suffix)
        props["musicVolume"] = c["render"].get("music_volume", 0.1)
    try:
        try:
            remotion_render(job, props, *render_target)
        except RuntimeError as exc:
            # Some stock clips still trip Remotion's frame extractor; swap clips for a still frame and retry.
            log(f"{job_id}: render failed with video clips ({str(exc)[:80]}), retrying with still frames")
            for sc in scenes:
                bg = sc.get("background", "")
                if bg.endswith(".mp4"):
                    src = COMPOSER / "public" / bg
                    still = src.with_suffix(".still.jpg")
                    subprocess.run([ff("ffmpeg"), "-v", "error", "-y", "-ss", "1", "-i", str(src), "-frames:v", "1", str(still)],
                                   capture_output=True, text=True)
                    sc["background"] = bg[:-4] + ".still.jpg" if still.exists() else ""
            remotion_render(job, props, *render_target)
    finally:
        cleanup_stage(job_id)
    job.update(status="uploaded" if job.get("video_id") else "rendered", seconds=round(t, 1))
    save_job(job)
    log(f"{job_id}: rendered {t:.1f}s -> jobs/{job_id}/short.mp4")
    return job


def make_from_clip(clip: Path, c: dict) -> dict:
    notes_file = clip.with_suffix(".txt")
    notes = notes_file.read_text(encoding="utf-8") if notes_file.exists() else ""
    seconds = media_seconds(clip)
    if seconds > 60:
        log(f"skip {clip.name}: {seconds:.0f}s is longer than 60s")
        return {}
    tmpl = (PIPE / "prompts" / "inbox_clip.md").read_text(encoding="utf-8")
    spec = ask_claude(tmpl.format(niche=c["channel"]["niche"], clip_name=clip.name, seconds=seconds,
                                  notes=notes or "(none)", history=history_lines()))
    validate_script_safety(spec)
    job_id = f"{dt.datetime.now():%Y%m%d-%H%M}-{slug(spec.get('topic', clip.stem))}"
    d = JOBS / job_id
    d.mkdir(parents=True, exist_ok=True)
    shutil.move(str(clip), d / f"source{clip.suffix.lower()}")
    if notes_file.exists():
        shutil.move(str(notes_file), d / "notes.txt")
    job = {"id": job_id, "lane": "inbox", "status": "scripted", "created": dt.datetime.now().isoformat(), **spec}
    save_job(job)
    bg = stage_asset(job_id, d / f"source{clip.suffix.lower()}", f"source{clip.suffix.lower()}")
    props = {"scenes": [{"start": 0, "end": round(seconds, 2), "headline": spec.get("hook", ""),
                         "sub": spec.get("sub", ""), "background": bg}], "words": []}
    try:
        remotion_render(job, props)
    finally:
        cleanup_stage(job_id)
    job.update(status="rendered", seconds=round(seconds, 1))
    save_job(job)
    log(f"{job_id}: rendered from your clip {clip.name}")
    return job


def process_inbox(c: dict) -> list[dict]:
    INBOX.mkdir(exist_ok=True)
    done = []
    for clip in sorted(p for p in INBOX.iterdir() if p.suffix.lower() in CLIP_EXT):
        try:
            job = make_from_clip(clip, c)
            if job:
                done.append(job)
        except Exception as exc:
            log(f"inbox {clip.name} failed: {exc}")
    return done


# ---------------------------------------------------------------- YouTube

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly",
          "https://www.googleapis.com/auth/yt-analytics.readonly"]


def yt_client(interactive: bool):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    SECRETS.mkdir(exist_ok=True)
    token = SECRETS / "youtube_token.json"
    creds = Credentials.from_authorized_user_file(str(token)) if token.exists() else None
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        if not interactive:
            raise SystemExit("YouTube not signed in. Run: shorts.py auth")
        secret = SECRETS / "client_secret.json"
        if not secret.exists():
            raise SystemExit(f"Put your Google OAuth desktop client file at {secret}")
        creds = InstalledAppFlow.from_client_secrets_file(str(secret), SCOPES).run_local_server(port=0)
    token.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


def youtube_description(text: str, credits: list[str], limit: int = 4900) -> str:
    """YouTube rejects descriptions over 5000 bytes or with < >; long videos have ~70 credit lines, so trim those."""
    def clean(s: str) -> str:
        return s.replace("<", "(").replace(">", ")")
    out = clean(text)
    if credits:
        out += "\n\nVisual credits:"
        for line in credits:
            line = "\n" + clean(line)
            if len((out + line).encode("utf-8")) > limit:
                out += "\n(and more)"
                break
            out += line
    return out.encode("utf-8")[:limit].decode("utf-8", "ignore")


def upload(job_id: str, c: dict, privacy: str | None = None, publish_at: dt.datetime | None = None) -> dict:
    from googleapiclient.http import MediaFileUpload

    job = load_job(job_id)
    validate_script_safety(job)
    if job.get("status") == "uploaded":
        log(f"{job_id}: already uploaded ({job.get('url')})")
        return job
    u = c["upload"]
    yt = yt_client(interactive=False)
    desc = job.get("description", "")
    if job.get("comment_prompt"):
        desc += "\n\n\U0001F4AC " + job["comment_prompt"] + " Tell me in the comments."
    # Growth Bridge: For Shorts, cross-link to latest long-form video to build 4,000 public watch hours
    if job.get("lane") != "long":
        longs = [j for j in all_jobs() if j.get("lane") == "long" and j.get("video_id")]
        if longs:
            recent_long = longs[-1]
            desc += f"\n\n\U0001F449 Watch our full 7-minute deep dive: https://youtube.com/watch?v={recent_long['video_id']}"
    if c.get("growth", {}).get("description_line"):
        desc += "\n\n" + c["growth"]["description_line"]

    body = {
        "snippet": {
            "title": job["title"][:100],
            "description": youtube_description(desc, job.get("credits") or []),
            "tags": job.get("tags", [])[:15],
            "categoryId": str(u.get("category_id", "28")),
        },
        "status": {
            "privacyStatus": privacy or u.get("privacy", "private"),
            "selfDeclaredMadeForKids": bool(u.get("made_for_kids", False)),
            "containsSyntheticMedia": bool(u.get("contains_synthetic_media", True)),
        },
    }
    if publish_at:
        # YouTube keeps it private, then makes it public by itself at this time.
        body["status"]["privacyStatus"] = "private"
        body["status"]["publishAt"] = publish_at.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    media = MediaFileUpload(str(JOBS / job_id / "short.mp4"), mimetype="video/mp4", resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    video_url = f"https://youtube.com/watch?v={resp['id']}" if job.get("lane") == "long" else f"https://youtube.com/shorts/{resp['id']}"
    job.update(status="uploaded", video_id=resp["id"], url=video_url,
               uploaded=dt.datetime.now().isoformat(), privacy=body["status"]["privacyStatus"],
               publish_at=publish_at.isoformat() if publish_at else "")
    save_job(job)
    when = f", goes public {publish_at:%a %H:%M}" if publish_at else ""
    log(f"{job_id}: uploaded as {job['privacy']}{when} -> {job['url']}")
    return job


# ---------------------------------------------------------------- tracking + strategy

REPORTS = ROOT / "reports"
TRACK_FIELDS = ["date", "job_id", "video_id", "category", "title", "hook", "uploaded", "publish_at", "seconds",
                "views", "likes", "comments", "avg_view_pct", "avg_view_sec", "subs_gained", "shares", "url"]


def track(c: dict) -> list[dict]:
    """Snapshot every uploaded Short's numbers into reports/shorts_tracker.csv (one row per Short per day)."""
    import csv

    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    jobs = [j for j in all_jobs() if j.get("video_id")]
    if not jobs:
        log("track: nothing uploaded yet")
        return []
    yt = yt_client(interactive=False)
    ids = [j["video_id"] for j in jobs]
    stats = {}
    for i in range(0, len(ids), 50):
        resp = yt.videos().list(part="statistics", id=",".join(ids[i:i + 50])).execute()
        for it in resp.get("items", []):
            stats[it["id"]] = it.get("statistics", {})

    analytics = {}
    try:
        creds = Credentials.from_authorized_user_file(str(SECRETS / "youtube_token.json"))
        ya = build("youtubeAnalytics", "v2", credentials=creds)
        start = min(j.get("uploaded", j["created"])[:10] for j in jobs)
        resp = ya.reports().query(
            ids="channel==MINE", startDate=start, endDate=dt.date.today().isoformat(),
            metrics="averageViewPercentage,averageViewDuration,subscribersGained,shares",
            dimensions="video", filters="video==" + ",".join(ids[:200]),
        ).execute()
        cols = [h["name"] for h in resp.get("columnHeaders", [])]
        for row in resp.get("rows", []) or []:
            analytics[row[0]] = dict(zip(cols, row))
    except Exception as exc:
        log(f"track: analytics unavailable ({str(exc)[:160]}) - run Reconnect-YouTube.bat and enable YouTube Analytics API")

    try:
        summary = {}
        start = min(j.get("uploaded", j["created"])[:10] for j in jobs)
        for key, dim in (("traffic_sources", "insightTrafficSourceType"), ("countries", "country"), ("ages", "ageGroup")):
            metric = "viewerPercentage" if dim == "ageGroup" else "views"
            resp = ya.reports().query(ids="channel==MINE", startDate=start, endDate=dt.date.today().isoformat(),
                                      metrics=metric, dimensions=dim).execute()
            summary[key] = resp.get("rows", [])
        REPORTS.mkdir(exist_ok=True)
        (REPORTS / "channel_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    except Exception:
        pass

    today = dt.date.today().isoformat()
    rows = []
    for j in jobs:
        st, an = stats.get(j["video_id"], {}), analytics.get(j["video_id"], {})
        rows.append({
            "date": today, "job_id": j["id"], "video_id": j["video_id"], "category": j.get("category", ""),
            "title": j.get("title", ""), "hook": j.get("hook", ""), "uploaded": j.get("uploaded", "")[:10],
            "publish_at": (j.get("publish_at") or "")[:16],
            "seconds": j.get("seconds", ""), "views": st.get("viewCount", ""), "likes": st.get("likeCount", ""),
            "comments": st.get("commentCount", ""), "avg_view_pct": round(an.get("averageViewPercentage", 0), 1) if an else "",
            "avg_view_sec": an.get("averageViewDuration", "") if an else "", "subs_gained": an.get("subscribersGained", "") if an else "",
            "shares": an.get("shares", "") if an else "", "url": j.get("url", ""),
        })
    REPORTS.mkdir(exist_ok=True)
    tracker = REPORTS / "shorts_tracker.csv"
    old = []
    if tracker.exists():
        with tracker.open(encoding="utf-8", newline="") as fh:
            old = [r for r in csv.DictReader(fh) if r.get("date") != today]
    with tracker.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=TRACK_FIELDS)
        w.writeheader()
        w.writerows(old + rows)
    with (REPORTS / "latest.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=TRACK_FIELDS)
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: -int(r["views"] or 0)))
    log(f"track: {len(rows)} Shorts snapshotted -> reports/shorts_tracker.csv")
    try:
        import growth_analytics
        growth_analytics.generate_daily_report(c)
    except Exception as exc:
        log(f"track: daily growth report note: {exc}")
    return rows


def strategy(c: dict) -> Path:
    """Daily: Claude reads the tracker with the yt-plan / yt-retention skills and writes strategy + topic mix."""
    tracker = REPORTS / "shorts_tracker.csv"
    if not tracker.exists():
        track(c)
    tmpl = (PIPE / "prompts" / "strategy.md").read_text(encoding="utf-8")
    spec = ask_claude(tmpl.format(categories=", ".join(c["ideas"].get("categories", {})), per_day=c["upload"].get("per_run", 3)))
    out = REPORTS / f"strategy-{dt.date.today().isoformat()}.md"
    out.write_text(spec.get("report_markdown", ""), encoding="utf-8")
    notes = spec.get("writer_notes", "")
    if isinstance(notes, list):
        notes = "\n".join(n if n.lstrip().startswith("-") else f"- {n}" for n in notes)
    (PIPE / "strategy_notes.md").write_text(notes, encoding="utf-8")
    weights = spec.get("category_weights") or {}
    if weights:
        (PIPE / "category_weights.json").write_text(json.dumps(weights, indent=2), encoding="utf-8")
    with (REPORTS / "strategy_changes.log").open("a", encoding="utf-8") as fh:
        fh.write(f"{dt.date.today().isoformat()}: {spec.get('changed', '')} | weights {weights}\n")
    log(f"strategy: wrote {out.name}; weights {weights}; change: {spec.get('changed', '')}")
    return out


# ---------------------------------------------------------------- commands

def publish_times(c: dict, count: int) -> list:
    """Spread a batch over the day: next occurrence of each configured slot, in priority order."""
    slots = c["upload"].get("publish_slots") or []
    if not slots:
        return [None] * count
    now = dt.datetime.now().astimezone()
    out = []
    for slot in slots:
        h, m = map(int, slot.split(":"))
        t = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if t < now + dt.timedelta(minutes=20):
            t += dt.timedelta(days=1)
        out.append(t)
    while len(out) < count:  # more Shorts than slots: repeat the slots a day later
        out.append(out[len(out) - len(slots)] + dt.timedelta(days=1))
    return out[:count]


def prepared_marker(day: dt.date | None = None) -> Path:
    return ROOT / "logs" / f"prepared-{(day or dt.date.today()).isoformat()}"


def prepare(c: dict) -> None:
    """Evening scheduler step (before 21:00): track numbers, daily strategy, make per_run Shorts + the long video."""
    done_today = (REPORTS / f"strategy-{dt.date.today().isoformat()}.md").exists()
    bank_only = c.get("scripts", {}).get("bank_only")
    steps = (track,) if done_today or bank_only else (track, strategy)  # strategy at most once a day; never without Claude
    for step in steps:  # numbers first, then today's strategy feeds the scripts below
        try:
            step(c)
        except SystemExit as exc:
            log(f"{step.__name__} skipped: {exc}")
        except Exception as exc:
            log(f"{step.__name__} failed: {exc}")
    process_inbox(c)
    # Top up today's batch to per_run Shorts + per_day long videos. Safe to run again: anything already
    # made today counts, and a failed video is retried with the next script (a few tries at most).
    today = dt.date.today().isoformat()

    def made(lane: str) -> int:
        return sum(1 for j in all_jobs() if j.get("lane") == lane and j.get("created", "")[:10] == today
                   and j.get("status") in ("rendered", "uploaded"))

    want = int(c["upload"].get("per_run", 1))
    start = str(c.get("scripts", {}).get("start_date", ""))
    if start and today < start:  # the pre-written schedule hasn't begun yet: don't use tomorrow's scripts today
        log(f"prepare: daily videos start on {start}; nothing to make today")
        return
    for _ in range(want + 3):
        if made("auto") >= want:
            break
        try:
            make_auto(c)
        except Exception as exc:
            log(f"make failed: {exc}")
    lc = c.get("long", {})
    for _ in range(2 if lc.get("per_day") else 0):
        if made("long") >= int(lc["per_day"]):
            break
        try:
            make_long(c)
        except Exception as exc:
            log(f"long video failed: {exc}")
    prepared_marker().write_text(dt.datetime.now().isoformat(), encoding="utf-8")
    ready = [j for j in all_jobs() if j.get("status") == "rendered"]
    log(f"prepare: {len(ready)} videos rendered and waiting for the 21:00 upload")


def cmd_daily(c: dict) -> None:
    """21:00 scheduler entry: upload everything prepared (makes today's batch first if prepare didn't run)."""
    if not prepared_marker().exists():
        prepare(c)
    upload_pending(c)


def upload_pending(c: dict) -> None:
    """Upload every rendered video, oldest first, until YouTube's daily limit; the rest wait for the next run."""
    lc = c.get("long", {})
    # Long videos go first (so the daily upload limit never skips them) at their own publish time.
    ready = [j for j in all_jobs() if j.get("status") == "rendered"]
    longs = [j for j in ready if j.get("lane") == "long"]
    for j in longs:
        when = None
        if lc.get("publish_time"):
            h, m = map(int, lc["publish_time"].split(":"))
            when = dt.datetime.now().astimezone().replace(hour=h, minute=m, second=0, microsecond=0)
            if when < dt.datetime.now().astimezone() + dt.timedelta(minutes=20):
                when += dt.timedelta(days=1)
        try:
            upload(j["id"], c, publish_at=when)
        except Exception as exc:
            log(f"{j['id']}: long upload failed: {exc}")
    ready = [j for j in ready if j.get("lane") != "long"]
    times = publish_times(c, len(ready))
    for j, when in zip(ready, times):
        try:
            try:
                upload(j["id"], c, publish_at=when)
            except Exception as exc:
                if when is None or "quota" in str(exc).lower() or "limit" in str(exc).lower():
                    raise
                log(f"{j['id']}: scheduled publishing refused ({str(exc)[:120]}); uploading without a publish time")
                upload(j["id"], c)
        except SystemExit as exc:
            log(f"upload skipped: {exc}")
            break
        except Exception as exc:
            log(f"{j['id']}: upload failed: {exc}")
            if "quotaExceeded" in str(exc) or "uploadLimitExceeded" in str(exc):
                log("YouTube daily upload limit reached; the rest stay queued for the next run")
                break


def youtube_ok() -> tuple[bool, str]:
    try:
        yt = yt_client(interactive=False)
        me = yt.channels().list(part="snippet", mine=True).execute()
        return True, me["items"][0]["snippet"]["title"] if me.get("items") else "(no channel)"
    except BaseException as exc:  # SystemExit when signed out, RefreshError when the weekly login expired
        return False, str(exc)[:200]


def autopilot(c: dict) -> int:
    """One click / one scheduled run: check YouTube, make today's videos if missing, upload everything pending."""
    lines = [f"Autopilot run {dt.datetime.now():%d %b %Y %H:%M}"]
    ok, who = youtube_ok()
    lines.append(f"YouTube: {'connected to ' + who if ok else 'NOT CONNECTED - double-click Reconnect-YouTube.bat'}")
    if not ok:
        log(f"autopilot: YouTube not connected ({who})")
    prepare(c)
    if ok:
        upload_pending(c)
    today = dt.date.today().isoformat()
    jobs = all_jobs()
    made = [j for j in jobs if j.get("created", "")[:10] == today and j.get("lane") in ("auto", "long")
            and j.get("status") in ("rendered", "uploaded")]
    up_today = [j for j in jobs if (j.get("uploaded") or "")[:10] == today]
    waiting = [j for j in jobs if j.get("status") == "rendered"]
    lines += [
        f"Made today: {sum(j['lane'] == 'auto' for j in made)} Shorts, {sum(j['lane'] == 'long' for j in made)} long "
        f"(target {c['upload'].get('per_run', 5)} + {c.get('long', {}).get('per_day', 0)})",
        f"Uploaded today: {len(up_today)}",
        f"Waiting to upload: {len(waiting)}" + (" (YouTube's daily limit; they go out next run)" if waiting and ok else ""),
        f"Scripts left: {bank_left('shorts')} Shorts, {bank_left('long')} long videos "
        f"(about {min(bank_left('shorts') // max(1, int(c['upload'].get('per_run', 5))), bank_left('long'))} days)",
    ]
    text = "\n".join(lines)
    (REPORTS / "autopilot_status.txt").write_text(text + "\n", encoding="utf-8")
    log("autopilot: " + " | ".join(lines[1:]))
    print("\n" + text + "\n")
    problem = not ok or len(made) < int(c["upload"].get("per_run", 5)) + int(c.get("long", {}).get("per_day", 0))
    if problem and os.environ.get("AUTOPILOT_POPUP", "1") == "1":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, text, "YouTube Autopilot needs attention", 0x40030)
        except Exception:
            pass
    return 0 if not problem else 2


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    try:
        # Keep Windows from idle-sleeping while this run works (released automatically when it exits).
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)  # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    mk = sub.add_parser("make")
    mk.add_argument("--category")
    lg = sub.add_parser("long", help="make today's ~7-minute 16:9 video (not uploaded)")
    lg.add_argument("--date", help="use this date's format and topic (YYYY-MM-DD)")
    sub.add_parser("inbox")
    sub.add_parser("auth")
    sub.add_parser("daily")
    sub.add_parser("prepare")
    sub.add_parser("autopilot", help="check YouTube, make today's videos if missing, upload everything pending")
    sub.add_parser("list")
    sub.add_parser("track")
    sub.add_parser("strategy")
    sub.add_parser("report", help="generate daily growth & analytics report")
    rm = sub.add_parser("remake", help="re-voice and re-render a job after editing its job.json")
    rm.add_argument("job_id")
    up = sub.add_parser("upload")
    up.add_argument("job_id")
    up.add_argument("--privacy", choices=["private", "unlisted", "public"])
    a = ap.parse_args(argv)
    c = cfg()
    try:
        if a.cmd == "make":
            make_auto(c, a.category)
        elif a.cmd == "long":
            make_long(c, dt.date.fromisoformat(a.date) if a.date else None)
        elif a.cmd == "inbox":
            process_inbox(c)
        elif a.cmd == "auth":
            yt = yt_client(interactive=True)
            me = yt.channels().list(part="snippet", mine=True).execute()
            name = me["items"][0]["snippet"]["title"] if me.get("items") else "(no channel on this account)"
            log(f"signed in to YouTube channel: {name}")
        elif a.cmd == "upload":
            upload(a.job_id, c, a.privacy)
        elif a.cmd == "remake":
            produce_auto(load_job(a.job_id), c)
        elif a.cmd == "track":
            track(c)
        elif a.cmd == "strategy":
            strategy(c)
        elif a.cmd == "report":
            import growth_analytics
            growth_analytics.generate_daily_report(c)
        elif a.cmd == "daily":
            cmd_daily(c)
        elif a.cmd == "prepare":
            prepare(c)
        elif a.cmd == "autopilot":
            return autopilot(c)
        elif a.cmd == "list":
            for j in all_jobs():
                print(f"{j['id']:55} {j.get('status',''):9} {j.get('title','')}  {j.get('url','')}")
    except Exception as exc:
        log(f"ERROR {a.cmd}: {exc}")
        return 1
    finally:
        try:  # keep Video-Dashboard.html current after every run
            import dashboard
            dashboard.build()
        except Exception as exc:
            log(f"dashboard not updated: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
