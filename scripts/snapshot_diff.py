"""Compare two monitoring checks and report every difference.

Each check is a folder with the files downloaded at that time (using the
"download original" option of each source). The script builds a manifest for
both folders and reports:

  - new files and removed files
  - renamed files (same SHA-256 hash, different name), including
    spacing-only or spelling-only changes
  - content changes (hash changed), with the size difference in KB
  - PDF metadata changes (title, author, creation and modification dates)
  - changed lines in the first page text (catches permit header edits such as
    expiration dates)
  - presence of digital signature fields

It writes a Markdown report and a JSON manifest for the newer check, so the
next run can compare against it.

Usage:
  python scripts/snapshot_diff.py samples/checks/2026-06-02_0700 samples/checks/2026-06-02_1900
"""

import difflib
import hashlib
import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader

META_KEYS = ("/Title", "/Author", "/Creator", "/Producer", "/CreationDate", "/ModDate")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def pdf_info(path: Path) -> dict:
    info = {"meta": {}, "first_page": [], "signature_fields": 0, "pages": 0}
    try:
        reader = PdfReader(str(path))
    except Exception as exc:  # damaged or not a PDF
        info["error"] = str(exc)
        return info
    meta = reader.metadata or {}
    info["meta"] = {k: str(meta.get(k, "")) for k in META_KEYS}
    info["pages"] = len(reader.pages)
    text = reader.pages[0].extract_text() or "" if reader.pages else ""
    info["first_page"] = [ln.strip() for ln in text.splitlines() if ln.strip()]
    fields = reader.get_fields() or {}
    info["signature_fields"] = sum(1 for f in fields.values() if f.get("/FT") == "/Sig")
    return info


def manifest(folder: Path) -> dict:
    out = {}
    for p in sorted(folder.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(folder).as_posix()
        entry = {"size_bytes": p.stat().st_size, "sha256": sha256(p)}
        if p.suffix.lower() == ".pdf":
            entry.update(pdf_info(p))
        out[rel] = entry
    return out


def show_name(name: str) -> str:
    """Make spaces visible so a double space is obvious in the report."""
    return name.replace(" ", "·")


def name_change_kind(a: str, b: str) -> str:
    if re.sub(r"\s+", " ", a) == re.sub(r"\s+", " ", b):
        return "spacing only"
    if a.lower() == b.lower():
        return "capitalization only"
    return "name changed"


def compare(old: dict, new: dict) -> list:
    lines = []
    old_names, new_names = set(old), set(new)
    removed = sorted(old_names - new_names)
    added = sorted(new_names - old_names)

    # renames: a removed and an added file with the same hash
    renames = []
    for r in list(removed):
        for a in list(added):
            if old[r]["sha256"] == new[a]["sha256"]:
                renames.append((r, a))
                removed.remove(r)
                added.remove(a)
                break

    for r, a in renames:
        lines.append(f"- RENAMED ({name_change_kind(r, a)}): `{show_name(r)}` -> `{show_name(a)}` "
                     f"(content identical, SHA-256 {new[a]['sha256'][:12]})")
    for a in added:
        lines.append(f"- NEW: `{show_name(a)}` ({new[a]['size_bytes'] / 1024:.2f} KB, "
                     f"SHA-256 {new[a]['sha256'][:12]})")
    for r in removed:
        lines.append(f"- REMOVED: `{show_name(r)}` (was {old[r]['size_bytes'] / 1024:.2f} KB, "
                     f"SHA-256 {old[r]['sha256'][:12]})")

    for name in sorted(old_names & new_names):
        o, n = old[name], new[name]
        if o["sha256"] == n["sha256"]:
            continue
        delta = (n["size_bytes"] - o["size_bytes"]) / 1024
        lines.append(f"- CHANGED: `{show_name(name)}` size {o['size_bytes'] / 1024:.2f} KB -> "
                     f"{n['size_bytes'] / 1024:.2f} KB ({delta:+.2f} KB), "
                     f"SHA-256 {o['sha256'][:12]} -> {n['sha256'][:12]}")
        for k in META_KEYS:
            ov, nv = o.get("meta", {}).get(k, ""), n.get("meta", {}).get(k, "")
            if ov != nv:
                lines.append(f"    - metadata {k[1:]}: `{ov}` -> `{nv}`")
        diff = [d for d in difflib.unified_diff(o.get("first_page", []), n.get("first_page", []),
                                                lineterm="", n=0)
                if d[:1] in "+-" and not d.startswith(("+++", "---"))]
        for d in diff:
            lines.append(f"    - page 1 text {'removed' if d[0] == '-' else 'added'}: `{d[1:]}`")
        if o.get("signature_fields") != n.get("signature_fields"):
            lines.append(f"    - signature fields: {o.get('signature_fields')} -> {n.get('signature_fields')}")

    return lines


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    old_dir, new_dir = Path(sys.argv[1]), Path(sys.argv[2])
    old, new = manifest(old_dir), manifest(new_dir)

    (new_dir.parent / f"{new_dir.name}_manifest.json").write_text(
        json.dumps(new, indent=2), encoding="utf-8")

    changes = compare(old, new)
    signed = [n for n, e in new.items() if e.get("signature_fields")]
    report = [
        f"# Check comparison: {old_dir.name} -> {new_dir.name}",
        "",
        f"Files in previous check: {len(old)}  ",
        f"Files in this check: {len(new)}  ",
        f"Differences found: {sum(1 for c in changes if c.startswith('- '))}",
        "",
        "Spaces in file names are shown as a middle dot (·) so spacing changes are visible.",
        "",
        "## Differences",
        "",
        *(changes or ["No differences."]),
        "",
        "## Digital signatures",
        "",
        (f"Files with signature fields: {', '.join(signed)}. Validate them in Adobe Acrobat "
         "(Signature panel) or with pyHanko before logging them as signed.") if signed
        else "No signature fields found in this check.",
        "",
    ]
    out = new_dir.parent / f"report_{old_dir.name}_to_{new_dir.name}.md"
    out.write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))
    print(f"Report saved to {out}")


if __name__ == "__main__":
    main()
