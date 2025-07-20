import requests

API_KEY = "a9666478-a834-43b2-9999-7c5464a384fb"
BASE_URL = "https://api.um.warszawa.pl/api/action/dbtimetable_get"

params = {
    "id": "ab75c33d-3a26-4342-b36a-6e5fef0a3ac3",
    "apikey": API_KEY
}

response = requests.get(BASE_URL, params=params)
stops = response.json()["result"]

target_name = "Rondo Daszyńskiego"
for stop in stops:
    data = {item["key"]: item["value"] for item in stop["values"]}
    if target_name.lower() in data["nazwa_zespolu"].lower():
        print(f'{data["nazwa_zespolu"]} {data["slupek"]} → busstopId: {data["zespol"]}, busstopNr: {data["slupek"]}')
