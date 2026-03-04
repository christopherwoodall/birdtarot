"""
Bird Tarot — Card Formatter
Converts square DALL-E output PNGs into properly proportioned tarot cards.

Layout:
  - 1024x1792 (1:1.75 — standard tarot ratio)
  - Parchment border top, sides, and within banner
  - Card image scaled to fill full width, centered vertically with parchment fill
  - Dark banner at bottom with gold card name

Usage:
    python format_cards.py                     # process all cards in ./cards/
    python format_cards.py --in ./cards        # explicit input dir
    python format_cards.py --out ./docs/cards  # explicit output dir
    python format_cards.py --only 03-the-empress
"""

import argparse
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_print_lock = threading.Lock()


def log(msg: str) -> None:
    with _print_lock:
        print(msg)


# ── Layout constants ───────────────────────────────────────────────────────────
CARD_W = 1024
CARD_H = 1792
BORDER = 26  # parchment border on all sides
BANNER_H = 112  # dark name banner at bottom (inside border)
GOLD_RULE = 3  # rule between image and banner
PARCHMENT = (245, 235, 208)
BANNER_BG = (22, 15, 8)
GOLD_BRIGHT = (218, 182, 88)
GOLD_DARK = (110, 85, 22)
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSerifCondensed-Bold.ttf"
FONT_SIZE = 50

MEANINGS_FILE = Path(__file__).parent / "meanings.json"
MIN_FILE_BYTES = 10_000


def load_names(meanings_path: Path) -> dict[str, str]:
    """Returns {card_id: display_name}."""
    if not meanings_path.exists():
        return {}
    data = json.loads(meanings_path.read_text(encoding="utf-8"))
    return {k: v["name"].upper() for k, v in data.items()}


def format_card(src: Path, dst: Path, name: str) -> None:
    img = Image.open(src).convert("RGB")

    card = Image.new("RGB", (CARD_W, CARD_H), PARCHMENT)
    draw = ImageDraw.Draw(card)

    # ── Image area dimensions ─────────────────────────────────────────────────
    img_x = BORDER
    img_y = BORDER
    img_area_w = CARD_W - BORDER * 2
    img_area_h = CARD_H - BORDER * 2 - BANNER_H - GOLD_RULE

    # Scale square image to fill width; center vertically within image area
    img_scaled = img.resize((img_area_w, img_area_w), Image.LANCZOS)

    if img_area_w <= img_area_h:
        # Image fits with parchment above/below — paste centered
        paste_y = img_y + (img_area_h - img_area_w) // 2
        card.paste(img_scaled, (img_x, paste_y))
    else:
        # Image taller than area (shouldn't happen at 1:1.75) — center-crop
        crop_top = (img_area_w - img_area_h) // 2
        img_cropped = img_scaled.crop((0, crop_top, img_area_w, crop_top + img_area_h))
        card.paste(img_cropped, (img_x, img_y))

    # ── Banner ────────────────────────────────────────────────────────────────
    banner_y = CARD_H - BORDER - BANNER_H
    draw.rectangle([BORDER, banner_y, CARD_W - BORDER, CARD_H - BORDER], fill=BANNER_BG)

    # Gold rule
    draw.rectangle(
        [BORDER, banner_y, CARD_W - BORDER, banner_y + GOLD_RULE], fill=GOLD_BRIGHT
    )

    # ── Outer border ──────────────────────────────────────────────────────────
    b = BORDER
    draw.rectangle(
        [b - 4, b - 4, CARD_W - b + 4, CARD_H - b + 4], outline=GOLD_BRIGHT, width=3
    )
    draw.rectangle(
        [b - 9, b - 9, CARD_W - b + 9, CARD_H - b + 9], outline=GOLD_BRIGHT, width=1
    )

    # ── Card name ─────────────────────────────────────────────────────────────
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    bbox = draw.textbbox((0, 0), name, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = (CARD_W - text_w) // 2
    text_y = banner_y + GOLD_RULE + (BANNER_H - GOLD_RULE - text_h) // 2 - bbox[1]

    draw.text((text_x + 2, text_y + 2), name, font=font, fill=GOLD_DARK)
    draw.text((text_x, text_y), name, font=font, fill=GOLD_BRIGHT)

    card.save(dst, format="PNG", optimize=True)


def main():
    parser = argparse.ArgumentParser(
        description="Format square card PNGs to tarot proportions."
    )
    parser.add_argument(
        "--in",
        dest="src_dir",
        type=Path,
        default=Path("cards"),
        help="Input directory of square PNGs.",
    )
    parser.add_argument(
        "--out",
        dest="dst_dir",
        type=Path,
        default=Path("docs/cards"),
        help="Output directory for formatted cards.",
    )
    parser.add_argument("--only", metavar="ID", help="Process a single card id.")
    parser.add_argument(
        "--meanings",
        type=Path,
        default=MEANINGS_FILE,
        help="meanings.json path for card names.",
    )
    args = parser.parse_args()

    args.dst_dir.mkdir(exist_ok=True)
    names = load_names(args.meanings)

    pngs = sorted(args.src_dir.glob("*.png"))
    if args.only:
        pngs = [p for p in pngs if p.stem == args.only]
        if not pngs:
            raise SystemExit(f"ERROR: '{args.only}.png' not found in {args.src_dir}.")

    workers = os.cpu_count() or 4

    todo = []
    for src in pngs:
        if src.stat().st_size < MIN_FILE_BYTES:
            log(f"  SKIP  {src.stem}  (file too small)")
        else:
            todo.append(src)

    total = len(todo)
    print(f"Formatting {total} card(s) with {workers} workers → {args.dst_dir}/\n")

    def worker(src: Path) -> str:
        dst = args.dst_dir / src.name
        display_name = names.get(src.stem, src.stem.replace("-", " ").upper())
        format_card(src, dst, display_name)
        log(f"  FMT   {src.stem}")
        return src.stem

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(worker, src) for src in todo]
        for future in as_completed(futures):
            future.result()  # re-raises any exception

    print(f"\nDone. {total} card(s) written to {args.dst_dir}/")


if __name__ == "__main__":
    main()
