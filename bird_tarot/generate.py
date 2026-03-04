"""
Bird Tarot Card Generator
Generates all 78 tarot cards using DALL-E 3, themed around North American birds.

Requirements:
    pip install openai requests pyyaml

Usage:
    export OPENAI_API_KEY="sk-..."
    python generate.py                        # generate all cards
    python generate.py --cards custom.yml     # alternate deck
    python generate.py --only 00-the-fool     # single card by id
    python generate.py --out ./output_dir     # custom output directory
    python generate.py --workers 3            # parallel workers (default 5, tier-1 max)

Cards are saved as <id>.png. Already-generated cards are skipped (safe to re-run).
Cost estimate: ~$3 at standard DALL-E 3 pricing ($0.04/image).
"""

import argparse
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
import yaml
from openai import OpenAI

MIN_FILE_BYTES = 10_000
TIER1_MAX_WORKERS = 5   # DALL-E 3 tier-1 rate limit: 5 img/min

_print_lock = threading.Lock()


def log(msg: str) -> None:
    with _print_lock:
        print(msg)


def load_deck(cards_yml: Path) -> tuple[str, list[dict]]:
    raw = yaml.safe_load(cards_yml.read_text(encoding="utf-8"))
    return raw["style"].strip(), raw["cards"]


def already_done(path: Path) -> bool:
    return path.exists() and path.stat().st_size > MIN_FILE_BYTES


def generate_card(client: OpenAI, prompt: str, out_path: Path, label: str) -> bool:
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        image_bytes = requests.get(response.data[0].url, timeout=30).content
        out_path.write_bytes(image_bytes)
        log(f"  OK    {label}")
        return True
    except Exception as exc:
        log(f"  ERROR {label}: {exc}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate bird tarot cards via DALL-E 3.")
    parser.add_argument("--cards",   type=Path, default=Path("cards.yml"), help="Path to cards YAML file.")
    parser.add_argument("--out",     type=Path, default=Path("cards"),     help="Output directory for PNGs.")
    parser.add_argument("--only",    metavar="ID",                         help="Generate a single card by id and exit.")
    parser.add_argument("--workers", type=int, default=TIER1_MAX_WORKERS,  help="Parallel workers. Default 5 (tier-1 rate limit). Raise on higher API tiers.")
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("ERROR: OPENAI_API_KEY environment variable not set.")

    args.out.mkdir(exist_ok=True)
    style, cards = load_deck(args.cards)

    if args.only:
        cards = [c for c in cards if c["id"] == args.only]
        if not cards:
            raise SystemExit(f"ERROR: No card with id '{args.only}' found in {args.cards}.")

    # Split into skip/generate upfront so progress labelling is clean
    todo = []
    for card in cards:
        out_path = args.out / f"{card['id']}.png"
        if already_done(out_path):
            print(f"  SKIP  {card['id']}")
        else:
            todo.append(card)

    total = len(todo)
    if total == 0:
        print("All cards already generated.")
        return

    print(f"\nBird Tarot Generator — generating {total} card(s) with {args.workers} workers → {args.out}/\n")

    # One OpenAI client per thread — the client is not thread-safe to share.
    def worker(card: dict) -> tuple[str, bool]:
        client = OpenAI(api_key=api_key)
        prompt = f"{style} {card['scene'].strip()}"
        out_path = args.out / f"{card['id']}.png"
        log(f"  GEN   {card['id']}")
        success = generate_card(client, prompt, out_path, card["id"])
        return card["id"], success

    failed = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(worker, card): card["id"] for card in todo}
        for future in as_completed(futures):
            card_id, success = future.result()
            if not success:
                failed.append(card_id)

    print(f"\nDone. {total - len(failed)}/{total} generated.")
    if failed:
        print("Failed (re-run to retry):")
        for name in failed:
            print(f"  {name}")


if __name__ == "__main__":
    main()
    