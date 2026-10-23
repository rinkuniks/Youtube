"""Pre-write scripts for many days ahead so the daily run never needs Claude.

    python pipeline/bank.py --days 60 --start 2026-10-18

Writes script_bank/plan.json (topics by date), script_bank/shorts/<date>-<n>.json and
script_bank/long/<date>.json. Safe to re-run: anything already written is kept.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import shorts  # noqa: E402

BANK = shorts.ROOT / "script_bank"
DAY_MIX = (["geography", "geography", "geography", "space", "technology"],
           ["geography", "geography", "geography", "technology", "space"])


def notes() -> str:
    return "\n\n".join(f.read_text(encoding="utf-8") for f in (shorts.PIPE / "standing_rules.md", shorts.PIPE / "strategy_notes.md")
                       if f.exists())


def used_titles() -> list[str]:
    return [j.get("title") or j.get("topic") for j in shorts.all_jobs() if j.get("title") or j.get("topic")]


def ask_topics(c: dict, kind: str, what: str, count: int, history: list[str]) -> list[str]:
    tmpl = (shorts.PIPE / "prompts" / "bank_topics.md").read_text(encoding="utf-8")
    cache = BANK / f"topics-{shorts.slug(kind)}.json"  # keeps finished batches if a later step fails
    out: list[str] = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else []
    while len(out) < count:
        n = min(50, count - len(out))
        spec = shorts.ask_claude(tmpl.format(niche=c["channel"]["niche"], kind=kind, what=what, count=n, notes=notes(),
                                             history="\n".join(f"- {h}" for h in history + out) or "- (none)"))
        got = [t.strip() for t in spec.get("topics", []) if isinstance(t, str) and t.strip()]
        if not got:
            raise RuntimeError(f"no topics returned for {kind}")
        out += got[:n]
        BANK.mkdir(exist_ok=True)
        cache.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
        shorts.log(f"bank: planned {len(out)}/{count} topics for {kind}")
    return out[:count]


def make_plan(c: dict, start: dt.date, days: int) -> dict:
    path = BANK / "plan.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    dates = [start + dt.timedelta(days=i) for i in range(days)]
    need = {"geography": 0, "space": 0, "technology": 0}
    for i in range(days):
        for cat in DAY_MIX[i % 2]:
            need[cat] += 1
    history = used_titles()
    cats = c["ideas"]["categories"]
    pools = {}
    for cat, n in need.items():
        pools[cat] = ask_topics(c, f"{cat} Shorts", f"{cat}: " + "; ".join(cats.get(cat, [])), n, history)
        history += pools[cat]
    formats = c["long"]["formats"]
    fixed = c["long"].get("topics") or {}
    long_need = [0] * len(formats)
    for d in dates:
        fmt, topic = shorts.long_format(c, d)
        if not topic:
            long_need[formats.index(fmt)] += 1
    long_pools = []
    for fi, fmt in enumerate(formats):
        pool = ask_topics(c, "~7-minute long videos", fmt, long_need[fi], history + list(fixed.values())) if long_need[fi] else []
        history += pool
        long_pools.append(pool)
    plan = {"start": start.isoformat(), "days": []}
    for i, d in enumerate(dates):
        fmt, topic = shorts.long_format(c, d)
        if not topic:
            topic = long_pools[formats.index(fmt)].pop(0)
        plan["days"].append({
            "date": d.isoformat(),
            "shorts": [{"category": cat, "topic": pools[cat].pop(0)} for cat in DAY_MIX[i % 2]],
            "long": {"format": fmt, "topic": topic},
        })
    BANK.mkdir(exist_ok=True)
    path.write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")
    return plan


def valid(spec: dict) -> bool:
    return bool(spec.get("title") and spec.get("scenes") and all(s.get("narration") for s in spec["scenes"]))


def write_short_batch(c: dict, slots: list[tuple[str, int, dict]]) -> int:
    tmpl = (shorts.PIPE / "prompts" / "bank_shorts.md").read_text(encoding="utf-8")
    topics = "\n".join(f"{k + 1}. [{s['category']}] {s['topic']}" for k, (_, _, s) in enumerate(slots))
    spec = shorts.ask_claude(tmpl.format(niche=c["channel"]["niche"], audience=c["channel"]["audience"], count=len(slots),
                                         topics=topics, notes=notes(), max_seconds=c["ideas"].get("max_seconds", 30)))
    done = 0
    for (date, n, slot), short in zip(slots, spec.get("shorts", [])):
        if valid(short):
            short.setdefault("category", slot["category"])
            try:
                shorts.validate_script_safety(short)
            except Exception as e:
                shorts.log(f"bank: rejected unsafe script {date}-{n}: {e}")
                continue
            (BANK / "shorts" / f"{date}-{n}.json").write_text(json.dumps(short, indent=1, ensure_ascii=False), encoding="utf-8")
            done += 1
    return done


def write_long(c: dict, date: str, item: dict, history: str) -> int:
    prompt = (shorts.PIPE / "prompts" / "long_video.md").read_text(encoding="utf-8").format(
        niche=c["channel"]["niche"], format=item["format"], topic=item["topic"], history=history, notes=notes())
    spec = shorts.ask_claude(prompt)
    if not valid(spec):
        return 0
    try:
        shorts.validate_script_safety(spec)
    except Exception as e:
        shorts.log(f"bank: rejected unsafe long video {date}: {e}")
        return 0
    (BANK / "long" / f"{date}.json").write_text(json.dumps(spec, indent=1, ensure_ascii=False), encoding="utf-8")
    return 1



def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--start", default=(dt.date.today() + dt.timedelta(days=1)).isoformat())
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--batch", type=int, default=6)
    a = ap.parse_args()
    c = shorts.cfg()
    (BANK / "shorts").mkdir(parents=True, exist_ok=True)
    (BANK / "long").mkdir(parents=True, exist_ok=True)
    plan = make_plan(c, dt.date.fromisoformat(a.start), a.days)
    shorts.log(f"bank: plan ready for {len(plan['days'])} days")

    slots = [(d["date"], n, s) for d in plan["days"] for n, s in enumerate(d["shorts"], 1)
             if not (BANK / "shorts" / f"{d['date']}-{n}.json").exists()]
    batches = [slots[i:i + a.batch] for i in range(0, len(slots), a.batch)]
    long_history = "\n".join(f"- {d['long']['topic']}" for d in plan["days"])
    longs = [(d["date"], d["long"]) for d in plan["days"] if not (BANK / "long" / f"{d['date']}.json").exists()]
    with ThreadPoolExecutor(a.workers) as pool:
        futs = {pool.submit(write_long, c, date, item, long_history): f"long {date}" for date, item in longs[:2]}
        futs.update({pool.submit(write_short_batch, c, b): f"shorts {b[0][0]}" for b in batches})
        futs.update({pool.submit(write_long, c, date, item, long_history): f"long {date}" for date, item in longs[2:]})
        for f in as_completed(futs):
            try:
                shorts.log(f"bank: {futs[f]} -> {f.result()} written")
            except Exception as exc:
                shorts.log(f"bank: {futs[f]} failed: {str(exc)[:200]}")
    have_s = len(list((BANK / "shorts").glob("*.json")))
    have_l = len(list((BANK / "long").glob("*.json")))
    shorts.log(f"bank: {have_s} Shorts and {have_l} long scripts saved (re-run to fill any gaps)")


if __name__ == "__main__":
    main()
