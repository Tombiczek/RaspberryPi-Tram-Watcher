import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY", "")
RESOURCE_ID = "88cd555f-6f31-43ca-9de4-66c479ad5942"

# Podaj tutaj swój przystanek:
BUSSTOP_ID = "4911"
BUSSTOP_NR = "80"

BASE_URL = "https://api.um.warszawa.pl/api/action/dbtimetable_get"

params = {
    "id":        RESOURCE_ID,
    "busstopId": BUSSTOP_ID,
    "busstopNr": BUSSTOP_NR,
    "apikey":    API_KEY,
}

resp = requests.get(BASE_URL, params=params)
resp.raise_for_status()

stops = resp.json().get("result", [])

lines = set()
for stop in stops:
    data = { item["key"]: item["value"] for item in stop.get("values", []) }
    if "linia" in data:
        lines.add(data["linia"])

if lines:
    print(f"Na przystanku {BUSSTOP_ID}/{BUSSTOP_NR} kursują następujące linie:")
    for ln in sorted(lines):
        print(" -", ln)
else:
    print(f"Brak odjazdów dla przystanku {BUSSTOP_ID}/{BUSSTOP_NR}, sprawdź poprawność ID/NR lub klucza API.")
