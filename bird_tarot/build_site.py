"""
Bird Tarot — Static Site Generator

Reads card definitions (cards.yml) and meanings (meanings.json), scans for
formatted card images, and produces a single-page static site with all data
embedded as a JS constant.

Usage:
    bird-tarot-site
    bird-tarot-site --cards cards.yml --meanings meanings.json --images ./site/cards --out ./site
"""

import argparse
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

CARDS_YML = ROOT / "cards.yml"
MEANINGS_JSON = ROOT / "meanings.json"
IMAGES_DIR = ROOT / "site" / "cards"
OUT_DIR = ROOT / "site"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_card_ids(cards_yml: Path) -> list[str]:
    """Return ordered list of card ids from cards.yml."""
    data = yaml.safe_load(cards_yml.read_text(encoding="utf-8"))
    return [c["id"] for c in data["cards"]]


def load_meanings(meanings_json: Path) -> dict:
    """Return {id: {name, upright, ...}} from meanings.json."""
    if not meanings_json.exists():
        return {}
    return json.loads(meanings_json.read_text(encoding="utf-8"))


def available_images(images_dir: Path) -> set[str]:
    """Return set of card slugs that have a .png in images_dir."""
    if not images_dir.is_dir():
        return set()
    return {p.stem for p in images_dir.glob("*.png")}


def build_cards_json(card_ids: list[str], meanings: dict, images: set[str]) -> str:
    """Build the JS-embeddable JSON array of card objects."""
    cards = []
    for cid in card_ids:
        if cid not in images:
            continue
        m = meanings.get(cid, {})
        name = m.get("name", cid.replace("-", " ").title())
        meaning = m.get("upright", "")
        entry: dict = {"slug": cid, "name": name, "meaning": meaning}
        # keywords would go here if present in meanings.json
        kw = m.get("keywords")
        if kw:
            entry["keywords"] = kw
        cards.append(entry)
    return json.dumps(cards, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------


def html_template(cards_json: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bird Tarot</title>
<meta name="description" content="Draw a card. Listen to the bird.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=EB+Garamond:ital,wght@0,400;0,500;1,400&display=swap" rel="stylesheet">
<style>
/* ── Reset & base ──────────────────────────────────────────────────────── */
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html{{font-size:16px;-webkit-text-size-adjust:100%}}
body{{
  background:#0d0d0f;color:#e8e0d0;
  font-family:'EB Garamond',Georgia,serif;
  min-height:100vh;overflow-x:hidden;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
}}
button{{cursor:pointer;font-family:inherit;border:none;background:none}}
a{{color:inherit;text-decoration:none}}

/* ── Palette vars ──────────────────────────────────────────────────────── */
:root{{
  --bg:#0d0d0f;--surface:#16161a;--text:#e8e0d0;
  --gold:#c9a84c;--violet:#7c6fcd;--muted:#6b6478;
  --pill-bg:#1e1e26;--pill-text:#7c6fcd;
}}

/* ── Canvas (particle layer) ───────────────────────────────────────────── */
#particles{{position:fixed;inset:0;z-index:0;pointer-events:none}}

/* ── Layout shells ─────────────────────────────────────────────────────── */
.screen{{
  position:relative;z-index:1;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  min-height:100vh;width:100%;padding:2rem 1rem;
  transition:opacity .4s ease,transform .4s ease;
}}
.screen.hidden{{display:none}}
.screen.fade-out{{opacity:0;transform:translateY(-12px);pointer-events:none}}
.screen.fade-in{{opacity:1;transform:translateY(0)}}

/* ── State 1: Home ─────────────────────────────────────────────────────── */
#home{{text-align:center}}
.title{{
  font-family:'Cinzel',serif;font-size:clamp(2.6rem,8vw,4.8rem);
  color:var(--gold);letter-spacing:.06em;line-height:1.15;
  margin-bottom:.4rem;
}}
.title .char{{display:inline-block;opacity:0;transform:translateY(12px)}}
.title .char.visible{{opacity:1;transform:translateY(0);transition:opacity .32s ease,transform .32s ease}}
.subtitle{{
  font-family:'EB Garamond',serif;font-variant:small-caps;
  color:var(--muted);font-size:1.15rem;letter-spacing:.08em;
  opacity:0;transition:opacity .4s ease;margin-bottom:2.4rem;
}}
.subtitle.visible{{opacity:1}}
.btn-row{{display:flex;gap:1.2rem;opacity:0;transition:opacity .3s ease}}
.btn-row.visible{{opacity:1}}

.draw-btn{{
  font-family:'Cinzel',serif;font-size:1rem;letter-spacing:.12em;
  color:var(--gold);border:1.5px solid var(--gold);
  background:transparent;padding:.85rem 2.2rem;border-radius:4px;
  position:relative;overflow:hidden;transition:color .2s ease,background .2s ease;
  min-width:140px;min-height:44px;
}}
.draw-btn:hover,.draw-btn:focus-visible{{background:var(--gold);color:var(--bg)}}

/* shimmer pseudo */
.draw-btn::after{{
  content:'';position:absolute;inset:0;
  background:linear-gradient(105deg,transparent 40%,rgba(201,168,76,.25) 50%,transparent 60%);
  transform:translateX(-100%);pointer-events:none;
}}
@media(prefers-reduced-motion:no-preference){{
  .draw-btn:hover::after{{animation:shimmer .4s ease forwards}}
}}
@keyframes shimmer{{to{{transform:translateX(100%)}}}}

/* ── Cards ─────────────────────────────────────────────────────────────── */
.spread{{display:flex;gap:1.6rem;justify-content:center;align-items:flex-start;flex-wrap:wrap;margin-top:1.2rem}}
.card-slot{{
  perspective:900px;display:flex;flex-direction:column;align-items:center;
  opacity:0;transform:translateY(20px);
}}
.card-slot.dealt{{opacity:1;transform:translateY(0);transition:opacity .35s ease,transform .35s ease}}
.position-label{{
  font-family:'Cinzel',serif;font-variant:small-caps;
  color:var(--muted);font-size:.82rem;letter-spacing:.1em;
  margin-bottom:.5rem;min-height:1.2em;
}}

.card-inner{{
  width:220px;height:385px;position:relative;
  transform-style:preserve-3d;cursor:pointer;
  border-radius:8px;
  transition:transform .6s ease;
}}
.card-inner.flipped{{transform:rotateY(180deg)}}
.card-inner.lifting{{transform:translateY(-8px)}}
.card-inner.flipped.landed{{
  transform:rotateY(180deg) translateY(-4px);
}}

/* breathing idle */
@media(prefers-reduced-motion:no-preference){{
  .card-inner:not(.flipped):not(.lifting){{animation:breathe 3s ease-in-out infinite}}
}}
@keyframes breathe{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.015)}}}}

/* gold pulse on land */
@media(prefers-reduced-motion:no-preference){{
  .card-inner.pulse{{animation:goldpulse .6s ease-out forwards}}
}}
@keyframes goldpulse{{
  0%{{box-shadow:0 0 0 rgba(201,168,76,0)}}
  30%{{box-shadow:0 0 40px rgba(201,168,76,.4)}}
  100%{{box-shadow:0 0 12px rgba(201,168,76,.15)}}
}}

.card-face{{
  position:absolute;inset:0;border-radius:8px;
  backface-visibility:hidden;-webkit-backface-visibility:hidden;
  overflow:hidden;
}}

/* ── Card back (CSS/SVG feather pattern) ───────────────────────────────── */
.card-back{{
  background:var(--surface);
  border:1.5px solid var(--gold);
  display:flex;align-items:center;justify-content:center;
}}
.card-back svg{{width:100%;height:100%;opacity:.55}}

/* ── Card front ────────────────────────────────────────────────────────── */
.card-front{{
  transform:rotateY(180deg);
  background:var(--surface);
  border:1.5px solid var(--gold);
}}
.card-front img{{
  width:100%;height:100%;object-fit:cover;display:block;border-radius:7px;
}}

/* revealed card lift + glow */
.card-inner.flipped.landed .card-front{{
  box-shadow:0 0 32px rgba(124,111,205,.35);
}}

/* ── Card info (below card) ────────────────────────────────────────────── */
.card-info{{text-align:center;max-width:280px;margin-top:.8rem}}
.card-name{{
  font-family:'Cinzel',serif;font-size:1.15rem;color:var(--gold);
  opacity:0;transform:translateY(6px);
  transition:opacity .2s ease,transform .2s ease;
}}
.card-name.visible{{opacity:1;transform:translateY(0)}}
.card-meaning{{
  font-family:'EB Garamond',serif;font-size:.97rem;color:var(--text);
  line-height:1.55;margin-top:.4rem;
}}
.card-meaning .line{{
  display:block;opacity:0;transform:translateY(8px);
  transition:opacity .3s ease,transform .3s ease;
}}
.card-meaning .line.visible{{opacity:1;transform:translateY(0)}}

.card-keywords{{display:flex;flex-wrap:wrap;gap:.4rem;justify-content:center;margin-top:.5rem}}
.pill{{
  font-family:'EB Garamond',serif;font-size:.78rem;
  background:var(--pill-bg);color:var(--pill-text);
  padding:.18rem .65rem;border-radius:20px;
  opacity:0;transform:scale(.8);
  transition:opacity .2s ease,transform .3s cubic-bezier(.34,1.56,.64,1);
}}
.pill.visible{{opacity:1;transform:scale(1)}}

/* ── Start over link ───────────────────────────────────────────────────── */
.start-over{{
  font-family:'EB Garamond',serif;font-size:.95rem;
  color:var(--muted);margin-top:2rem;
  opacity:0;transition:opacity .5s ease,color .2s ease;
  cursor:pointer;min-height:44px;display:inline-flex;align-items:center;gap:.35rem;
}}
.start-over.visible{{opacity:1}}
.start-over:hover{{color:var(--gold)}}
.start-over .arrow{{display:inline-block;transition:transform .25s cubic-bezier(.34,1.56,.64,1)}}
.start-over:hover .arrow{{transform:rotate(-20deg)}}

/* ── Modal ─────────────────────────────────────────────────────────────── */
.modal-overlay{{
  position:fixed;inset:0;z-index:100;
  background:rgba(0,0,0,.82);
  display:flex;align-items:center;justify-content:center;
  opacity:0;pointer-events:none;
  transition:opacity .28s ease;
  padding:1rem;
}}
.modal-overlay.open{{opacity:1;pointer-events:auto}}
.modal-panel{{
  background:var(--surface);border:1.5px solid var(--gold);
  border-radius:10px;max-width:420px;width:100%;
  padding:1.6rem;text-align:center;
  transform:scale(.94) translateY(10px);
  transition:transform .28s ease-out,opacity .28s ease-out;
  opacity:0;
}}
.modal-overlay.open .modal-panel{{transform:scale(1) translateY(0);opacity:1}}
.modal-panel img{{width:100%;border-radius:6px;margin-bottom:1rem}}
.modal-position{{
  font-family:'Cinzel',serif;font-variant:small-caps;
  color:var(--muted);font-size:.82rem;letter-spacing:.1em;margin-bottom:.3rem;
}}
.modal-name{{
  font-family:'Cinzel',serif;font-size:1.3rem;color:var(--gold);margin-bottom:.6rem;
}}
.modal-meaning{{
  font-family:'EB Garamond',serif;font-size:1rem;color:var(--text);line-height:1.6;
}}
.modal-keywords{{display:flex;flex-wrap:wrap;gap:.4rem;justify-content:center;margin-top:.6rem}}

/* ── Mobile ────────────────────────────────────────────────────────────── */
@media(max-width:740px){{
  .spread{{flex-direction:column;align-items:center}}
  .card-inner{{width:200px;height:350px}}
  .modal-panel{{max-width:calc(100vw - 32px)}}
}}

/* ── Reduced motion ────────────────────────────────────────────────────── */
@media(prefers-reduced-motion:reduce){{
  *,*::before,*::after{{
    animation-duration:.01ms!important;animation-iteration-count:1!important;
    transition-duration:.01ms!important;
  }}
  .title .char{{opacity:1;transform:none}}
  .subtitle,.btn-row{{opacity:1}}
}}
</style>
</head>
<body>

<!-- Particle canvas -->
<canvas id="particles"></canvas>

<!-- ── State 1: Home ───────────────────────────────────────────────────── -->
<div id="home" class="screen">
  <h1 class="title" id="title"></h1>
  <p class="subtitle" id="subtitle">draw a card. listen to the bird.</p>
  <div class="btn-row" id="btnRow">
    <button class="draw-btn" id="drawOne">Draw One</button>
    <button class="draw-btn" id="drawThree">Draw Three</button>
  </div>
</div>

<!-- ── State 2: Reading ────────────────────────────────────────────────── -->
<div id="reading" class="screen hidden">
  <div class="spread" id="spread"></div>
  <div class="start-over" id="startOver"><span class="arrow">&#8617;</span> start over</div>
</div>

<!-- ── Modal (three-card detail) ───────────────────────────────────────── -->
<div class="modal-overlay" id="modal">
  <div class="modal-panel" id="modalPanel">
    <img id="modalImg" src="" alt="">
    <div class="modal-position" id="modalPosition"></div>
    <div class="modal-name" id="modalName"></div>
    <div class="modal-meaning" id="modalMeaning"></div>
    <div class="modal-keywords" id="modalKeywords"></div>
  </div>
</div>

<!-- Card back SVG pattern (hidden, cloned into cards) -->
<svg id="cardBackSvg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 385" style="display:none">
  <defs>
    <pattern id="featherPat" x="0" y="0" width="28" height="32" patternUnits="userSpaceOnUse" patternTransform="rotate(15)">
      <path d="M14 2 C14 2 8 10 8 18 C8 24 11 28 14 30 C17 28 20 24 20 18 C20 10 14 2 14 2Z"
            fill="none" stroke="#1e1e26" stroke-width="1" opacity=".6"/>
      <line x1="14" y1="6" x2="14" y2="28" stroke="#1e1e26" stroke-width=".5" opacity=".4"/>
      <line x1="10" y1="14" x2="14" y2="18" stroke="#1e1e26" stroke-width=".4" opacity=".3"/>
      <line x1="18" y1="14" x2="14" y2="18" stroke="#1e1e26" stroke-width=".4" opacity=".3"/>
      <line x1="10" y1="20" x2="14" y2="23" stroke="#1e1e26" stroke-width=".4" opacity=".3"/>
      <line x1="18" y1="20" x2="14" y2="23" stroke="#1e1e26" stroke-width=".4" opacity=".3"/>
    </pattern>
  </defs>
  <rect width="220" height="385" fill="#16161a"/>
  <rect width="220" height="385" fill="url(#featherPat)"/>
  <rect x="8" y="8" width="204" height="369" rx="4" fill="none" stroke="#c9a84c" stroke-width="1" opacity=".5"/>
  <rect x="12" y="12" width="196" height="361" rx="3" fill="none" stroke="#c9a84c" stroke-width=".5" opacity=".3"/>
  <!-- Central decorative diamond -->
  <g transform="translate(110,192)" opacity=".35">
    <polygon points="0,-30 18,0 0,30 -18,0" fill="none" stroke="#c9a84c" stroke-width="1"/>
    <polygon points="0,-18 10,0 0,18 -10,0" fill="none" stroke="#c9a84c" stroke-width=".7"/>
    <circle cx="0" cy="0" r="3" fill="#c9a84c" opacity=".5"/>
  </g>
</svg>

<script>
// ── Card data (embedded at build time) ────────────────────────────────────
const CARDS = {cards_json};

// ── State ─────────────────────────────────────────────────────────────────
let titleAnimated = false;
let modalOpen = false;

// ── DOM refs ──────────────────────────────────────────────────────────────
const $home = document.getElementById('home');
const $reading = document.getElementById('reading');
const $spread = document.getElementById('spread');
const $startOver = document.getElementById('startOver');
const $modal = document.getElementById('modal');
const $modalPanel = document.getElementById('modalPanel');
const $modalImg = document.getElementById('modalImg');
const $modalPosition = document.getElementById('modalPosition');
const $modalName = document.getElementById('modalName');
const $modalMeaning = document.getElementById('modalMeaning');
const $modalKeywords = document.getElementById('modalKeywords');

// ── Utility ───────────────────────────────────────────────────────────────
function shuffle(arr) {{
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {{
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }}
  return a;
}}

function sleep(ms) {{ return new Promise(r => setTimeout(r, ms)); }}

const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
function ms(val) {{ return prefersReducedMotion ? 0 : val; }}

// ── Card back SVG HTML ────────────────────────────────────────────────────
function cardBackHTML() {{
  const svg = document.getElementById('cardBackSvg');
  return svg.outerHTML.replace('style="display:none"', '').replace('id="cardBackSvg"', '');
}}
const CARD_BACK_SVG = cardBackHTML();

// ── Particle canvas ───────────────────────────────────────────────────────
(function initParticles() {{
  if (prefersReducedMotion) return;
  const canvas = document.getElementById('particles');
  const ctx = canvas.getContext('2d');
  let W, H;
  function resize() {{ W = canvas.width = window.innerWidth; H = canvas.height = window.innerHeight; }}
  resize();
  window.addEventListener('resize', resize);

  const glyphs = ['\\u2726','\\u22C6','\\u2727','\\u2022'];
  const count = 40 + Math.floor(Math.random() * 21); // 40-60
  const particles = [];
  for (let i = 0; i < count; i++) {{
    particles.push({{
      x: Math.random() * W,
      y: Math.random() * H,
      glyph: glyphs[Math.floor(Math.random() * glyphs.length)],
      speed: 0.15 + Math.random() * 0.35,
      sway: 20 + Math.random() * 40,
      swaySpeed: 0.0004 + Math.random() * 0.0008,
      phase: Math.random() * Math.PI * 2,
      maxOpacity: 0.06 + Math.random() * 0.12,
      opacitySpeed: 0.0003 + Math.random() * 0.0006,
      opacityPhase: Math.random() * Math.PI * 2,
      size: 8 + Math.random() * 6,
    }});
  }}

  let lastTime = performance.now();
  function animate(now) {{
    const dt = now - lastTime; lastTime = now;
    ctx.clearRect(0, 0, W, H);
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    for (const p of particles) {{
      p.y -= p.speed * (dt / 16);
      if (p.y < -20) {{ p.y = H + 20; p.x = Math.random() * W; }}
      const sx = Math.sin(now * p.swaySpeed + p.phase) * p.sway;
      const opacity = p.maxOpacity * (0.5 + 0.5 * Math.sin(now * p.opacitySpeed + p.opacityPhase));
      ctx.globalAlpha = Math.min(opacity, 0.18);
      ctx.font = p.size + 'px serif';
      ctx.fillStyle = '#e8e0d0';
      ctx.fillText(p.glyph, p.x + sx, p.y);
    }}
    ctx.globalAlpha = 1;
    requestAnimationFrame(animate);
  }}
  requestAnimationFrame(animate);
}})();

// ── Title entrance ────────────────────────────────────────────────────────
function animateTitle() {{
  if (titleAnimated) return;
  titleAnimated = true;
  const el = document.getElementById('title');
  const text = 'Bird Tarot';
  el.innerHTML = '';
  for (const ch of text) {{
    const span = document.createElement('span');
    span.className = 'char';
    span.textContent = ch === ' ' ? '\\u00A0' : ch;
    el.appendChild(span);
  }}
  const chars = el.querySelectorAll('.char');
  chars.forEach((c, i) => {{
    setTimeout(() => c.classList.add('visible'), ms(i * 40));
  }});
  const totalLetterTime = ms(text.length * 40);
  setTimeout(() => document.getElementById('subtitle').classList.add('visible'), totalLetterTime + ms(400));
  setTimeout(() => document.getElementById('btnRow').classList.add('visible'), totalLetterTime + ms(600));
}}

// ── State transitions ─────────────────────────────────────────────────────
function showHome() {{
  $reading.classList.add('fade-out');
  setTimeout(() => {{
    $reading.classList.add('hidden');
    $reading.classList.remove('fade-out');
    $spread.innerHTML = '';
    $startOver.classList.remove('visible');
    $home.classList.remove('hidden');
    // Don't re-animate title, just show it
    if (titleAnimated) {{
      document.getElementById('title').querySelectorAll('.char').forEach(c => c.classList.add('visible'));
      document.getElementById('subtitle').classList.add('visible');
      document.getElementById('btnRow').classList.add('visible');
    }}
    $home.classList.add('fade-in');
    setTimeout(() => $home.classList.remove('fade-in'), ms(300));
  }}, ms(400));
}}

function showReading() {{
  $home.classList.add('hidden');
  $reading.classList.remove('hidden');
  $reading.style.opacity = '1';
  $reading.style.transform = 'translateY(0)';
}}

// ── Card slot builder ─────────────────────────────────────────────────────
function createCardSlot(card, positionLabel) {{
  const slot = document.createElement('div');
  slot.className = 'card-slot';

  const label = document.createElement('div');
  label.className = 'position-label';
  label.textContent = positionLabel || '';
  slot.appendChild(label);

  const inner = document.createElement('div');
  inner.className = 'card-inner';
  inner.setAttribute('role', 'button');
  inner.setAttribute('tabindex', '0');
  inner.setAttribute('aria-label', 'Flip ' + (positionLabel || 'card'));

  const back = document.createElement('div');
  back.className = 'card-face card-back';
  back.innerHTML = CARD_BACK_SVG;
  inner.appendChild(back);

  const front = document.createElement('div');
  front.className = 'card-face card-front';
  const img = document.createElement('img');
  img.src = 'cards/' + card.slug + '.png';
  img.alt = card.name;
  img.loading = 'lazy';
  front.appendChild(img);
  inner.appendChild(front);

  slot.appendChild(inner);

  const info = document.createElement('div');
  info.className = 'card-info';
  slot.appendChild(info);

  slot._card = card;
  slot._inner = inner;
  slot._info = info;
  slot._positionLabel = positionLabel;
  return slot;
}}

// ── Flip a single card ────────────────────────────────────────────────────
async function flipCard(slot) {{
  const inner = slot._inner;
  if (inner.classList.contains('flipped')) return;

  // Lift
  inner.style.animation = 'none';
  inner.classList.add('lifting');
  await sleep(ms(150));

  // Flip
  inner.classList.remove('lifting');
  inner.classList.add('flipped');
  await sleep(ms(600));

  // Land
  inner.classList.add('landed');
  inner.classList.add('pulse');
  setTimeout(() => inner.classList.remove('pulse'), 600);
}}

// ── Reveal info for single draw ───────────────────────────────────────────
async function revealSingleInfo(slot) {{
  const card = slot._card;
  const info = slot._info;

  // Name
  const nameEl = document.createElement('div');
  nameEl.className = 'card-name';
  nameEl.textContent = card.name;
  info.appendChild(nameEl);
  await sleep(ms(50));
  nameEl.classList.add('visible');
  await sleep(ms(200));

  // Meaning lines
  if (card.meaning) {{
    const meaningEl = document.createElement('div');
    meaningEl.className = 'card-meaning';
    const lines = card.meaning.split(', ');
    lines.forEach(l => {{
      const span = document.createElement('span');
      span.className = 'line';
      span.textContent = l;
      meaningEl.appendChild(span);
    }});
    info.appendChild(meaningEl);
    await sleep(ms(100));
    const lineEls = meaningEl.querySelectorAll('.line');
    for (let i = 0; i < lineEls.length; i++) {{
      setTimeout(() => lineEls[i].classList.add('visible'), ms(i * 60));
    }}
    await sleep(ms(lineEls.length * 60 + 100));
  }}

  // Keywords
  if (card.keywords && card.keywords.length) {{
    const kwEl = document.createElement('div');
    kwEl.className = 'card-keywords';
    card.keywords.forEach(kw => {{
      const pill = document.createElement('span');
      pill.className = 'pill';
      pill.textContent = kw;
      kwEl.appendChild(pill);
    }});
    info.appendChild(kwEl);
    await sleep(ms(80));
    kwEl.querySelectorAll('.pill').forEach((p, i) => {{
      setTimeout(() => p.classList.add('visible'), ms(i * 80));
    }});
  }}
}}

// ── Draw One ──────────────────────────────────────────────────────────────
async function drawOne() {{
  showReading();
  const deck = shuffle(CARDS);
  const card = deck[0];
  const slot = createCardSlot(card, '');
  $spread.appendChild(slot);

  // Deal animation
  await sleep(ms(50));
  slot.classList.add('dealt');

  // Pause then flip
  await sleep(ms(300));
  await flipCard(slot);

  // Reveal info
  await revealSingleInfo(slot);

  // Start over
  await sleep(ms(800));
  $startOver.classList.add('visible');
}}

// ── Draw Three ────────────────────────────────────────────────────────────
async function drawThree() {{
  showReading();
  const deck = shuffle(CARDS);
  const positions = ['Past', 'Present', 'Future'];
  const slots = [];

  for (let i = 0; i < 3; i++) {{
    const slot = createCardSlot(deck[i], positions[i]);
    $spread.appendChild(slot);
    slots.push(slot);
  }}

  // Deal entrance stagger
  for (let i = 0; i < 3; i++) {{
    await sleep(ms(120));
    slots[i].classList.add('dealt');
  }}

  // Pause
  await sleep(ms(300));

  // Flip in sequence
  for (let i = 0; i < 3; i++) {{
    flipCard(slots[i]);
    await sleep(ms(150));
  }}
  // Wait for last flip to finish
  await sleep(ms(600));

  // Make cards clickable for modal (three-card only)
  slots.forEach(slot => {{
    const openModal = () => {{
      const c = slot._card;
      $modalImg.src = 'cards/' + c.slug + '.png';
      $modalImg.alt = c.name;
      $modalPosition.textContent = slot._positionLabel;
      $modalName.textContent = c.name;
      $modalMeaning.textContent = c.meaning || '';
      $modalKeywords.innerHTML = '';
      if (c.keywords && c.keywords.length) {{
        c.keywords.forEach(kw => {{
          const pill = document.createElement('span');
          pill.className = 'pill visible';
          pill.textContent = kw;
          $modalKeywords.appendChild(pill);
        }});
      }}
      $modal.classList.add('open');
      modalOpen = true;
    }};
    slot._inner.addEventListener('click', openModal);
    slot._inner.addEventListener('keydown', e => {{ if (e.key === 'Enter' || e.key === ' ') openModal(); }});
  }});

  // Start over
  await sleep(ms(800));
  $startOver.classList.add('visible');
}}

// ── Modal dismiss ─────────────────────────────────────────────────────────
function closeModal() {{
  $modal.classList.remove('open');
  modalOpen = false;
}}
$modal.addEventListener('click', e => {{ if (e.target === $modal) closeModal(); }});
document.addEventListener('keydown', e => {{ if (e.key === 'Escape' && modalOpen) closeModal(); }});

// ── Wire up buttons ───────────────────────────────────────────────────────
document.getElementById('drawOne').addEventListener('click', drawOne);
document.getElementById('drawThree').addEventListener('click', drawThree);
$startOver.addEventListener('click', () => {{ closeModal(); showHome(); }});

// ── Init ──────────────────────────────────────────────────────────────────
animateTitle();
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# CNAME / README
# ---------------------------------------------------------------------------

CNAME_CONTENT = "birdtarot.com\n"

README_CONTENT = """\
# Bird Tarot — Static Site

Published at [birdtarot.com](https://birdtarot.com).

## Pipeline

```
./cards/              Raw card artwork (square PNGs)
        │
        ▼
  format_cards.py     Resize to tarot proportions, add gold banner
        │
        ▼
./site/cards/         Formatted card PNGs (1024×1792)
        │
        ▼
  build_site.py       Merge cards.yml + meanings.json, embed in HTML
        │
        ▼
./site/index.html     Single-page static site (all data inline)
./site/CNAME          GitHub Pages custom domain
```

## Build

```bash
# Format raw card images (requires Pillow)
bird-tarot-format

# Generate the static site
bird-tarot-site
```

## CLI Options

```
bird-tarot-site --cards cards.yml --meanings meanings.json --images ./site/cards --out ./site
```

| Flag         | Default          | Description                     |
|-------------|------------------|---------------------------------|
| `--cards`   | `cards.yml`      | Card definitions (ids + scenes) |
| `--meanings`| `meanings.json`  | Display names and meanings      |
| `--images`  | `./site/cards`   | Formatted card PNGs directory   |
| `--out`     | `./site`         | Output directory for site files |

## What Gets Built

- `site/index.html` — self-contained SPA with all card data embedded as JS
- `site/cards/*.png` — formatted card images referenced by relative path
- `site/CNAME` — custom domain for GitHub Pages
- `site/README.md` — this file
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Build the Bird Tarot static site.")
    parser.add_argument(
        "--cards",
        type=Path,
        default=CARDS_YML,
        help="Path to cards.yml (default: %(default)s)",
    )
    parser.add_argument(
        "--meanings",
        type=Path,
        default=MEANINGS_JSON,
        help="Path to meanings.json (default: %(default)s)",
    )
    parser.add_argument(
        "--images",
        type=Path,
        default=IMAGES_DIR,
        help="Directory of formatted card PNGs (default: %(default)s)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=OUT_DIR,
        help="Output directory (default: %(default)s)",
    )
    args = parser.parse_args()

    # Load data
    print(f"Loading cards from {args.cards}")
    card_ids = load_card_ids(args.cards)

    print(f"Loading meanings from {args.meanings}")
    meanings = load_meanings(args.meanings)

    print(f"Scanning images in {args.images}")
    images = available_images(args.images)

    # Build merged dataset
    cards_json = build_cards_json(card_ids, meanings, images)
    included = cards_json.count('"slug"')
    print(f"  {included} cards with images (of {len(card_ids)} total)")

    # Write outputs
    args.out.mkdir(parents=True, exist_ok=True)

    index_path = args.out / "index.html"
    index_path.write_text(html_template(cards_json), encoding="utf-8")
    print(f"  Wrote {index_path}")

    cname_path = args.out / "CNAME"
    cname_path.write_text(CNAME_CONTENT, encoding="utf-8")
    print(f"  Wrote {cname_path}")

    readme_path = args.out / "README.md"
    readme_path.write_text(README_CONTENT, encoding="utf-8")
    print(f"  Wrote {readme_path}")

    print(f"\nDone. Site ready in {args.out}/")


if __name__ == "__main__":
    main()
