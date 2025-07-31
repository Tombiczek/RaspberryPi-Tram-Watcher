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
        "label": "Rondo Daszyńskiego",
        "id": "5040",
        "nr": "07",
        "lines": ["10", "11"],
        "horizon": 60,
        "walk": 5,
        "hide_before": 3,
    }
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
    # ------------------ DYNAMICZNE WYMIARY ------------------
    MARGIN_TOP = 10      # od góry przed pierwszym kafelkiem
    GAP        = 10      # odstęp pomiędzy kafelkami
    TOTAL_H    = IMG_SIZE[1]
    # wysokość boxa tak, by 4 kafelki + 3*GAP + 2*MARGIN_TOP == TOTAL_H
    usable_h   = TOTAL_H - 2 * MARGIN_TOP - 3 * GAP
    BOX_H      = int(usable_h / 4)
    BOX_W      = 700
    # skala wz. BOX_H bazowego 86px
    scale      = BOX_H / 86
    # zaokrąglenie, marginesy i rozmiary wewnętrzne
    RADIUS        = int(22 * scale)
    LEFT_W        = int(165 * scale)
    ICON_TEXT_GAP = int(8 * scale)
    # fonty i ikonka
    BIG_FS   = max(12, int(62 * scale))
    SMALL_FS = max(8, int(22 * scale))
    ICON_SIZE = max(16, int(30 * scale))
    # ---------------------------------------------------------

    img = Image.new("1", IMG_SIZE, 255)
    d   = ImageDraw.Draw(img)
    big_f   = ImageFont.truetype(FONT_PATH, BIG_FS)
    small_f = ImageFont.truetype(FONT_PATH, SMALL_FS)

    def _bbox_wh(text: str, font):
        x0, y0, x1, y1 = d.textbbox((0, 0), text, font=font)
        return x1 - x0, y1 - y0

    # ładowanie ikonki tramwaju
    try:
        tram_raw = Image.open("icons/tram.png").convert("1")
    except FileNotFoundError:
        tram_raw = Image.open("tram.svg").convert("1")
    tram_icon = tram_raw.resize((ICON_SIZE, ICON_SIZE), Image.Resampling.LANCZOS)

    if not rows:
        y = MARGIN_TOP
        d.text((20, y), "Brak danych", font=big_f, fill=0)
        for m in err:
            y += BIG_FS + 10
            d.text((20, y), m, font=small_f, fill=0)
        return img

    rows = rows[:4]
    x0 = (IMG_SIZE[0] - BOX_W) // 2
    x1 = x0 + BOX_W
    # Initialize y1 with a default value in case rows is empty
    y1 = MARGIN_TOP

    for idx, (label, line, dest, mins_dep, mins_leave) in enumerate(rows):
        y0 = MARGIN_TOP + idx * (BOX_H + GAP)
        y1 = y0 + BOX_H

        # ramka i separator
        d.rounded_rectangle([x0, y0, x1, y1], radius=RADIUS, outline=0, width=2)
        d.line([(x0 + LEFT_W, y0), (x0 + LEFT_W, y1)], fill=0, width=2)
        # LEWA: "X min" (wspólna linia, wspólna podstawa)
        num_txt = str(mins_leave)
        w_num, h_num = _bbox_wh(num_txt, big_f)
        w_min, h_min = _bbox_wh("min", small_f)
        total_w = w_num + 4 + w_min
        num_x = x0 + (LEFT_W - total_w) // 2
        # wspólna podstawa: y_center
        baseline_y = y0 + BOX_H // 2 + max(h_min, h_num)//4
        y_num = baseline_y - h_num
        y_min = baseline_y - h_min + 10
        # odwrócone tło + kolor tekstu
        if mins_leave < 0:
            d.rectangle([x0 + RADIUS, y0, x0 + LEFT_W, y1], fill=0)
            d.rounded_rectangle([x0, y0, x0 + LEFT_W, y1], radius=RADIUS, fill=0)
            fill_col = 1
        else:
            fill_col = 0
        d.text((num_x, y_num), num_txt, font=big_f, fill=fill_col)
        d.text((num_x + w_num + 4, y_min), "min", font=small_f, fill=fill_col)

        # PRAWA: line+ikonka+→+dest wyśrodkowane wertykalnie
        cur_x = x0 + LEFT_W + int(15 * scale)
        mid_y = y0 + ((BOX_H - ICON_SIZE) // 2) - 5
        d.text((cur_x, mid_y + (ICON_SIZE - SMALL_FS)//2), line, font=small_f, fill=0)
        cur_x += _bbox_wh(line, small_f)[0] + ICON_TEXT_GAP
        img.paste(tram_icon, (int(cur_x), int(mid_y)))
        cur_x += ICON_SIZE + ICON_TEXT_GAP
        d.text((cur_x, mid_y + (ICON_SIZE - SMALL_FS)//2), "→", font=small_f, fill=0)
        cur_x += _bbox_wh("→", small_f)[0] + ICON_TEXT_GAP
        max_dest_w = x1 - 15 - cur_x
        dest_txt = dest if _bbox_wh(dest, small_f)[0] <= max_dest_w else dest[:max_dest_w // (SMALL_FS // 2)] + "…"
        d.text((cur_x, mid_y + (ICON_SIZE - SMALL_FS)//2), dest_txt, font=small_f, fill=0)

        # DOLNE ELEMENTY: label i minutes_to_departure (podniesione wyżej)
        dep_txt = f"{mins_dep} min"
        w_dep, h_dep = _bbox_wh(dep_txt, small_f)
        # zwiększony margines od dolnej krawędzi
        bottom_y = y1 - h_dep - int(13 * scale)
        # rysujemy label i czas do odjazdu
        d.text((x0 + LEFT_W + int(15 * scale), bottom_y), label, font=small_f, fill=0)
        d.text((x1 - w_dep - int(15 * scale), bottom_y), dep_txt, font=small_f, fill=0)

    # błędy poniżej
    if err:
        y_err = y1 + GAP + 10
        d.text((x0, y_err), "Błędy:", font=small_f, fill=0)
        for m in err:
            y_err += SMALL_FS + 4
            d.text((x0, y_err), m, font=small_f, fill=0)

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
