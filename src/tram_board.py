"""simple_tram_board.py
=======================
E-ink board z odjazdami tramwajów. Dane z API pobierane raz na dobę i cacheowane
w .kcache/.  Tryb wybiera zmienna TRAM_MODE (debug → PNG, production → render).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, time
from pathlib import Path
from typing import List, Tuple

import requests
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

API_URL = "https://api.um.warszawa.pl/api/action/dbtimetable_get"
FONT_PATH = "/System/Library/Fonts/SFNS.ttf"
IMG_SIZE = (800, 480)
FONT_SIZE = 20
CACHE_DIR = Path(".kcache")
CACHE_DIR.mkdir(exist_ok=True)

MODE = os.getenv("TRAM_MODE", "debug").lower()

STOP_CONFIGS = [
    {
        "label": "Rondo",
        "id": "5040",
        "nr": "07",
        "lines": ["10", "11"],
        "horizon": 60,
        "walk": 5,
        "hide_before": 3,
    },
]

load_dotenv()
API_KEY = os.getenv("API_KEY", "")

def _cache_path(sid: str, snr: str, line: str, date: str) -> Path:
    return CACHE_DIR / f"{sid}_{snr}_{line}_{date}.json"


def fetch(sid: str, snr: str, line: str) -> List[Tuple[datetime, str, str]] | str:
    today = datetime.now().date()
    cfile = _cache_path(sid, snr, line, str(today))
    if cfile.exists():
        data = json.loads(cfile.read_text())
    else:
        params = {
            "id": "e923fa0e-d96c-43f9-ae6e-60518c9f3238",
            "busstopId": sid,
            "busstopNr": snr,
            "line": line,
            "apikey": API_KEY,
        }
        try:
            data = requests.get(API_URL, params=params, timeout=4).json().get("result", [])
        except Exception as exc:
            return f"Błąd sieci {line}@{snr}: {exc}"
        if isinstance(data, str):
            return f"Błąd API {line}@{snr}: {data}"
        cfile.write_text(json.dumps(data))

    deps: list[Tuple[datetime, str, str]] = []
    for entry in data:
        rec = {i["key"]: i["value"] for i in entry}
        if "czas" in rec and "kierunek" in rec:
            hh, mm, ss = map(int, rec["czas"].split(":"))
            deps.append((datetime.combine(today, time(hh, mm, ss)), line, rec["kierunek"]))
    return deps or f"Brak danych {line}@{snr}"


def prepare(now: datetime):
    rows: list[Tuple[str, str, str, int, int]] = []
    errors: list[str] = []
    for cfg in STOP_CONFIGS:
        for line in cfg["lines"]:
            r = fetch(cfg["id"], cfg["nr"], line)
            if isinstance(r, str):
                errors.append(r)
                continue
            for dt, ln, dest in r:
                diff = int((dt - now).total_seconds() // 60)
                if cfg["hide_before"] < diff <= cfg["horizon"]:
                    rows.append((cfg.get("label", cfg["nr"]), ln, dest, diff, diff - cfg["walk"]))
    rows.sort(key=lambda r: r[3])
    return rows[:10], errors


def draw(rows, err):
    img = Image.new("1", IMG_SIZE, 255)
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    y = 10
    if err and not rows:
        d.text((10, y), "Błędy:", font=f, fill=0)
        for m in err:
            y += 25
            d.text((10, y), m, font=f, fill=0)
    else:
        d.text((10, y), "Najbliższe tramwaje:", font=f, fill=0)
        for lab, ln, dest, mn, lv in rows:
            y += 25
            d.text((10, y), f"{lab} {ln:<2} → {dest:<16} {mn:>2}m wyjście {lv:>2}", font=f, fill=0)
        for m in err:
            y += 25
            d.text((10, y), m, font=f, fill=0)
    return img


def render_to_screen(img):
    pass  # TODO


def output_image(img):
    (img.save(Path("tram_board.png")) if MODE == "debug" else render_to_screen(img))


def main():
    now = datetime.now()
    rows, err = prepare(now)
    output_image(draw(rows, err))


if __name__ == "__main__":
    main()
