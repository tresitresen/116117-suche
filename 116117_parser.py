#!/usr/bin/env python3

import re
import csv
from pathlib import Path


INPUT_FILE = "ergebnisse.txt"
OUTPUT_FILE = "therapeuten_telefon.csv"


WEEKDAYS = [
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag",
]


DAY_ABBREVIATIONS = {
    "Mo": "Montag",
    "Di": "Dienstag",
    "Mi": "Mittwoch",
    "Do": "Donnerstag",
    "Fr": "Freitag",
    "Sa": "Samstag",
    "So": "Sonntag",
}


# ------------------------------------------------------------
# TEXT BEREINIGEN
# ------------------------------------------------------------

def clean_text(text):
    text = text.replace("\r", " ")
    text = text.replace("\n", " ")
    text = text.replace("\xa0", " ")
    text = text.replace("\u200b", "")

    # Mehrere Leerzeichen zusammenfassen
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ------------------------------------------------------------
# NAMEN
# ------------------------------------------------------------

def extract_name(block):

    pattern = re.compile(
        r"Psychotherapie\s+"
        r"((?:Frau|Herr)"
        r"(?:\s+Dr\.)?"
        r"(?:\s+[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+)+)"
    )

    match = pattern.search(block)

    if match:
        return match.group(1).strip()

    return ""


# ------------------------------------------------------------
# E-MAIL
# ------------------------------------------------------------

def extract_email(block):

    matches = re.findall(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        block
    )

    if matches:
        return matches[0]

    return ""


# ------------------------------------------------------------
# TELEFON
# ------------------------------------------------------------

def extract_phone(block):

    # Wir suchen Telefonnummern mit mindestens 8 Ziffern.
    # Dabei dürfen Leerzeichen enthalten sein.

    matches = re.findall(
        r"(?<!\d)"
        r"(0\d{2,5}"
        r"(?:\s*\d{2,5}){2,4})"
        r"(?!\d)",
        block
    )

    if not matches:
        return ""

    # Telefonnummern normalisieren
    phones = []

    for phone in matches:

        phone = re.sub(r"\s+", " ", phone).strip()

        if phone not in phones:
            phones.append(phone)

    return phones[0] if phones else ""


# ------------------------------------------------------------
# ADRESSE
# ------------------------------------------------------------

def extract_address(block):

    # Wir suchen nach einer Berliner PLZ.
    #
    # Funktioniert sowohl bei:
    #
    # 13187 Berlin
    #
    # als auch bei:
    #
    # 2713187 Berlin
    #
    # weil die PLZ am Ende immer 13187 ist.

    plz_match = re.search(
        r"(1\d{4})\s*Berlin",
        block
    )

    if not plz_match:
        return ""

    plz = plz_match.group(1)

    # Alles zwischen dem Namen und der PLZ
    name = extract_name(block)

    if not name:
        return ""

    name_position = block.find(name)

    if name_position == -1:
        return ""

    start = name_position + len(name)
    end = plz_match.start()

    address = block[start:end]

    # Typische nachfolgende Angaben entfernen
    address = re.sub(
        r"\b(?:Sprechstunde|Telefonische|Psych\.)\b.*$",
        "",
        address,
        flags=re.IGNORECASE
    )

    address = address.strip(" ,")

    # Falls die Hausnummer direkt an die PLZ geklebt wurde,
    # steht sie bereits in "address".
    #
    # Beispiel:
    #
    # Schulstraße 27
    #
    # + 13187 Berlin

    # Doppelte Leerzeichen entfernen
    address = re.sub(r"\s+", " ", address)

    if not address:
        return f"{plz} Berlin"

    return f"{address}, {plz} Berlin"


# ------------------------------------------------------------
# TELEFONZEITEN
# ------------------------------------------------------------

TIME_REGEX = re.compile(
    r"(\d{1,2}:\d{2})\s*(?:bis|-)\s*(\d{1,2}:\d{2})"
)


def normalize_time(start, end):

    if len(start) == 4:
        start = "0" + start

    if len(end) == 4:
        end = "0" + end

    return f"{start}-{end}"


def extract_unique_times(text):

    times = []

    for match in TIME_REGEX.finditer(text):

        value = normalize_time(
            match.group(1),
            match.group(2)
        )

        if value not in times:
            times.append(value)

    return times


# ------------------------------------------------------------
# TAGE ERKENNEN
# ------------------------------------------------------------

DAY_REGEX = re.compile(
    r"(Heute\s+Heute\s+\d{2}\.\d{2}\.\d{4})"
    r"|"
    r"(Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag)"
    r"(?:\s+(Mo|Di|Mi|Do|Fr|Sa|So))?"
    r"\s+\d{2}\.\d{2}\.\d{4}"
)


def identify_day(match):

    # "Heute"
    if match.group(1):
        return "__HEUTE__"

    # Normaler Wochentag
    day = match.group(2)

    if day:
        return day

    return None


def get_today_from_text(text):

    match = re.search(
        r"Heute\s+Heute\s+"
        r"(\d{2})\.(\d{2})\.(\d{4})",
        text
    )

    if not match:
        return None

    from datetime import date

    d = date(
        int(match.group(3)),
        int(match.group(2)),
        int(match.group(1))
    )

    german_days = [
        "Montag",
        "Dienstag",
        "Mittwoch",
        "Donnerstag",
        "Freitag",
        "Samstag",
        "Sonntag",
    ]

    return german_days[d.weekday()]


# ------------------------------------------------------------
# TELEFONISCHE ERREICHBARKEIT EINES BLOCKS
# ------------------------------------------------------------

def extract_phone_hours(block):

    result = {
        day: ""
        for day in WEEKDAYS
    }

    marker = block.find("Telefonische Erreichbarkeit")

    if marker == -1:
        return result

    section = block[marker:]

    today = get_today_from_text(section)

    day_matches = list(DAY_REGEX.finditer(section))

    if not day_matches:
        return result

    for i, match in enumerate(day_matches):

        day = identify_day(match)

        if day == "__HEUTE__":
            day = today

        if day is None:
            continue

        # Ende dieses Tages
        if i + 1 < len(day_matches):
            end = day_matches[i + 1].start()
        else:
            end = len(section)

        day_text = section[
            match.end():end
        ]

        # Keine Sprechstunde
        if re.search(
            r"Keine\s+Sprechstunde",
            day_text,
            re.IGNORECASE
        ):
            result[day] = "Keine Sprechstunde"
            continue

        times = extract_unique_times(day_text)

        if not times:
            continue

        # ----------------------------------------------------
        # WICHTIG:
        #
        # Die 116117-Seite kopiert die Zeitangaben doppelt:
        #
        # 08:00 bis 12:00
        # 08:00 - 12:00
        #
        # Durch extract_unique_times() haben wir daraus nur:
        #
        # 08:00-12:00
        #
        # gemacht.
        #
        # Die erste Zeit ist die Sprechstunde.
        # Danach kommen die telefonischen Zeiten.
        # ----------------------------------------------------

        if len(times) >= 2:

            phone_times = times[1:]

            result[day] = "; ".join(phone_times)

        else:
            # Wenn nur eine Zeit vorhanden ist,
            # können wir nicht sicher unterscheiden,
            # ob sie Sprechstunde oder Telefonzeit ist.
            #
            # In deinem Datensatz lassen wir sie deshalb
            # leer.
            result[day] = ""

    return result


# ------------------------------------------------------------
# THERAPEUTEN TRENNEN
# ------------------------------------------------------------

def split_blocks(text):

    # Ein neuer Eintrag beginnt jeweils bei:
    #
    # Psychotherapie
    # Frau/Herr ...

    pattern = re.compile(
        r"Psychotherapie\s+"
        r"(?:Frau|Herr)\b"
    )

    matches = list(pattern.finditer(text))

    blocks = []

    for i, match in enumerate(matches):

        start = match.start()

        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(text)

        blocks.append(
            text[start:end].strip()
        )

    return blocks


# ------------------------------------------------------------
# EINEN THERAPEUTEN VERARBEITEN
# ------------------------------------------------------------

def parse_block(block):

    phone_hours = extract_phone_hours(block)

    return {
        "Name": extract_name(block),
        "Adresse": extract_address(block),
        "Telefon": extract_phone(block),
        "E-Mail": extract_email(block),

        "Montag": phone_hours["Montag"],
        "Dienstag": phone_hours["Dienstag"],
        "Mittwoch": phone_hours["Mittwoch"],
        "Donnerstag": phone_hours["Donnerstag"],
        "Freitag": phone_hours["Freitag"],
        "Samstag": phone_hours["Samstag"],
        "Sonntag": phone_hours["Sonntag"],
    }


# ------------------------------------------------------------
# HAUPTPROGRAMM
# ------------------------------------------------------------

def main():

    input_path = Path(INPUT_FILE)

    if not input_path.exists():

        print()
        print("FEHLER")
        print(
            f"Die Datei '{INPUT_FILE}' wurde nicht gefunden."
        )
        print()
        print("Der Ordner sollte so aussehen:")
        print()
        print("116117suche/")
        print("├── 116117_parser.py")
        print("└── ergebnisse.txt")
        print()

        return

    # UTF-8 versuchen
    try:
        text = input_path.read_text(
            encoding="utf-8"
        )

    except UnicodeDecodeError:

        text = input_path.read_text(
            encoding="cp1252"
        )

    text = clean_text(text)

    blocks = split_blocks(text)

    print()
    print(
        f"Gefundene Therapeutenblöcke: {len(blocks)}"
    )

    therapists = []

    for block in blocks:

        data = parse_block(block)

        if data["Name"]:

            therapists.append(data)

    print(
        f"Erkannte Therapeuten: {len(therapists)}"
    )

    if not therapists:

        print()
        print(
            "Es wurden keine Therapeuten erkannt."
        )

        return

    columns = [
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
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=columns,
            delimiter=";"
        )

        writer.writeheader()

        writer.writerows(therapists)

    print()
    print("Fertig.")
    print()
    print(
        f"CSV erstellt: {output_path.resolve()}"
    )
    print()


if __name__ == "__main__":
    main()