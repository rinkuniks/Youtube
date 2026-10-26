"""Builds Video-Dashboard.html: every video from script to publishing, with the script text.

Runs after every shorts.py command (and by hand: python pipeline/dashboard.py). Local files only,
no Claude and no internet needed.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import shorts  # noqa: E402

OUT = shorts.ROOT / "Video-Dashboard.html"


def _status(job: dict | None, has_script: bool, now: dt.datetime) -> str:
    if job is None:
        return "Script ready" if has_script else "Script pending"
    st = job.get("status", "")
    if st == "uploaded":
        pa = job.get("publish_at") or ""
        try:
            when = dt.datetime.fromisoformat(pa) if pa else None
        except ValueError:
            when = None
        if when and when.astimezone() > now:
            return "Uploaded, scheduled"
        return "Published"
    if st == "rendered":
        return "Created, waiting upload"
    if st == "scripted":
        try:
            created = dt.datetime.fromisoformat(job.get("created", "")).astimezone()
        except ValueError:
            created = now
        return "Making" if (now - created).total_seconds() < 3 * 3600 else "Failed"
    return {"rejected": "Rejected", "preview": "Preview (not for upload)", "test": "Test"}.get(st, st or "Unknown")


def _row(date: str, kind: str, spec: dict, job: dict | None, has_script: bool, now: dt.datetime) -> dict:
    src = job or spec
    scenes = src.get("scenes") or []
    return {
        "date": date,
        "kind": kind,
        "category": (job or {}).get("category") or spec.get("category", ""),
        "title": src.get("title") or spec.get("topic") or "",
        "hook": src.get("hook", ""),
        "status": _status(job, has_script, now),
        "seconds": (job or {}).get("seconds"),
        "publish_at": ((job or {}).get("publish_at") or "")[:16].replace("T", " "),
        "uploaded": ((job or {}).get("uploaded") or "")[:16].replace("T", " "),
        "url": (job or {}).get("url", ""),
        "description": src.get("description", ""),
        "script": [s.get("narration", "") for s in scenes],
        "job": (job or {}).get("id", ""),
    }


def build() -> Path:
    now = dt.datetime.now().astimezone()
    jobs = shorts.all_jobs()
    by_bank = {j["bank_file"]: j for j in jobs if j.get("bank_file")}
    rows, seen = [], set()
    plan_path = shorts.BANK / "plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8")) if plan_path.exists() else {"days": []}
    for day in plan["days"]:
        d = day["date"]
        slots = [("Short", f"shorts/{d}-{n}.json", s) for n, s in enumerate(day["shorts"], 1)]
        slots.append(("Long video", f"long/{d}.json", day["long"]))
        for kind, rel, planned in slots:
            f = shorts.BANK / rel
            spec = json.loads(f.read_text(encoding="utf-8")) if f.exists() else dict(planned)
            spec.setdefault("category", planned.get("category", "geography"))
            job = by_bank.get(f.name)
            if job:
                seen.add(job["id"])
            rows.append(_row(d, kind, spec, job, f.exists(), now))
    for j in jobs:  # everything made before the script bank, or by hand
        if j["id"] not in seen and j.get("status") != "test":
            rows.append(_row(j.get("created", "")[:10], "Long video" if j.get("lane") == "long" else "Short", {}, j, True, now))
    # Today first, then upcoming days (soonest first), then past days (newest first).
    today = now.date().isoformat()
    upcoming = sorted((r for r in rows if r["date"] > today), key=lambda r: (r["date"], r["kind"] != "Long video"))
    past = sorted((r for r in rows if r["date"] < today), key=lambda r: (r["date"], r["kind"] == "Long video"), reverse=True)
    rows = [r for r in rows if r["date"] == today] + upcoming + past

    status_file = shorts.REPORTS / "autopilot_status.txt"
    last_run = status_file.read_text(encoding="utf-8") if status_file.exists() else "Autopilot has not run yet."
    data = json.dumps({"rows": rows, "built": now.strftime("%d %b %Y %H:%M"), "lastRun": last_run}, ensure_ascii=False)
    OUT.write_text(TEMPLATE.replace("__DATA__", data.replace("</", "<\\/")), encoding="utf-8")
    return OUT


TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Video Dashboard</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--text:#16181d;--muted:#5f6672;--line:#e3e6ea;--accent:#2563eb;
--ok:#15803d;--okbg:#dcfce7;--warn:#a16207;--warnbg:#fef3c7;--bad:#b91c1c;--badbg:#fee2e2;--info:#1d4ed8;--infobg:#dbeafe;--grey:#4b5563;--greybg:#eceff3}
@media (prefers-color-scheme:dark){:root{--bg:#0f1115;--card:#181b21;--text:#e8eaee;--muted:#9aa2ae;--line:#2a2f37;--accent:#60a5fa;
--ok:#4ade80;--okbg:#12301f;--warn:#fbbf24;--warnbg:#3a2c0b;--bad:#f87171;--badbg:#3b1414;--info:#93c5fd;--infobg:#132544;--grey:#c0c6cf;--greybg:#252a32}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:1180px;margin:0 auto;padding:20px 16px 48px}h1{font-size:22px;margin:0 0 4px}.sub{color:var(--muted);margin:0 0 18px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px;cursor:pointer}
.card b{display:block;font-size:24px;font-variant-numeric:tabular-nums}.card span{color:var(--muted);font-size:12px}
.card.on{outline:2px solid var(--accent)}
pre.run{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px;white-space:pre-wrap;margin:0 0 16px;font:13px/1.5 ui-monospace,Consolas,monospace}
.bar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}input,select{background:var(--card);color:var(--text);border:1px solid var(--line);border-radius:8px;padding:8px 10px;font:inherit}
input{flex:1;min-width:180px}
.list{background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.row{display:grid;grid-template-columns:96px 90px 1fr 190px;gap:10px;padding:10px 12px;border-top:1px solid var(--line);cursor:pointer;align-items:center}
.list>.row:first-child{border-top:0}.row:hover{background:var(--greybg)}.t{font-weight:600}.m{color:var(--muted);font-size:12px}
.pill{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;font-weight:600;white-space:nowrap}
.s-ok{color:var(--ok);background:var(--okbg)}.s-warn{color:var(--warn);background:var(--warnbg)}.s-bad{color:var(--bad);background:var(--badbg)}
.s-info{color:var(--info);background:var(--infobg)}.s-grey{color:var(--grey);background:var(--greybg)}
.detail{display:none;padding:4px 12px 14px 12px;border-top:1px dashed var(--line)}.detail.open{display:block}
.detail ol{margin:6px 0 10px 18px;padding:0}.detail li{margin:2px 0}a{color:var(--accent)}
@media (max-width:700px){.row{grid-template-columns:1fr;gap:4px}}
</style></head><body><main>
<header style="display:flex;align-items:center;gap:14px;margin-bottom:14px"><img src="assets/branding/logo.jpg" alt="TerraQuest Logo" style="width:52px;height:52px;border-radius:50%;object-fit:cover;box-shadow:0 0 14px rgba(37,99,235,0.35);border:2px solid var(--accent)"><div><h1 style="margin:0;font-size:22px;display:flex;align-items:center;gap:8px">TerraQuest <span style="font-size:13px;color:var(--muted);font-weight:normal">@TheTerraQuest_92</span></h1><p class="sub" id="sub" style="margin:2px 0 0"></p></div></header>
<div class="cards" id="cards"></div>
<pre class="run" id="run"></pre>
<div class="bar"><input id="q" placeholder="Search title, hook or script"><select id="kind"><option value="">Shorts and long videos</option><option>Short</option><option>Long video</option></select></div>
<div class="list" id="list"></div>
</main>
<script>
const D=__DATA__;
const ORDER=["Script pending","Script ready","Making","Created, waiting upload","Uploaded, scheduled","Published","Failed"];
const CLS={"Published":"s-ok","Uploaded, scheduled":"s-info","Created, waiting upload":"s-warn","Making":"s-warn","Script ready":"s-grey","Script pending":"s-grey","Failed":"s-bad","Rejected":"s-bad"};
let filter="";const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
document.getElementById("sub").textContent="Updated "+D.built+" · every video from script to publishing · click a row to read its script";
document.getElementById("run").textContent=D.lastRun;
function cards(){const n={};D.rows.forEach(r=>n[r.status]=(n[r.status]||0)+1);
document.getElementById("cards").innerHTML=[["","All videos",D.rows.length],...ORDER.filter(s=>n[s]).map(s=>[s,s,n[s]])]
.map(([k,l,v])=>`<div class="card ${filter===k?"on":""}" data-k="${esc(k)}"><b>${v}</b><span>${esc(l)}</span></div>`).join("");
document.querySelectorAll(".card").forEach(c=>c.onclick=()=>{filter=c.dataset.k;cards();list()});}
function list(){const q=document.getElementById("q").value.toLowerCase(),k=document.getElementById("kind").value;
const rows=D.rows.filter(r=>(!filter||r.status===filter)&&(!k||r.kind===k)&&(!q||(r.title+" "+r.hook+" "+r.script.join(" ")).toLowerCase().includes(q)));
document.getElementById("list").innerHTML=rows.slice(0,800).map((r,i)=>`<div class="row" data-i="${i}"><div>${esc(r.date)}<div class="m">${esc(r.kind)}</div></div>
<div class="m">${esc(r.category)}${r.seconds?"<br>"+Math.floor(r.seconds/60)+":"+String(Math.round(r.seconds%60)).padStart(2,"0"):""}</div>
<div><div class="t">${esc(r.title)||"<span class=m>(topic planned, script not written yet)</span>"}</div><div class="m">${esc(r.hook)}</div></div>
<div><span class="pill ${CLS[r.status]||"s-grey"}">${esc(r.status)}</span>${r.publish_at?`<div class="m">public at ${esc(r.publish_at)}</div>`:""}</div></div>
<div class="detail" id="d${i}">${r.url?`<p><a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.url)}</a>${r.uploaded?" · uploaded "+esc(r.uploaded):""}</p>`:""}
${r.script.length?`<b>Script</b><ol>${r.script.map(s=>`<li>${esc(s)}</li>`).join("")}</ol>`:"<p class=m>No script yet.</p>"}
${r.description?`<b>Description</b><p style="white-space:pre-wrap">${esc(r.description)}</p>`:""}${r.job?`<p class=m>job: ${esc(r.job)}</p>`:""}</div>`).join("")||"<div class=row>No videos match.</div>";
document.querySelectorAll(".row[data-i]").forEach(el=>el.onclick=()=>document.getElementById("d"+el.dataset.i).classList.toggle("open"));}
document.getElementById("q").oninput=list;document.getElementById("kind").onchange=list;cards();list();
</script></body></html>
"""

if __name__ == "__main__":
    print(build())
