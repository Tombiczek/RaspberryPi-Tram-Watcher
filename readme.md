# RaspberryPi Tram Watcher

**Tram watcher** to prosty projekt w Pythonie przeznaczony do uruchomienia na Raspberry Pi. Celem jest wyświetlanie nadchodzących odjazdów tramwajów ZTM Warszawa na ekranie e‑paper, aby zawsze wiedzieć o której godzinie należy wyjść z domu bez potrzeby sprawdzania swojego telefonu.


## Status projektu

- Projekt jest w fazie rozwoju.

- Na ten moment działa pobieranie danych o odjazdach z API ZTM oraz generowanie prostego podglądu w formie obrazu PNG.

## Wymagania

- Raspberry Pi Zero 2 W 512MB RAM - WiFi + BT 4.2
- E-paper E-Ink 7,5'' 800x480px - wyświetlacz z nakładką HAT dla Raspberry Pi

Zainstaluj zależności:

```bash
pip install -r requirements.txt
```

## TODO

- Dopracowanie finalnego wyświetlanego wyglądu
- Dodanie obliczonego czasu do wyjścia z domu na następny tramwaj
- Zapakowanie RasberryPi w przyjemną dla oka ramkę obrazową
- Napisanie kodu który faktycznie wyświetla obraz na ekranie e-ink
- Dopracowanie metody synchronizowania czasu
- Wymyślenie zmiennych interwałów czasowych odświeżania (zależnie od pory dnia)
