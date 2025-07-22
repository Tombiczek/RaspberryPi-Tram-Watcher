from __future__ import annotations

import os
from datetime import datetime, time
from pathlib import Path
from typing import List, Tuple

import requests
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

API_URL: str = "https://api.um.warszawa.pl/api/action/dbtimetable_get"
FONT_PATH: str = "/System/Library/Fonts/SFNS.ttf"
OUTPUT_FILE: Path = Path("tram_board.png")
IMG_SIZE = (648, 480)
FONT_SIZE = 15

MODE: str = os.getenv("TRAM_MODE", "debug").lower()

STOP_CONFIGS: list[dict] = [
    {
        "label": "Rondo",      # etykieta na ekranie
        "id": "5040",         # id słupka ZTM
        "nr": "07",           # nr przystanku
        "lines": ["10", "11"],
        "horizon": 60,        # ile minut naprzód szukamy
        "walk": 5,           # czas dojścia na słupek (min)
        "hide_before": 3,     # kurs znika, gdy zostało ≤ N min
    },
]


load_dotenv()
API_KEY: str | None = os.getenv("API_KEY")
if not API_KEY:
    API_KEY = ""


def fetch(stop_id: str, stop_nr: str, line: str) -> List[Tuple[datetime, str, str]] | str:
    """Zwraca listę (datetime, line, kierunek) lub tekst błędu."""
    params = {
        "id": "e923fa0e-d96c-43f9-ae6e-60518c9f3238",
        "busstopId": stop_id,
        "busstopNr": stop_nr,
        "line": line,
        "apikey": API_KEY,
    }
    try:
        data = requests.get(API_URL, params=params, timeout=4).json().get("result", [])
    except Exception as exc:
        return f"Błąd sieci {line}@{stop_nr}: {exc}"
    if isinstance(data, str):
        return f"Błąd API {line}@{stop_nr}: {data}"

    today = datetime.now().date()
    deps: list[Tuple[datetime, str, str]] = []
    for entry in data:
        rec = {i["key"]: i["value"] for i in entry}
        if "czas" in rec and "kierunek" in rec:
            hh, mm, ss = map(int, rec["czas"].split(":"))
            deps.append((datetime.combine(today, time(hh, mm, ss)), line, rec["kierunek"]))
    return deps or f"Brak danych {line}@{stop_nr}"


def prepare(now: datetime):
    """Zwraca (rows, errors).
    *rows*   - (label, line, kierunek, min_odjazd, min_wyjście)
    *errors* - lista komunikatów tekstowych
    """
    rows: list[Tuple[str, str, str, int, int]] = []
    errors: list[str] = []

    for cfg in STOP_CONFIGS:
        label = cfg.get("label", cfg["nr"])
        for line in cfg["lines"]:
            result = fetch(cfg["id"], cfg["nr"], line)
            if isinstance(result, str):
                errors.append(result)
                continue
            for dep_dt, ln, direction in result:
                diff = int((dep_dt - now).total_seconds() // 60)
                if cfg["hide_before"] < diff <= cfg["horizon"]:
                    leave_in = diff - cfg["walk"]
                    rows.append((label, ln, direction, diff, leave_in))

    rows.sort(key=lambda r: r[3])  # wg min_odjazd
    return rows[:10], errors


def draw(rows, errors):
    img = Image.new("1", IMG_SIZE, 255)
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

    y = 10
    if errors and not rows:
        d.text((10, y), "Błędy:", font=font, fill=0)
        y += 30
        for msg in errors:
            d.text((10, y), f"• {msg}", font=font, fill=0)
            y += 25
    else:
        d.text((10, y), "Najbliższe tramwaje:", font=font, fill=0)
        y += 40
        for label, line, direction, mins, leave in rows:
            txt = f"{label} {line:<2} → {direction:<16} {mins:>2} min wyjście {leave:>2}"
            d.text((10, y), txt, font=font, fill=0)
            y += 25
        if errors:
            y += 20
            d.text((10, y), "Błędy (niektóre linie):", font=font, fill=0)
            y += 25
            for msg in errors:
                d.text((10, y), f"• {msg}", font=font, fill=0)
                y += 25
    return img


def render_to_screen(img):
    """Stub pod docelowe sterowanie wyświetlaczem e-ink."""
    # TODO: zaimplementuj integrację z Twoim modułem e-paper.
    pass


def output_image(img):
    if MODE == "debug":
        img.save(OUTPUT_FILE)
    else:
        render_to_screen(img)


def get_now() -> datetime:
    return datetime.now()


def main():
    now = get_now()
    rows, errors = prepare(now)
    img = draw(rows, errors)
    output_image(img)


if __name__ == "__main__":
    main()
