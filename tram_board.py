"""tram_board.py
================
Wyświetla najbliższe odjazdy tramwajów dla wybranych linii na ekranie e-paper
(lub w pliku PNG). Kod jest maksymalnie skrócony i udokumentowany, żeby po
kilku miesiącach można było z marszu zrozumieć, co się dzieje.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path
from typing import Iterable, List, Tuple

import requests
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
load_dotenv()
API_KEY: str | None = os.getenv("API_KEY")
if not API_KEY:
    raise RuntimeError("Brak klucza API")
timeout = 4  # s – domyślny timeout dla requestów HTTP
API_ENDPOINT = "https://api.um.warszawa.pl/api/action/dbtimetable_get"
TIME_API = "http://worldtimeapi.org/api/timezone/Europe/Warsaw"
FONT_PATH = "/System/Library/Fonts/SFNS.ttf"
OUTPUT_FILE = Path("tramwaje_output.png")
WATCHED_LINES = ("10", "11")


# ---------------------------------------------------------------------------
# Konfiguracja logowania
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


@dataclass(frozen=True)
class Stop:
    """Reprezentuje przystanek ZTM."""

    id: str
    number: str


STOP = Stop(id="5040", number="07")


# ---------------------------------------------------------------------------
# Funkcje pomocnicze

def now(tz_source: str = TIME_API) -> datetime:
    """Zwraca aktualny czas w strefie *Europe/Warsaw*.

    Gdy zewnętrzne API jest niedostępne, korzysta z zegara systemowego.
    """
    try:
        resp = requests.get(tz_source, timeout=2)
        resp.raise_for_status()
        return datetime.fromisoformat(resp.json()["datetime"])
    except Exception as exc:  # pragma: no cover – odpuszczamy testowanie sieci
        logging.warning("WorldTime API unavailable (%s). Falling back to local clock.", exc)
        return datetime.now()


def departures_for(
    line: str,
    *,
    stop: Stop = STOP,
    api_key: str = API_KEY,
) -> list[tuple[str, str, str]]:
    """Pobiera surowe odjazdy linii *line* na przystanku *stop*.

    Każdy rekord to ("HH:MM:SS", kierunek, linia).
    """
    params = {
        "id": "e923fa0e-d96c-43f9-ae6e-60518c9f3238",
        "busstopId": stop.id,
        "busstopNr": stop.number,
        "line": line,
        "apikey": api_key,
    }
    result = requests.get(API_ENDPOINT, params=params, timeout=timeout).json().get("result", [])
    if isinstance(result, str):
        logging.error("API error for line %s: %s", line, result)
        return []

    parsed: list[tuple[str, str, str]] = []
    for entry in result:
        record = {itm["key"]: itm["value"] for itm in entry}
        if record.get("czas") and record.get("kierunek"):
            parsed.append((record["czas"], record["kierunek"], line))
    return parsed


def next_departures(
    raw: Iterable[tuple[str, str, str]],
    *,
    current: datetime,
    limit: int = 10,
) -> list[tuple[datetime, str, str, int]]:
    """Filtruje i porządkuje listę odjazdów.

    Zwraca maksymalnie *limit* pozycji (departure_dt, linia, kierunek, minuty).
    """
    today = current.date()
    upcoming: list[tuple[datetime, str, str, int]] = []
    for tstr, direction, line in raw:
        hh, mm, ss = map(int, tstr.split(":"))
        dep = datetime.combine(today, time(hh, mm, ss))
        if dep >= current:
            minutes = round((dep - current).total_seconds() / 60)
            upcoming.append((dep, line, direction, minutes))

    return sorted(upcoming, key=lambda x: x[0])[:limit]


def render(
    board: list[tuple[datetime, str, str, int]],
    *,
    font_path: str = FONT_PATH,
    outfile: Path = OUTPUT_FILE,
) -> None:
    """Rysuje tablicę *board* do pliku PNG przyjaznego e-papierowi."""
    W, H = 648, 480
    img = Image.new("1", (W, H), 255)  # 1‑bit, białe tło
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, 15)

    draw.text((10, 10), "Następne kursy:", font=font, fill=0)

    y = 50
    for _, line, direction, minutes in board:
        draw.text((10, y), f"Linia {line:<3} → {direction} za {minutes:>2} min", font=font, fill=0)
        y += 32

    img.save(outfile)
    logging.info("Saved preview to %s", outfile)


# ---------------------------------------------------------------------------
# Główna pętla

def main() -> None:
    clock = now()
    logging.info("Synchronized time: %s", clock.strftime("%Y-%m-%d %H:%M:%S"))

    raw: List[Tuple[str, str, str]] = []
    for line in WATCHED_LINES:
        raw.extend(departures_for(line))

    board = next_departures(raw, current=clock, limit=10)

    if board:
        render(board)
    else:
        logging.warning("No remaining departures for today (%s).", ", ".join(WATCHED_LINES))


if __name__ == "__main__":
    main()
