"""
Bird Tarot — Local Generator (FLUX.1-schnell via HuggingFace)
Generates all 78 tarot cards locally using FLUX.1-schnell.

Model: black-forest-labs/FLUX.1-schnell (Apache 2.0, commercial use OK)
       Swap MODEL_ID to "black-forest-labs/FLUX.1-dev" for higher quality
       (non-commercial only; also requires guidance_scale=3.5, steps=20-50).

Requirements:
    pip install "bird-tarot[local]"
    # CUDA 12+ and ~24GB of system RAM also required for CPU offloading.

Usage:
    python generate_local.py                    # generate all cards
    python generate_local.py --cards custom.yml # alternate deck
    python generate_local.py --only 00-the-fool # single card by id
    python generate_local.py --out ./output_dir # custom output directory
    python generate_local.py --steps 4          # inference steps (default 4)

VRAM: peaks ~10-12GB at 1024x1024 with enable_model_cpu_offload + bfloat16.
Cards are saved as <id>.png. Already-generated cards are skipped (safe to re-run).
"""

import argparse
from pathlib import Path

import torch
import yaml
from diffusers import FluxPipeline
from PIL import Image

MODEL_ID = "black-forest-labs/FLUX.1-schnell"
MIN_FILE_BYTES = 10_000


def load_deck(cards_yml: Path) -> tuple[str, list[dict]]:
    raw = yaml.safe_load(cards_yml.read_text(encoding="utf-8"))
    return raw["style"].strip(), raw["cards"]


def already_done(path: Path) -> bool:
    return path.exists() and path.stat().st_size > MIN_FILE_BYTES


def load_pipeline() -> FluxPipeline:
    print(f"Loading {MODEL_ID} in bfloat16 + CPU offload...")
    pipe = FluxPipeline.from_pretrained(MODEL_ID, torch_dtype=torch.bfloat16)
    # Offloads full sub-models to CPU between uses — keeps peak VRAM ~10-12GB.
    # Replace with pipe.to("cuda") if you have >=24GB VRAM and want faster gen.
    pipe.enable_model_cpu_offload()
    # VAE tiling prevents VRAM spikes during decode at 1024x1024.
    pipe.vae.enable_tiling()
    print("Model ready.\n")
    return pipe


def generate_card(pipe: FluxPipeline, prompt: str, out_path: Path, steps: int) -> bool:
    try:
        image: Image.Image = pipe(
            prompt=prompt,
            guidance_scale=0.0,       # schnell is guidance-distilled; must be 0.0
            num_inference_steps=steps,
            max_sequence_length=512,
            height=1024,
            width=1024,
        ).images[0]
        image.save(out_path, format="PNG")
        return True
    except Exception as exc:
        print(f"    ERROR: {exc}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate bird tarot cards locally via FLUX.1-schnell.")
    parser.add_argument("--cards", type=Path, default=Path("cards.yml"), help="Path to cards YAML file.")
    parser.add_argument("--out", type=Path, default=Path("cards"), help="Output directory for PNGs.")
    parser.add_argument("--only", metavar="ID", help="Generate a single card by id and exit.")
    parser.add_argument("--steps", type=int, default=4, help="Inference steps. 4 is schnell's sweet spot; raise to 8 for marginally more detail.")
    args = parser.parse_args()

    args.out.mkdir(exist_ok=True)
    style, cards = load_deck(args.cards)

    if args.only:
        cards = [c for c in cards if c["id"] == args.only]
        if not cards:
            raise SystemExit(f"ERROR: No card with id '{args.only}' found in {args.cards}.")

    total = len(cards)
    print(f"Bird Tarot Local Generator — {total} card(s) → {args.out}/\n")

    pipe = load_pipeline()

    failed = []
    for i, card in enumerate(cards, start=1):
        card_id = card["id"]
        out_path = args.out / f"{card_id}.png"

        if already_done(out_path):
            print(f"  [{i}/{total}] SKIP  {card_id}")
            continue

        print(f"  [{i}/{total}] GEN   {card_id}")
        prompt = f"{style} {card['scene'].strip()}"
        if not generate_card(pipe, prompt, out_path, args.steps):
            failed.append(card_id)

    print(f"\nDone. {total - len(failed)}/{total} generated.")
    if failed:
        print("Failed (re-run to retry):")
        for name in failed:
            print(f"  {name}")


if __name__ == "__main__":
    main()