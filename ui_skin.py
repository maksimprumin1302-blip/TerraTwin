# AI DISCLOSURE: OpenAI ChatGPT assisted parts of TerraTwin code drafting/debugging.
# See AI_USAGE.md and ai_provenance.json; external scientific data are not AI-generated.
"""Theme palette and lightweight static styling for TerraTwin. No DOM scripting."""
from __future__ import annotations
import base64
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent

PAL = {
    "dark": {
        "BG": "#080f1d", "PANEL": "#111e30", "ALT": "#192a40",
        "INK": "#f3f7ff", "MUTED": "#aabbd0", "BORDER": "#2c3d53",
        "BLUE": "#7fcbff", "SOFTRED": "#3a1e2b",
    },
    "light": {
        "BG": "#f5f7fb", "PANEL": "#ffffff", "ALT": "#edf2f7",
        "INK": "#111e31", "MUTED": "#58697d", "BORDER": "#dbe3eb",
        "BLUE": "#1768ae", "SOFTRED": "#fff0f1",
    },
}


def theme_css(mode: str) -> str:
    if mode not in PAL:
        raise ValueError(f"Unknown theme: {mode}")
    css = (ROOT / "assets" / "interface.css").read_text(encoding="utf-8")
    hero = base64.b64encode((ROOT / "assets" / "orbital_hero.svg").read_bytes()).decode("ascii")
    for k, v in PAL[mode].items():
        css = css.replace(f"__{k}__", v)
    polish=(ROOT / "assets" / "public_polish.css").read_text(encoding="utf-8")
    return css.replace("__HERO__", f"data:image/svg+xml;base64,{hero}") + "\n" + polish


def brand() -> str:
    return '''<div class="tt-brand" translate="no">
      <div class="tt-brand-left"><div class="tt-symbol">✦</div>
        <div><div class="tt-brand-name">TERRA<span>TWIN</span></div>
        <div class="tt-brand-sub">EARTH ANALOG EXPLORER</div></div></div>
      <div class="tt-brand-side">SPACE APPS 2026&nbsp; · &nbsp;INDEPENDENT PROJECT</div>
    </div>'''


def hero(lang: str="uk") -> str:
    if lang=="en":
        return '''<div class="tt-hero" translate="no">
      <div class="tt-overline">EARTH DATA · MOON & MARS RESEARCH</div>
      <h1>Explore Earth.<br><em>Prepare for space.</em></h1>
      <p>Scientific analogs and mission-testing scenarios, with mapped evidence, clear limitations and open research data.</p>
    </div>'''
    return '''<div class="tt-hero" translate="no">
      <div class="tt-overline">EARTH DATA · MOON & MARS RESEARCH</div>
      <h1>Знайди Землю<br>на <em>інших планетах.</em></h1>
      <p>Два режими: аналіз геологічної подібності та підготовка випробувань для майбутніх космічних баз. Реальні дані, прозорі висновки.</p>
    </div>'''


def heading(number: str, title: str, explanation: str) -> str:
    return (f'<div class="tt-section"><b>{escape(number)}</b>'
            f'<h2>{escape(title)}</h2><p>{escape(explanation)}</p></div>')


def mini_card(number: str, label: str) -> str:
    return (f'<div class="tt-mini"><div class="value">{escape(number)}</div>'
            f'<div class="label">{escape(label.upper())}</div></div>')


def location_card(site: dict) -> str:
    return (f'<div class="tt-loc-head"><small>{escape(site["planet"])} · {escape(site["country"])}</small>'
            f'<h3>{escape(site["name"])}</h3><p>{escape(site["terrain"])}</p></div>')
