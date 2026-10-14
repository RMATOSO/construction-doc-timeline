# Construction Document Control and Timeline (demo)

A small toolkit for tracking construction project documents and turning the log into a dated, printable timeline. All data in this repository is fictional.

**Live sample report:** https://rmatoso.github.io/construction-doc-timeline/

## What it does

**1. Twice-daily document checks** (`scripts/snapshot_diff.py`)

Compares the files downloaded in two checks (for example 07:00 and 19:00) and lists every difference:

- new and removed files
- renamed files, including spacing-only changes (a double space in a file name is flagged)
- content changes, detected by SHA-256 hash, with the size difference in KB (0.01 KB precision)
- PDF metadata changes (title, author, creation and modification dates)
- changed lines in the first page, which catches permit header edits such as a new expiration date
- digital signature fields present in each PDF

Sample output: [`samples/checks/report_2026-06-02_0700_to_2026-06-02_1900.md`](samples/checks/report_2026-06-02_0700_to_2026-06-02_1900.md)

**2. Visual overlay of plan revisions** (`scripts/overlay_compare.py`)

Overlays two versions of a sheet. Red shows what was removed, blue shows what was added, and each changed area is boxed and numbered. It does the same job as Bluebeam Revu's Overlay Pages, and its output can be confirmed in Bluebeam when the client uses it.

**3. Timeline report** (`scripts/build_timeline.py`)

Builds `docs/index.html` from the logs:

- one entry per dated record, with a short factual description and links to the source documents
- every entry must point to a `doc_id` or `video_id` that exists in the log, so nothing appears in the timeline without a logged source
- before building, it recalculates the SHA-256 of every linked file and stops if any file is missing or changed
- a static QR code for each entry with video; the code encodes the video link directly, with no redirect service in between
- print-friendly layout (links are printed in full)

## Data

| File | Content |
|---|---|
| `data/document_log.csv` | Document log: ID, first seen, source, file name, version, status, size, SHA-256, PDF dates, notes. Same columns can live in Airtable. |
| `data/video_log.csv` | Video log: original camera name, renamed copy, hashes of both, link. |
| `data/timeline_entries.csv` | Timeline entries: date, category, title, factual description, linked IDs. |

## Video handling

- Originals are never edited, trimmed or re-encoded. The report uses byte-for-byte copies, and the log stores the hash of both the original and the copy to prove they are identical.
- Copies follow one naming pattern: `YYYY-MM-DD_HHMM_short-description.mp4`, so sorting by name is sorting by date.
- In a real project the videos stay in the client's own Google Drive with sharing restricted to approved people. The `link` column holds that Drive link, and the QR code encodes it directly. In this demo the videos are placeholders hosted on GitHub Pages.

## Run it

Requires Python 3.10+.

```
pip install -r requirements.txt
python scripts/make_demo_data.py
python scripts/snapshot_diff.py samples/checks/2026-06-02_0700 samples/checks/2026-06-02_1900
python scripts/overlay_compare.py docs/files/A-101_Floor_Plan_Rev0.pdf docs/files/A-101_Floor_Plan_Rev1.pdf docs/img/A-101_Rev0_vs_Rev1.png
python scripts/build_timeline.py
```

Then open `docs/index.html`.

## Author

Rodrigo Matoso, court-appointed real estate appraiser and broker in Brazil, with a degree in Systems Analysis and Development. Built with AI-assisted coding.
