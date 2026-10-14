"""Generate the fictional sample data used in this demo.

Everything created here is invented: the project, the permit, the plan sheets,
the inspections and the site videos. Nothing comes from a real project.

Output:
  docs/files/        source documents (PDF) linked from the timeline
  docs/videos/       short placeholder site videos
  samples/checks/    two monitoring snapshots (morning and evening of one day)
  data/              document log and video log (the "Job 1" database)

Usage:
  python scripts/make_demo_data.py
"""

import csv
import hashlib
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent.parent
FILES = ROOT / "docs" / "files"
VIDEOS = ROOT / "docs" / "videos"
CHECKS = ROOT / "samples" / "checks"
DATA = ROOT / "data"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

PROJECT = "Sample Residence - 100 Example Lane"
CITY = "Sample City Building Department"
BANNER = "FICTIONAL SAMPLE - NOT A REAL DOCUMENT"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def pdf_date(dt: datetime) -> str:
    return dt.strftime("D:%Y%m%d%H%M%S-04'00'")


def finish_pdf(tmp: Path, out: Path, title: str, author: str, created: datetime, modified: datetime):
    """Rewrite PDF metadata with fixed dates so the demo is reproducible."""
    reader = PdfReader(str(tmp))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata({
        "/Title": title,
        "/Author": author,
        "/Creator": "Demo generator",
        "/Producer": "ReportLab + pypdf",
        "/CreationDate": pdf_date(created),
        "/ModDate": pdf_date(modified),
    })
    with open(out, "wb") as f:
        writer.write(f)
    tmp.unlink()


def header(c, title, sub):
    w, h = c._pagesize
    c.setFillColorRGB(0.75, 0.1, 0.1)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, h - 30, BANNER)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, h - 60, title)
    c.setFont("Helvetica", 10)
    c.drawString(40, h - 76, sub)
    c.line(40, h - 84, w - 40, h - 84)


def permit_card(out: Path, version: int, expires: str, modified: datetime):
    tmp = out.with_suffix(".tmp.pdf")
    c = canvas.Canvas(str(tmp), pagesize=letter, invariant=1)
    header(c, f"{CITY} - Building Permit", PROJECT)
    rows = [
        ("Permit number", "BP-26-0142"),
        ("Permit type", "New single-family residence"),
        ("Status", "Issued" if version == 1 else "Issued - extension granted"),
        ("Issue date", "2026-02-03"),
        ("Expiration date", expires),
        ("Card revision", str(version)),
        ("Contractor", "Example Builders LLC (fictional)"),
    ]
    y = 660
    for k, v in rows:
        c.setFont("Helvetica", 11)
        c.drawString(60, y, f"{k}: {v}")
        y -= 22
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(60, y - 20, "Keep this card visible on site. Inspections must be requested through the portal.")
    c.save()
    finish_pdf(tmp, out, "Permit Card BP-26-0142", CITY, datetime(2026, 2, 3, 9, 12), modified)


def plan_sheet(out: Path, rev: int, modified: datetime):
    """Simple floor plan. Rev 1 widens the west window and moves the interior door."""
    tmp = out.with_suffix(".tmp.pdf")
    c = canvas.Canvas(str(tmp), pagesize=landscape(letter), invariant=1)
    w, h = landscape(letter)
    header(c, f"A-101 Floor Plan - Rev {rev}", PROJECT)
    c.setLineWidth(4)
    c.rect(120, 140, 520, 300)          # outer walls
    c.setLineWidth(2)
    c.line(380, 140, 380, 440)          # interior wall
    # interior door opening (moves in Rev 1)
    door_y = 260 if rev == 0 else 320
    c.setStrokeColorRGB(1, 1, 1)
    c.setLineWidth(4)
    c.line(380, door_y, 380, door_y + 40)
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1)
    c.arc(340, door_y - 40, 420, door_y + 40, 0, 90)
    # west window (wider in Rev 1)
    win_h = 60 if rev == 0 else 110
    c.setLineWidth(1)
    c.rect(114, 290 - win_h / 2, 12, win_h)
    # labels
    c.setFont("Helvetica", 11)
    c.drawString(200, 300, "LIVING")
    c.drawString(470, 300, "BEDROOM")
    c.setFont("Helvetica", 8)
    c.drawString(60, 290, f"W1 {'3-0' if rev == 0 else '5-6'}")
    # title block
    c.rect(w - 230, 40, 190, 70)
    c.setFont("Helvetica", 8)
    c.drawString(w - 222, 95, "Sheet: A-101")
    c.drawString(w - 222, 82, f"Revision: {rev}")
    c.drawString(w - 222, 69, "Date: " + ("2026-02-10" if rev == 0 else "2026-04-07"))
    c.drawString(w - 222, 56, "Example Architects (fictional)")
    c.save()
    finish_pdf(tmp, out, f"A-101 Floor Plan Rev {rev}", "Example Architects",
               datetime(2026, 2, 10, 14, 0), modified)


def simple_doc(out: Path, title: str, lines, author: str, created: datetime):
    tmp = out.with_suffix(".tmp.pdf")
    c = canvas.Canvas(str(tmp), pagesize=letter, invariant=1)
    header(c, title, PROJECT)
    c.setFont("Helvetica", 11)
    y = 660
    for line in lines:
        c.drawString(60, y, line)
        y -= 20
    c.save()
    finish_pdf(tmp, out, title, author, created, created)


def video(out: Path, label: str, created: str):
    vf = (
        f"drawtext=fontfile={FONT}:text='{label}':fontcolor=white:fontsize=26:"
        "x=(w-text_w)/2:y=(h-text_h)/2-20,"
        f"drawtext=fontfile={FONT}:text='{BANNER}':fontcolor=0xffcccc:fontsize=16:"
        "x=(w-text_w)/2:y=(h-text_h)/2+30"
    )
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=0x334455:s=640x360:d=4:r=15",
        "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "32",
        "-metadata", f"creation_time={created}",
        str(out),
    ], check=True)


def main():
    for d in (FILES, VIDEOS, DATA):
        d.mkdir(parents=True, exist_ok=True)
    if CHECKS.exists():
        shutil.rmtree(CHECKS)

    # ---- source documents -------------------------------------------------
    permit_card(FILES / "BP-26-0142_Permit_Card_r1.pdf", 1, "2026-08-02", datetime(2026, 2, 3, 9, 12))
    permit_card(FILES / "BP-26-0142_Permit_Card_r2.pdf", 2, "2026-12-01", datetime(2026, 6, 2, 15, 41))
    plan_sheet(FILES / "A-101_Floor_Plan_Rev0.pdf", 0, datetime(2026, 2, 10, 14, 0))
    plan_sheet(FILES / "A-101_Floor_Plan_Rev1.pdf", 1, datetime(2026, 4, 7, 11, 25))
    simple_doc(FILES / "INSP-0318_Foundation_Result.pdf", "Inspection Result - Foundation",
               ["Inspection date: 2026-03-18", "Inspection type: Foundation", "Result: APPROVED",
                "Inspector ID: 0457"], CITY, datetime(2026, 3, 18, 16, 5))
    simple_doc(FILES / "INSP-0514_Framing_Correction_Notice.pdf", "Correction Notice - Framing",
               ["Inspection date: 2026-05-14", "Inspection type: Framing", "Result: FAILED",
                "Item 1: Missing hold-down at west wall, grid line 1.",
                "Item 2: Header size at W1 does not match approved sheet A-101 Rev 1.",
                "Re-inspection required."], CITY, datetime(2026, 5, 14, 17, 30))
    simple_doc(FILES / "INSP-0708_Framing_Result.pdf", "Inspection Result - Framing (re-inspection)",
               ["Inspection date: 2026-07-08", "Inspection type: Framing re-inspection",
                "Result: APPROVED", "Inspector ID: 0457"], CITY, datetime(2026, 7, 8, 10, 50))
    simple_doc(FILES / "RFI-007_Response.pdf", "RFI 007 - Response",
               ["Question: Confirm header size at W1 after Rev 1 widening.",
                "Answer: Use 2-ply LVL 1-3/4 x 11-7/8 per structural note S-3.",
                "Answered by: Example Engineers (fictional)", "Date: 2026-06-02"],
               "Example Engineers", datetime(2026, 6, 2, 13, 2))
    simple_doc(FILES / "Site_Logistics_Draft.pdf", "Site Logistics Plan - Draft",
               ["Draft for discussion only.", "Dumpster location: driveway, north side.",
                "Material staging: rear yard."], "Example Builders LLC", datetime(2026, 5, 20, 9, 0))

    # ---- site videos (original camera names) -----------------------------
    originals = [
        ("VID_20260305_081422.mp4", "Site video - 2026-03-05 - foundation pour", "2026-03-05T08:14:22Z"),
        ("VID_20260422_163010.mp4", "Site video - 2026-04-22 - framing, west wall", "2026-04-22T16:30:10Z"),
        ("VID_20260529_095507.mp4", "Site video - 2026-05-29 - correction work", "2026-05-29T09:55:07Z"),
    ]
    raw = ROOT / "samples" / "camera_originals"
    raw.mkdir(parents=True, exist_ok=True)
    for name, label, created in originals:
        video(raw / name, label, created)

    # ---- two monitoring snapshots on 2026-06-02 ---------------------------
    am = CHECKS / "2026-06-02_0700"
    pm = CHECKS / "2026-06-02_1900"
    for d in (am / "city_portal", am / "procore", pm / "city_portal", pm / "procore"):
        d.mkdir(parents=True, exist_ok=True)
    shutil.copy(FILES / "BP-26-0142_Permit_Card_r1.pdf", am / "city_portal" / "BP-26-0142 Permit Card.pdf")
    shutil.copy(FILES / "INSP-0514_Framing_Correction_Notice.pdf", am / "city_portal" / "INSP-0514 Correction Notice.pdf")
    shutil.copy(FILES / "A-101_Floor_Plan_Rev1.pdf", am / "procore" / "A-101_Floor Plan_Rev1.pdf")
    shutil.copy(FILES / "Site_Logistics_Draft.pdf", am / "procore" / "Site_Logistics_Draft.pdf")

    shutil.copy(FILES / "BP-26-0142_Permit_Card_r2.pdf", pm / "city_portal" / "BP-26-0142 Permit Card.pdf")
    shutil.copy(FILES / "INSP-0514_Framing_Correction_Notice.pdf", pm / "city_portal" / "INSP-0514 Correction Notice.pdf")
    shutil.copy(FILES / "A-101_Floor_Plan_Rev1.pdf", pm / "procore" / "A-101_Floor  Plan_Rev1.pdf")  # two spaces
    shutil.copy(FILES / "RFI-007_Response.pdf", pm / "procore" / "RFI-007_Response.pdf")

    # ---- document log (Job 1 database, Airtable-style export) -------------
    docs = [
        ("DOC-001", "2026-02-03", "City portal", "BP-26-0142_Permit_Card_r1.pdf", "r1", "Issued", "Permit card, expiration 2026-08-02"),
        ("DOC-002", "2026-02-10", "Procore", "A-101_Floor_Plan_Rev0.pdf", "Rev 0", "Current", "Floor plan, first issue"),
        ("DOC-003", "2026-03-18", "City portal", "INSP-0318_Foundation_Result.pdf", "-", "Approved", "Foundation inspection result"),
        ("DOC-004", "2026-04-07", "Procore", "A-101_Floor_Plan_Rev1.pdf", "Rev 1", "Current", "Supersedes DOC-002"),
        ("DOC-005", "2026-05-14", "City portal", "INSP-0514_Framing_Correction_Notice.pdf", "-", "Failed", "Framing correction notice, 2 items"),
        ("DOC-006", "2026-05-20", "Procore", "Site_Logistics_Draft.pdf", "Draft", "Removed 2026-06-02", "No longer listed in Procore at the 19:00 check"),
        ("DOC-007", "2026-06-02", "City portal", "BP-26-0142_Permit_Card_r2.pdf", "r2", "Issued - extension", "Expiration changed 2026-08-02 -> 2026-12-01"),
        ("DOC-008", "2026-06-02", "Procore", "RFI-007_Response.pdf", "-", "Answered", "New file at the 19:00 check"),
        ("DOC-009", "2026-07-08", "City portal", "INSP-0708_Framing_Result.pdf", "-", "Approved", "Framing re-inspection result"),
    ]
    with open(DATA / "document_log.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["doc_id", "first_seen", "source", "file_name", "version", "status",
                     "size_bytes", "size_kb", "sha256", "pdf_created", "pdf_modified", "notes"])
        for doc_id, seen, src, name, ver, status, note in docs:
            p = FILES / name
            meta = PdfReader(str(p)).metadata
            wr.writerow([doc_id, seen, src, name, ver, status, p.stat().st_size,
                         f"{p.stat().st_size / 1024:.2f}", sha256(p),
                         meta.get("/CreationDate", ""), meta.get("/ModDate", ""), note])

    # ---- video log: originals untouched, renamed copies for the report -----
    renamed = [
        ("VID-001", "2026-03-05", "08:14", "foundation-pour"),
        ("VID-002", "2026-04-22", "16:30", "framing-west-wall"),
        ("VID-003", "2026-05-29", "09:55", "correction-work"),
    ]
    base = "https://rmatoso.github.io/construction-doc-timeline/videos/"
    with open(DATA / "video_log.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["video_id", "date", "time", "original_name", "copy_name",
                     "size_bytes", "sha256_original", "sha256_copy", "link"])
        for (orig, _, _), (vid, date, time, slug) in zip(originals, renamed):
            src = raw / orig
            copy_name = f"{date}_{time.replace(':', '')}_{slug}.mp4"
            dst = VIDEOS / copy_name
            shutil.copy2(src, dst)  # byte-for-byte copy, no re-encoding
            wr.writerow([vid, date, time, orig, copy_name, src.stat().st_size,
                         sha256(src), sha256(dst), base + copy_name])

    print("Demo data created.")


if __name__ == "__main__":
    main()
