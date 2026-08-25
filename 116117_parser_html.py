#!/usr/bin/env python3

# ------------------------------------------------------------
# 116117 – NUR telefonische Erreichbarkeit aus gespeicherter HTML-Seite
#
# Liest eine gespeicherte HTML-Datei der 116117-Ergebnisliste und
# schreibt ausschliesslich die telefonischen Erreichbarkeiten
# (keine Sprechstunden) in eine CSV-Datei.
#
# Warum HTML statt Text-Kopie?
# Auf der Seite stehen Sprechstunde und telefonische Erreichbarkeit
# in getrennten Tabellenspalten nebeneinander. Beim Kopieren als
# reiner Text verschmelzen die Spalten. Im HTML bleibt die Spalte
# "Telefonische Erreichbarkeit" eindeutig erkennbar -> kein Raten.
#
# Benutzung:
#   1. Ergebnisseite im Browser mit Cmd+S als "Webseite, vollstaendig"
#      speichern, Dateiname: ergebnisse.html (gleicher Ordner).
#   2. Einmalig:  pip install beautifulsoup4   (oder pip3 ...)
#   3. Starten:   python3 116117_parser_html.py
# ------------------------------------------------------------

import re
import csv
from pathlib import Path
from datetime import date

try:
    from bs4 import BeautifulSoup
except ImportError:
    print()
    print("Die Bibliothek 'beautifulsoup4' fehlt.")
    print("Bitte einmal im Terminal ausfuehren:")
    print()
    print("    pip install beautifulsoup4")
    print("    (falls das nicht klappt: pip3 install beautifulsoup4)")
    print()
    raise SystemExit(1)


INPUT_FILE = "ergebnisse.html"
OUTPUT_FILE = "telefonische_erreichbarkeit.csv"

WEEKDAYS = [
    "Montag", "Dienstag", "Mittwoch", "Donnerstag",
    "Freitag", "Samstag", "Sonntag",
]


# ------------------------------------------------------------
# HILFSFUNKTIONEN
# ------------------------------------------------------------

def norm(text):
    # Mehrfache Leerzeichen / Umbrueche zu einem Leerzeichen
    return re.sub(r"\s+", " ", (text or "")).strip()


NAME_START = re.compile(r"^(Frau|Herr|Dr\.|Prof\.|Dipl)", re.IGNORECASE)
PHONE_RE = re.compile(r"^0[\d/ ]{5,}\d$")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PLZ_RE = re.compile(r"^\d{5}\s+\w")            # z.B. "13187 Berlin"
DATE_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")
TIME_RANGE_RE = re.compile(r"(\d{1,2}):(\d{2})\s*(?:bis|-)\s*(\d{1,2}):(\d{2})")


def is_name(text):
    return bool(NAME_START.match(text))


def weekday_from_date(dd, mm, yyyy):
    return WEEKDAYS[date(int(yyyy), int(mm), int(dd)).weekday()]


def detect_weekday(cell_text):
    t = norm(cell_text)
    for wd in WEEKDAYS:
        if wd in t:
            return wd
    if "Heute" in t:
        m = DATE_RE.search(t)
        if m:
            return weekday_from_date(m.group(1), m.group(2), m.group(3))
    return None


def extract_times(cell_text):
    # Die Seite listet jede Zeit doppelt ("08:00 bis 12:00" und
    # "08:00 - 12:00"). Wir sammeln jede Zeitspanne nur einmal.
    seen = []
    for m in TIME_RANGE_RE.finditer(cell_text or ""):
        start = f"{int(m.group(1)):02d}:{m.group(2)}"
        end = f"{int(m.group(3)):02d}:{m.group(4)}"
        value = f"{start}-{end}"
        if value not in seen:
            seen.append(value)
    return "; ".join(seen)


# ------------------------------------------------------------
# KONTAKTDATEN (Name, Adresse, Telefon, E-Mail) VOR DER TABELLE
# ------------------------------------------------------------

def extract_contact(table):
    # Textstuecke vor der Tabelle rueckwaerts einsammeln, bis der
    # Praxis-Name auftaucht (naechster "Frau/Herr/Dr. ..."-Eintrag).
    collected = []
    for s in table.find_all_previous(string=True):
        txt = norm(s)
        if not txt:
            continue
        collected.append(txt)
        if is_name(txt):
            break
        if len(collected) > 60:
            break
    collected.reverse()

    name = adresse = phone = email = ""
    plz_line = street = ""

    if collected and is_name(collected[0]):
        name = collected[0]

    for i, txt in enumerate(collected):
        if not phone and PHONE_RE.match(txt):
            phone = txt
        if not email:
            em = EMAIL_RE.search(txt)
            if em and not txt.lower().startswith("http"):
                email = em.group(0)
        if not plz_line and PLZ_RE.match(txt):
            plz_line = txt
            if i > 0 and "entfernt" not in collected[i - 1].lower():
                street = collected[i - 1]

    if street and plz_line:
        adresse = f"{street}, {plz_line}"
    elif plz_line:
        adresse = plz_line

    return name, adresse, phone, email


# ------------------------------------------------------------
# TABELLE AUSLESEN (nur die Telefon-Spalte)
# ------------------------------------------------------------

def is_schedule_table(table):
    head = norm(table.get_text(" "))
    return ("Telefonische Erreichbarkeit" in head) or ("Sprechstunde" in head)


def phone_column_index(header_cells):
    for idx, c in enumerate(header_cells):
        if "Telefonische Erreichbarkeit" in norm(c.get_text(" ")):
            return idx
    return None


def parse_table(table):
    rows = table.find_all("tr")
    if not rows:
        return None

    phone_idx = phone_column_index(rows[0].find_all(["th", "td"]))
    result = {wd: "" for wd in WEEKDAYS}

    if phone_idx is None:
        return result  # keine Telefon-Spalte -> alle Tage leer

    for row in rows[1:]:
        cells = row.find_all(["th", "td"])
        if not cells:
            continue
        weekday = detect_weekday(cells[0].get_text(" "))
        if not weekday or phone_idx >= len(cells):
            continue
        times = extract_times(cells[phone_idx].get_text(" "))
        if times:
            result[weekday] = times

    return result


# ------------------------------------------------------------
# HAUPTPROGRAMM
# ------------------------------------------------------------

def main():
    input_path = Path(INPUT_FILE)
    if not input_path.exists():
        print()
        print("FEHLER: Datei nicht gefunden:", INPUT_FILE)
        print("Bitte die Ergebnisseite mit Cmd+S als 'Webseite, vollstaendig'")
        print("speichern und als", INPUT_FILE, "im selben Ordner ablegen.")
        print()
        return

    html = input_path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")

    tables = [t for t in soup.find_all("table") if is_schedule_table(t)]
    print()
    print(f"Gefundene Tabellen: {len(tables)}")

    if not tables:
        print()
        print("Keine Tabellen gefunden. Vermutlich wurde die Seite ohne den")
        print("sichtbaren Inhalt gespeichert. Alternative:")
        print("  Rechtsklick auf die Seite -> 'Untersuchen' -> im Reiter")
        print("  'Elemente' Rechtsklick auf <html> -> Copy -> Copy outerHTML")
        print("  -> in einen Editor einfuegen -> als ergebnisse.html speichern.")
        print()
        return

    therapists = []
    for table in tables:
        name, adresse, phone, email = extract_contact(table)
        if not name:
            continue
        row = {"Name": name, "Adresse": adresse,
               "Telefon": phone, "E-Mail": email}
        row.update(parse_table(table))
        therapists.append(row)

    print(f"Erkannte Praxen: {len(therapists)}")
    if not therapists:
        print("Es wurden keine Praxen erkannt.")
        return

    columns = ["Name", "Adresse", "Telefon", "E-Mail"] + WEEKDAYS
    with Path(OUTPUT_FILE).open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns, delimiter=";")
        writer.writeheader()
        writer.writerows(therapists)

    print()
    print("Fertig. CSV erstellt:", Path(OUTPUT_FILE).resolve())
    print()


if __name__ == "__main__":
    main()
