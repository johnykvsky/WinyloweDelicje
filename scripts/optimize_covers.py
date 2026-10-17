#!/usr/bin/env python3
"""
Resize and optimize album cover thumbnails in assets/covers/.
- Preserves original aspect ratio.
- Ensures the shorter side is at least TARGET_MIN_SIDE (200px) when downscaling,
  so thumbnails (displayed at 82x82px CSS / ~164x164px on 2x HiDPI) stay crisp.
- Converts any PNG/RGBA/CMYK files into proper optimized RGB JPEGs.
"""

import os
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COVERS_DIR = os.path.join(BASE_DIR, "assets", "covers")

TARGET_MIN_SIDE = 200
JPEG_QUALITY = 85


def optimize_cover(filepath: str) -> tuple[int, int, tuple[int, int], tuple[int, int]]:
    old_size = os.path.getsize(filepath)
    with Image.open(filepath) as img:
        orig_dims = img.size
        w, h = orig_dims

        # Handle transparency / palette modes before converting to RGB
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            rgba = img.convert("RGBA")
            bg = Image.new("RGB", rgba.size, (25, 28, 36))
            bg.paste(rgba, mask=rgba.split()[3])
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Keep aspect ratio; scale down only if shorter side > TARGET_MIN_SIDE
        short_side = min(w, h)
        if short_side > TARGET_MIN_SIDE:
            scale = TARGET_MIN_SIDE / float(short_side)
            new_w = max(TARGET_MIN_SIDE, int(round(w * scale)))
            new_h = max(TARGET_MIN_SIDE, int(round(h * scale)))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        new_dims = img.size
        tmp_path = filepath + ".tmp.jpg"
        img.save(tmp_path, format="JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)

    os.replace(tmp_path, filepath)
    new_size = os.path.getsize(filepath)
    return old_size, new_size, orig_dims, new_dims


def main():
    files = sorted(
        f for f in os.listdir(COVERS_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    )
    if not files:
        print("No cover files found in", COVERS_DIR)
        return

    total_old = 0
    total_new = 0
    resized_count = 0

    for fname in files:
        fpath = os.path.join(COVERS_DIR, fname)
        old_sz, new_sz, old_dims, new_dims = optimize_cover(fpath)
        total_old += old_sz
        total_new += new_sz
        if old_dims != new_dims:
            resized_count += 1

    print(f"Processed {len(files)} covers ({resized_count} resized to min-side {TARGET_MIN_SIDE}px).")
    print(f"Total size before: {total_old / (1024 * 1024):.2f} MB")
    print(f"Total size after:  {total_new / (1024 * 1024):.2f} MB (saved {(1 - total_new / total_old) * 100:.1f}%)")


if __name__ == "__main__":
    main()
