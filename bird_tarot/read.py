"""
Bird Tarot — Card Reader
Looks up or randomly draws tarot card meanings.

Usage:
    bird-tarot-read                          # draw a random card
    bird-tarot-read --id 00-the-fool         # look up a specific card
    bird-tarot-read --reversed               # force reversed meaning
    bird-tarot-read --suit cups              # draw randomly from one suit
    bird-tarot-read --list                   # print all card ids
"""

import argparse
import json
import random
from pathlib import Path

MEANINGS_FILE = Path(__file__).parent.parent / "meanings.json"

SUITS = ("wands", "cups", "swords", "pentacles")
MAJOR = "major"


def load_meanings(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def filter_ids(meanings: dict, suit: str | None) -> list[str]:
    if suit is None:
        return list(meanings.keys())
    if suit == MAJOR:
        return [k for k in meanings if k[0].isdigit()]
    return [k for k in meanings if k.endswith(f"-of-{suit}") or f"-of-{suit}" in k]


def display(card_id: str, card: dict, reversed: bool) -> None:
    orientation = "REVERSED" if reversed else "UPRIGHT"
    meaning = card["reversed"] if reversed else card["upright"]
    print(f"\n  {card['name']}  [{orientation}]")
    print(f"  id: {card_id}")
    print(f"\n  {meaning}\n")


def main():
    parser = argparse.ArgumentParser(description="Look up bird tarot card meanings.")
    parser.add_argument("--meanings", type=Path, default=MEANINGS_FILE, help="Path to meanings JSON file.")
    parser.add_argument("--id", metavar="ID", help="Card id to look up (e.g. 00-the-fool).")
    parser.add_argument("--reversed", action="store_true", help="Show reversed meaning. Omit for a random orientation.")
    parser.add_argument("--suit", choices=(*SUITS, MAJOR), help="Draw randomly from a suit or major arcana only.")
    parser.add_argument("--list", action="store_true", help="Print all card ids and exit.")
    args = parser.parse_args()

    meanings = load_meanings(args.meanings)

    if args.list:
        for card_id, card in meanings.items():
            print(f"  {card_id:30s}  {card['name']}")
        return

    if args.id:
        if args.id not in meanings:
            raise SystemExit(f"ERROR: '{args.id}' not found. Run --list to see valid ids.")
        card_id = args.id
    else:
        pool = filter_ids(meanings, args.suit)
        card_id = random.choice(pool)

    # If --reversed not explicitly passed, randomise orientation like a real shuffle
    is_reversed = args.reversed if args.reversed else random.choice([True, False])

    display(card_id, meanings[card_id], is_reversed)


if __name__ == "__main__":
    main()