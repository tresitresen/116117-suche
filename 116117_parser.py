#!/usr/bin/env python3

import re
import csv
import sys
from pathlib import Path


# ============================================================
# EINSTELLUNGEN
# ============================================================

INPUT_FILE = "ergebnisse.txt"
OUTPUT_FILE = "ergebnisse.csv"

WEEKDAYS = [
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag",
]

WEEKDAY_PATTERN = (
    r"(Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag)"
    r"(?:\s+(?:Mo|Di|Mi|Do|Fr|Sa|So))?"
)

DATE_PATTERN = r"\d{2}\.\d{2}\.\d{4}"

TIME_PATTERN = re.compile(
    r"(?P<start>\d{1,2}:\d{2})"
    r"\s*(?:bis|-)\s*"
    r"(?P<end>\d{1,2}:\d{2})"
)


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def normalize_text(text):
    """Bereinigt typische Copy/Paste-Artefakte."""

    text = text.replace("\u00a0", " ")
    text = text.replace("\u200b", "")
    text = text.replace("\r", " ")

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def unique_preserve_order(items):
    """Entfernt Duplikate und behält die ursprüngliche Reihenfolge."""

    result = []

    for item in items:
        if item not in result:
            result.append(item)

    return result


def extract_time_ranges(text):
    """
    Extrahiert Zeitintervalle und entfernt doppelte Angaben.

    Beispiel:

    10:00 bis 16:00 10:00 - 16:00

    wird zu:

    10:00-16:00
    """

    ranges = []

    for match in TIME_PATTERN.finditer(text):

        start = match.group("start")
        end = match.group("end")

        if len(start) == 4:
            start = "0" + start

        if len(end) == 4:
            end = "0" + end

        value = f"{start}-{end}"

        if value not in ranges:
            ranges.append(value)

    return ranges


def extract_email(text):
    """Findet die erste E-Mail-Adresse."""

    matches = re.findall(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        text
    )

    if not matches:
        return ""

    return matches[0]


def extract_phone(text):
    """Findet eine Telefonnummer."""

    patterns = [
        r"\b0\d{2,5}\s+\d{5,9}\b",
        r"\b0\d{2,5}\s+\d{3,5}\s+\d{2,5}\b",
        r"\b0\d{2,5}\s+\d{2,5}\s+\d{2,5}\b",
        r"\b0\d{8,12}\b",
    ]

    candidates = []

    for pattern in patterns:
        candidates.extend(re.findall(pattern, text))

    candidates = unique_preserve_order(candidates)

    if not candidates:
        return ""

    for candidate in candidates:
        if " " in candidate:
            return candidate.strip()

    return candidates[0].strip()


def extract_name(block):
    """
    Extrahiert den Namen nach 'Psychotherapie'.

    Beispiele:

    Frau Dr. Brigitta Blum
    Frau Uta Voigt
    Herr Bernd Sonntag
    """

    pattern = re.compile(
        r"Psychotherapie\s+"
        r"((?:Frau|Herr)\s+"
        r"(?:Dr\.\s+)?"
        r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+"
        r"(?:\s+[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+)+)"
    )

    match = pattern.search(block)

    if match:
        return match.group(1).strip()

    return ""


def extract_address(block):
    """
    Versucht die Adresse aus dem Block zu extrahieren.

    Beispiel:

    Schulstraße 2713187 Berlin

    wird zu:

    Schulstraße 27, 13187 Berlin
    """

    plz_match = re.search(r"\b(1\d{4})\s+Berlin\b", block)

    if not plz_match:
        return ""

    before_plz = block[:plz_match.start()]

    name_match = re.search(
        r"Psychotherapie\s+"
        r"(?:Frau|Herr)\s+"
        r"(?:Dr\.\s+)?"
        r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+"
        r"(?:\s+[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+)+",
        before_plz
    )

    if name_match:
        address = before_plz[name_match.end():]
    else:
        address = before_plz

    address = address.strip()

    address = re.split(
        r"\b(?:0\d{2,5}[\s\d]+|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
        address
    )[0]

    address = address.strip()

    address = re.sub(
        r"(\d)(1\d{4})$",
        r"\1, \2",
        address
    )

    return f"{address}, {plz_match.group(1)} Berlin".strip(", ")


# ============================================================
# WOCHENTAGE ERKENNEN
# ============================================================

def find_day_sections(text):

    pattern = re.compile(
        rf"(?P<day>{WEEKDAY_PATTERN})"
        rf"\s+(?P<date>{DATE_PATTERN})"
    )

    sections = []

    for match in pattern.finditer(text):

        sections.append({
            "day": match.group("day"),
            "start": match.start(),
            "end": match.end(),
        })

    return sections


# ============================================================
# ZEITEN IN MINUTEN UMWANDELN
# ============================================================

def time_to_minutes(value):

    hour, minute = map(int, value.split(":"))

    return hour * 60 + minute


# ============================================================
# TELEFONISCHE ERREICHBARKEIT
# ============================================================

def guess_phone_ranges(ranges):

    if not ranges:
        return []

    if len(ranges) == 1:
        return ranges

    parsed = []

    for r in ranges:

        start, end = r.split("-")

        parsed.append({
            "value": r,
            "start": time_to_minutes(start),
            "end": time_to_minutes(end),
            "duration": (
                time_to_minutes(end)
                - time_to_minutes(start)
            )
        })

    # Telefonische Erreichbarkeit ist im Beispiel
    # normalerweise das kürzere Zeitintervall.

    short = [
        item
        for item in parsed
        if item["duration"] <= 120
    ]

    if short:
        return [
            item["value"]
            for item in short
        ]

    return [parsed[-1]["value"]]


def extract_phone_hours(block):

    result = {
        day: ""
        for day in WEEKDAYS
    }

    marker = "Telefonische Erreichbarkeit"

    phone_marker = block.find(marker)

    if phone_marker == -1:
        return result

    phone_section = block[phone_marker:]

    day_sections = find_day_sections(phone_section)

    if not day_sections:
        return result

    for i, section in enumerate(day_sections):

        start = section["end"]

        if i + 1 < len(day_sections):
            end = day_sections[i + 1]["start"]
        else:
            end = len(phone_section)

        day_text = phone_section[start:end]

        day = section["day"]

        if re.search(
            r"Keine\s+Sprechstunde",
            day_text,
            flags=re.IGNORECASE
        ):
            result[day] = "Keine Sprechstunde"
            continue

        ranges = extract_time_ranges(day_text)

        if not ranges:
            result[day] = ""
            continue

        phone_ranges = guess_phone_ranges(ranges)

        result[day] = "; ".join(phone_ranges)

    return result


# ============================================================
# THERAPEUTEN TRENNEN
# ============================================================

def split_therapist_blocks(text):

    positions = [
        match.start()
        for match in re.finditer(
            r"Psychotherapie",
            text
        )
    ]

    blocks = []

    for i, start in enumerate(positions):

        if i + 1 < len(positions):
            end = positions[i + 1]
        else:
            end = len(text)

        block = text[start:end].strip()

        if block:
            blocks.append(block)

    return blocks


# ============================================================
# EINEN THERAPEUTEN PARSEN
# ============================================================

def parse_therapist(block):

    name = extract_name(block)
    email = extract_email(block)
    phone = extract_phone(block)
    address = extract_address(block)

    phone_hours = extract_phone_hours(block)

    return {
        "Name": name,
        "Adresse": address,
        "Telefon": phone,
        "E-Mail": email,
        "Montag": phone_hours["Montag"],
        "Dienstag": phone_hours["Dienstag"],
        "Mittwoch": phone_hours["Mittwoch"],
        "Donnerstag": phone_hours["Donnerstag"],
        "Freitag": phone_hours["Freitag"],
        "Samstag": phone_hours["Samstag"],
        "Sonntag": phone_hours["Sonntag"],
    }


# ============================================================
# HAUPTPROGRAMM
# ============================================================

def main():

    input_path = Path(INPUT_FILE)

    if not input_path.exists():

        print()
        print(
            f"FEHLER: Die Datei '{INPUT_FILE}' "
            "wurde nicht gefunden."
        )
        print()
        print(
            "Die Ordnerstruktur sollte so aussehen:"
        )
        print()
        print("116117suche/")
        print("├── 116117_parser.py")
        print("└── ergebnisse.txt")
        print()

        sys.exit(1)

    try:
        text = input_path.read_text(
            encoding="utf-8"
        )

    except UnicodeDecodeError:

        text = input_path.read_text(
            encoding="cp1252"
        )

    text = normalize_text(text)

    blocks = split_therapist_blocks(text)

    if not blocks:

        print(
            "Keine 'Psychotherapie'-Einträge gefunden."
        )

        sys.exit(1)

    therapists = []

    for block in blocks:

        therapist = parse_therapist(block)

        if therapist["Name"]:
            therapists.append(therapist)

    if not therapists:

        print(
            "Es konnten keine Therapeuten erkannt werden."
        )

        sys.exit(1)

    fieldnames = [
        "Name",
        "Adresse",
        "Telefon",
        "E-Mail",
        "Montag",
        "Dienstag",
        "Mittwoch",
        "Donnerstag",
        "Freitag",
        "Samstag",
        "Sonntag",
    ]

    output_path = Path(OUTPUT_FILE)

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as csvfile:

        writer = csv.DictWriter(
            csvfile,
            fieldnames=fieldnames,
            delimiter=";",
            quoting=csv.QUOTE_MINIMAL
        )

        writer.writeheader()

        for therapist in therapists:
            writer.writerow(therapist)

    print()
    print("=" * 60)
    print("FERTIG")
    print("=" * 60)
    print()
    print(
        f"Gefundene Therapeuten: {len(therapists)}"
    )
    print(
        f"CSV-Datei: {output_path.resolve()}"
    )
    print()


if __name__ == "__main__":
    main()