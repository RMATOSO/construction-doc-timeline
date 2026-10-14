"""Build the HTML timeline report from the document log and video log.

Every timeline entry must point to records that exist in the logs:
  - each doc_id must exist in data/document_log.csv
  - each video_id must exist in data/video_log.csv
Before writing the report, the script recalculates the SHA-256 hash of every
linked file and compares it with the logged hash. If anything is missing or
does not match, it stops and says which record failed.

QR codes are static: each one encodes the video link directly (in a real
project, the client's Google Drive link with restricted sharing). Nothing
redirects through a third-party QR service.

Usage:
  python scripts/build_timeline.py
Output:
  docs/index.html
"""

import csv
import hashlib
import html
import sys
from collections import OrderedDict
from datetime import date, datetime
from pathlib import Path

import segno

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
DATA = ROOT / "data"

PROJECT = "Sample Residence - 100 Example Lane"
PREPARED_BY = "Rodrigo Matoso"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(name):
    with open(DATA / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def esc(s):
    return html.escape(s or "", quote=True)


def verify(docs, videos):
    errors = []
    for d in docs.values():
        p = DOCS / "files" / d["file_name"]
        if not p.exists():
            errors.append(f"{d['doc_id']}: file not found ({p.name})")
        elif sha256(p) != d["sha256"]:
            errors.append(f"{d['doc_id']}: hash does not match the log ({p.name})")
    for v in videos.values():
        p = DOCS / "videos" / v["copy_name"]
        if not p.exists():
            errors.append(f"{v['video_id']}: file not found ({p.name})")
        elif sha256(p) != v["sha256_copy"]:
            errors.append(f"{v['video_id']}: copy hash does not match the log ({p.name})")
        elif v["sha256_copy"] != v["sha256_original"]:
            errors.append(f"{v['video_id']}: copy differs from the original")
    return errors


def qr_svg(url):
    return segno.make(url, error="q").svg_inline(scale=3, border=4, dark="#14213d", omitsize=True)


def entry_html(e, docs, videos):
    doc_ids = [x for x in e["doc_ids"].split(";") if x]
    vid_ids = [x for x in e["video_ids"].split(";") if x]
    parts = []
    for i in doc_ids:
        d = docs[i]
        parts.append(
            f'<li><a href="files/{esc(d["file_name"])}">{esc(d["file_name"])}</a>'
            f'<span class="tag">{esc(i)}</span><span class="tag">{esc(d["source"])}</span>'
            f'<span class="tag">{esc(d["version"])}</span>'
            f'<span class="hash" title="SHA-256 {esc(d["sha256"])}">SHA-256 {esc(d["sha256"][:12])}</span></li>'
        )
    for i in vid_ids:
        v = videos[i]
        parts.append(
            f'<li><a href="{esc(v["link"])}">{esc(v["copy_name"])}</a>'
            f'<span class="tag">{esc(i)}</span><span class="tag">original: {esc(v["original_name"])}</span>'
            f'<span class="hash" title="SHA-256 {esc(v["sha256_original"])}">SHA-256 {esc(v["sha256_original"][:12])}</span></li>'
        )
    qr = ""
    for i in vid_ids:
        v = videos[i]
        qr += (f'<figure class="qr">{qr_svg(v["link"])}'
               f'<figcaption>Scan to open the video of {esc(v["date"])}</figcaption></figure>')
    img = ""
    if e["image"]:
        img = (f'<figure class="overlay"><a href="{esc(e["image"])}"><img src="{esc(e["image"])}" '
               f'alt="Overlay comparison"></a><figcaption><span class="sw red"></span>removed in new version '
               f'<span class="sw blue"></span>added in new version <span class="sw grey"></span>unchanged'
               f'</figcaption></figure>')
    d = datetime.strptime(e["date"], "%Y-%m-%d")
    return f'''
    <article class="entry{' has-qr' if qr else ''}" data-cat="{esc(e['category'])}">
      <div class="when"><span class="day">{d.day:02d}</span><span class="mon">{d.strftime('%b %Y')}</span></div>
      <div class="body">
        <p class="cat">{esc(e['category'])}</p>
        <h3>{esc(e['title'])}</h3>
        <p>{esc(e['description'])}</p>
        <ul class="src">{''.join(parts)}</ul>
        {img}
      </div>
      {f'<div class="qrs">{qr}</div>' if qr else ''}
    </article>'''


CSS = """
:root{--ink:#14213d;--muted:#5c6577;--line:#d9dee7;--bg:#f6f7f9;--card:#fff;--accent:#1d4e89;--red:#d62828;--blue:#1e5adc}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 "Segoe UI",system-ui,-apple-system,Roboto,Arial,sans-serif}
.wrap{max-width:980px;margin:0 auto;padding:32px 16px 64px}
header{border-bottom:2px solid var(--ink);padding-bottom:18px;margin-bottom:20px}
.eyebrow{text-transform:uppercase;letter-spacing:.12em;font-size:12px;color:var(--accent);margin:0 0 6px;font-weight:600}
h1{font-size:28px;margin:0 0 10px;line-height:1.2}
.meta{display:flex;flex-wrap:wrap;gap:6px 22px;color:var(--muted);font-size:13px;margin:0;padding:0;list-style:none}
.meta b{color:var(--ink);font-weight:600}
.notice{background:#fff4e5;border:1px solid #f0c27a;border-radius:6px;padding:10px 14px;font-size:13px;margin:16px 0}
.check{background:#eaf4ec;border:1px solid #9cc9a6;border-radius:6px;padding:10px 14px;font-size:13px;margin:0 0 18px}
.filters{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 8px}
.filters button{border:1px solid var(--line);background:#fff;color:var(--ink);border-radius:999px;padding:5px 12px;font:inherit;font-size:13px;cursor:pointer}
.filters button[aria-pressed=true]{background:var(--ink);color:#fff;border-color:var(--ink)}
h2.month{font-size:14px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin:28px 0 10px;border-bottom:1px solid var(--line);padding-bottom:4px}
.entry{display:grid;grid-template-columns:78px 1fr;gap:16px;background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:6px;padding:16px 18px;margin:0 0 12px;break-inside:avoid}
.entry.has-qr{grid-template-columns:78px 1fr 150px}
.when{text-align:center}
.day{display:block;font-size:30px;font-weight:700;line-height:1}
.mon{display:block;font-size:12px;color:var(--muted);margin-top:4px}
.cat{margin:0;font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--accent);font-weight:600}
h3{margin:2px 0 6px;font-size:17px}
.body p{margin:0 0 8px}
.src{list-style:none;margin:8px 0 0;padding:0;font-size:13px}
.src li{padding:5px 0;border-top:1px dashed var(--line);display:flex;flex-wrap:wrap;gap:4px 8px;align-items:center}
.src a{color:var(--accent);font-weight:600;word-break:break-all}
.tag{background:#eef1f6;border-radius:4px;padding:1px 6px;font-size:12px;color:var(--muted)}
.hash{font-family:ui-monospace,Consolas,monospace;font-size:12px;color:var(--muted)}
.qrs{display:flex;flex-direction:column;gap:10px;align-items:center}
.qr{margin:0;text-align:center}
.qr svg{width:128px;height:128px}
.qr figcaption{font-size:11px;color:var(--muted)}
.overlay{margin:12px 0 0}
.overlay img{width:100%;max-width:620px;display:block;border:1px solid var(--line);border-radius:4px;background:#fff}
.overlay figcaption{font-size:12px;color:var(--muted);display:flex;flex-wrap:wrap;gap:4px 10px;align-items:center}
.sw{display:inline-block;width:12px;height:12px;border-radius:2px;margin-right:-6px}
.sw.red{background:var(--red)}.sw.blue{background:var(--blue)}.sw.grey{background:#aaa}
footer{margin-top:32px;font-size:12px;color:var(--muted);border-top:1px solid var(--line);padding-top:12px}
@media (max-width:640px){
  .entry,.entry.has-qr{grid-template-columns:1fr}
  .when{text-align:left;display:flex;gap:8px;align-items:baseline}
  .qrs{align-items:flex-start}
}
@media print{
  body{background:#fff;font-size:11pt}
  .wrap{max-width:none;padding:0}
  .filters{display:none}
  .entry{border:1px solid #999;border-left:4px solid #333;box-shadow:none}
  .src a::after{content:" (" attr(href) ")";font-weight:400;color:#555}
  .notice,.check{border-color:#999;background:#fff}
  h2.month{break-after:avoid}
  @page{margin:16mm}
}
"""

JS = """
const buttons=document.querySelectorAll('.filters button');
buttons.forEach(b=>b.addEventListener('click',()=>{
  buttons.forEach(x=>x.setAttribute('aria-pressed','false'));
  b.setAttribute('aria-pressed','true');
  const c=b.dataset.cat;
  document.querySelectorAll('.entry').forEach(e=>{e.hidden=!(c==='All'||e.dataset.cat===c)});
  document.querySelectorAll('h2.month').forEach(h=>{
    let n=h.nextElementSibling,any=false;
    while(n&&n.classList.contains('entry')){if(!n.hidden)any=true;n=n.nextElementSibling}
    h.hidden=!any;
  });
}));
"""


def main():
    docs = {d["doc_id"]: d for d in read_csv("document_log.csv")}
    videos = {v["video_id"]: v for v in read_csv("video_log.csv")}
    entries = sorted(read_csv("timeline_entries.csv"), key=lambda e: e["date"])

    errors = verify(docs, videos)
    for e in entries:
        for i in filter(None, e["doc_ids"].split(";")):
            if i not in docs:
                errors.append(f"{e['date']} '{e['title']}': {i} is not in the document log")
        for i in filter(None, e["video_ids"].split(";")):
            if i not in videos:
                errors.append(f"{e['date']} '{e['title']}': {i} is not in the video log")
    if errors:
        print("Report not built. Fix these records first:")
        print("\n".join("  - " + x for x in errors))
        sys.exit(1)

    months = OrderedDict()
    for e in entries:
        key = datetime.strptime(e["date"], "%Y-%m-%d").strftime("%B %Y")
        months.setdefault(key, []).append(e)

    cats = ["All"] + sorted({e["category"] for e in entries})
    filters = "".join(f'<button type="button" data-cat="{esc(c)}" aria-pressed="{str(c == "All").lower()}">{esc(c)}</button>'
                      for c in cats)
    body = ""
    for m, es in months.items():
        body += f'<h2 class="month">{esc(m)}</h2>' + "".join(entry_html(e, docs, videos) for e in es)

    first, last = entries[0]["date"], entries[-1]["date"]
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Project Record Timeline</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<header>
  <p class="eyebrow">Project record timeline</p>
  <h1>{esc(PROJECT)}</h1>
  <ul class="meta">
    <li>Period: <b>{first} to {last}</b></li>
    <li>Entries: <b>{len(entries)}</b></li>
    <li>Documents logged: <b>{len(docs)}</b></li>
    <li>Videos logged: <b>{len(videos)}</b></li>
    <li>Generated: <b>{date.today().isoformat()}</b></li>
    <li>Prepared by: <b>{esc(PREPARED_BY)}</b></li>
  </ul>
</header>
<p class="notice"><b>Sample with fictional data.</b> The project, permit, plans, inspections and videos are invented to show the format. In a real project, documents and videos stay in the client's own Google Drive with restricted sharing, and the QR codes encode those Drive links directly.</p>
<p class="check">Integrity check passed when this report was generated: all {len(docs)} documents and {len(videos)} videos match the SHA-256 hashes recorded in the log. Each entry states only what the record shows.</p>
<nav class="filters" aria-label="Filter entries">{filters}</nav>
{body}
<footer>Source: data/document_log.csv and data/video_log.csv. Entries are sorted by record date. Video copies are byte-for-byte copies of the camera originals (same hash); originals are never edited, trimmed or re-encoded.</footer>
</div>
<script>{JS}</script>
</body>
</html>"""
    (DOCS / "index.html").write_text(page, encoding="utf-8")
    print(f"Integrity check passed: {len(docs)} documents, {len(videos)} videos.")
    print(f"Timeline written: docs/index.html ({len(entries)} entries)")


if __name__ == "__main__":
    main()
