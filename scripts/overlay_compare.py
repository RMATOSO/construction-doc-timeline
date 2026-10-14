"""Visual overlay comparison of two versions of a plan sheet.

Renders page 1 of both PDFs at the same resolution and builds one image:
  red   = only in the old version (removed)
  blue  = only in the new version (added)
  grey  = unchanged
It also prints the bounding boxes of the changed areas, so the change can be
described in the log ("west window widened", "door moved") after checking
the image.

This does the same job as Bluebeam Revu's Overlay Pages. When the client uses
Bluebeam, the result should be confirmed there too.

Usage:
  python scripts/overlay_compare.py OLD.pdf NEW.pdf OUT.png
"""

import sys

import pymupdf
from PIL import Image, ImageChops, ImageDraw, ImageFilter

DPI = 100


def render(path: str) -> Image.Image:
    doc = pymupdf.open(path)
    pix = doc[0].get_pixmap(dpi=DPI)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("L")


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    old, new = render(sys.argv[1]), render(sys.argv[2])
    if old.size != new.size:
        new = new.resize(old.size)

    # ink masks: 255 where there is a line
    old_ink = old.point(lambda v: 255 if v < 200 else 0)
    new_ink = new.point(lambda v: 255 if v < 200 else 0)
    removed = ImageChops.subtract(old_ink, new_ink)
    added = ImageChops.subtract(new_ink, old_ink)
    common = ImageChops.multiply(old_ink, new_ink)

    out = Image.new("RGB", old.size, "white")
    out.paste((170, 170, 170), mask=common)
    out.paste((214, 40, 40), mask=removed)
    out.paste((30, 90, 220), mask=added)

    # group changed pixels into regions and draw a box around each one
    changed = ImageChops.lighter(removed, added).filter(ImageFilter.MaxFilter(25))
    regions = []
    px = changed.load()
    w, h = changed.size
    seen = set()
    for y in range(0, h, 4):
        for x in range(0, w, 4):
            if px[x, y] and (x, y) not in seen:
                stack, box = [(x, y)], [x, y, x, y]
                while stack:
                    cx, cy = stack.pop()
                    if (cx, cy) in seen or not (0 <= cx < w and 0 <= cy < h) or not px[cx, cy]:
                        continue
                    seen.add((cx, cy))
                    box = [min(box[0], cx), min(box[1], cy), max(box[2], cx), max(box[3], cy)]
                    stack += [(cx + 4, cy), (cx - 4, cy), (cx, cy + 4), (cx, cy - 4)]
                regions.append(box)

    draw = ImageDraw.Draw(out)
    for i, (x0, y0, x1, y1) in enumerate(regions, 1):
        draw.rectangle([x0 - 4, y0 - 4, x1 + 4, y1 + 4], outline=(240, 160, 0), width=2)
        draw.text((x0, y0 - 16), f"#{i}", fill=(200, 120, 0))
    out.save(sys.argv[3])

    print(f"Changed areas: {len(regions)}")
    for i, (x0, y0, x1, y1) in enumerate(regions, 1):
        # convert pixels back to inches from the top-left corner of the sheet
        print(f"  #{i}: x {x0 / DPI:.1f}-{x1 / DPI:.1f} in, y {y0 / DPI:.1f}-{y1 / DPI:.1f} in")
    print(f"Saved {sys.argv[3]}")


if __name__ == "__main__":
    main()
