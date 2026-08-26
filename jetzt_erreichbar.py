#!/usr/bin/env python3

# ------------------------------------------------------------
# 116117 – "Wer ist JETZT erreichbar?" auf Basis einer bereits
# erzeugten ergebnisse.csv (ohne die HTML-Datei neu auszulesen).
#
# Nimmt ergebnisse.csv, prueft fuer den HEUTIGEN Tag, bei welcher
# Praxis man in genau diesem Moment anrufen kann, sortiert diese
# nach oben und schreibt das Ganze in eine NEUE Datei mit Datum
# und Uhrzeit im Namen, z.B.:  ergebnisse_2026-08-26_10-18.csv
#
# Die urspruengliche ergebnisse.csv bleibt unveraendert.
#
# Benutzung:  python3 jetzt_erreichbar.py
# ------------------------------------------------------------

import re
import csv
from pathlib import Path
from datetime import datetime

INPUT_FILE = "ergebnisse.csv"

WINDOW_RE = re.compile(r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})")


def is_open_now(window_str, now_minutes):
    # Prueft, ob 'now_minutes' (Minuten seit Mitternacht) in einem
    # der Zeitfenster "07:30-08:00; 12:30-12:55" liegt.
    for m in WINDOW_RE.finditer(window_str or ""):
        start = int(m.group(1)) * 60 + int(m.group(2))
        end = int(m.group(3)) * 60 + int(m.group(4))
        if start <= now_minutes < end:
            return True
    return False


def main():
    input_path = Path(INPUT_FILE)
    if not input_path.exists():
        print()
        print("FEHLER: Datei nicht gefunden:", INPUT_FILE)
        print("Bitte zuerst mit dem HTML-Skript eine ergebnisse.csv erzeugen.")
        print()
        return

    now = datetime.now()
    today_str = now.strftime("%d.%m.%Y")          # passt zu den Datumsspalten
    now_minutes = now.hour * 60 + now.minute

    with input_path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    if not rows:
        print("Die CSV enthaelt keine Datenzeilen.")
        return

    # Sicherstellen, dass die beiden Spalten existieren (nach E-Mail einfuegen)
    def ensure_column(name):
        if name not in fieldnames:
            if "E-Mail" in fieldnames:
                fieldnames.insert(fieldnames.index("E-Mail") + 1, name)
            else:
                fieldnames.insert(0, name)

    ensure_column("Jetzt erreichbar")
    ensure_column("Heute")

    # Gibt es ueberhaupt eine Spalte fuer den heutigen Tag?
    has_today = today_str in fieldnames
    if not has_today:
        print()
        print(f"Hinweis: Fuer heute ({today_str}) gibt es keine Spalte in der CSV.")
        print("Die Daten stammen vermutlich von anderen Tagen. Dann kann keine")
        print("aktuelle Erreichbarkeit berechnet werden – bitte die 116117-Seite")
        print("neu speichern und die ergebnisse.csv neu erzeugen.")
        print()

    for row in rows:
        heute_zeiten = row.get(today_str, "") if has_today else ""
        row["Heute"] = heute_zeiten
        if heute_zeiten:
            row["Jetzt erreichbar"] = "JA" if is_open_now(heute_zeiten, now_minutes) else "NEIN"
        else:
            row["Jetzt erreichbar"] = ""

    # Sortierung: jetzt erreichbar zuerst, dann nach Name
    def sort_key(row):
        j = row.get("Jetzt erreichbar", "")
        rank = 0 if j == "JA" else (1 if j == "NEIN" else 2)
        return (rank, (row.get("Name", "") or "").lower())

    rows.sort(key=sort_key)

    erreichbar_jetzt = sum(1 for r in rows if r.get("Jetzt erreichbar") == "JA")

    # Neuer Dateiname mit ISO-Datum und Uhrzeit
    stamp = now.strftime("%Y-%m-%d_%H-%M")
    output_path = input_path.with_name(f"ergebnisse_{stamp}.csv")

    with output_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames,
                                delimiter=";", restval="")
        writer.writeheader()
        writer.writerows(rows)

    print()
    print(f"Zeitpunkt: {now.strftime('%d.%m.%Y %H:%M')}")
    print(f"Jetzt erreichbar: {erreichbar_jetzt} von {len(rows)} Praxen")
    print("Neue Datei:", output_path.resolve())
    print("(ergebnisse.csv bleibt unveraendert.)")
    print()


if __name__ == "__main__":
    main()
