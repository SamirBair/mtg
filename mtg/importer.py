import re
import sqlite3
from pathlib import Path
from xml.etree import ElementTree as ET

from mtg.db import is_already_imported, mark_imported, upsert_card

_SET_RE = re.compile(r"\[([A-Z0-9]+)\]")
_NUM_RE = re.compile(r"\{(\d+)\}")

# Metadata suffixes to strip from mpcfill filenames, in order:
#   1. file extension
#   2. set code in brackets: [DFT]
#   3. collector number in braces: {191}
#   4. parenthetical variant: (Normal) or (OTJ 20) — a single capitalised word
#      or an uppercase set code followed by a number
_STRIP_EXT    = re.compile(r"\.[a-zA-Z]{2,4}$")
_STRIP_SET    = re.compile(r"\s*\[[A-Z0-9]+\]")
_STRIP_NUM    = re.compile(r"\s*\{[0-9]+\}")
_STRIP_PARENS = re.compile(r"\s*\([^)]*\)")


def _name_from_filename(filename: str) -> str:
    name = _STRIP_EXT.sub("", filename)
    name = _STRIP_SET.sub("", name)
    name = _STRIP_NUM.sub("", name)
    name = _STRIP_PARENS.sub("", name)
    return name.strip()


def _parse_card(card_el: ET.Element) -> dict:
    filename = (card_el.findtext("name") or "").strip()
    query    = (card_el.findtext("query") or "").strip()

    name = _name_from_filename(filename) if filename else query.title()

    slots_text = (card_el.findtext("slots") or "").strip()
    quantity = len([s for s in slots_text.split(",") if s.strip()]) if slots_text else 1

    set_match = _SET_RE.search(filename)
    num_match = _NUM_RE.search(filename)
    set_code         = set_match.group(1) if set_match else None
    collector_number = num_match.group(1) if num_match else None

    return {
        "name": name,
        "quantity": quantity,
        "set_code": set_code,
        "collector_number": collector_number,
    }


def import_txt(path: Path, conn: sqlite3.Connection, label: str = "Proxies") -> list[dict]:
    if is_already_imported(conn, path.name):
        raise ValueError(f"{path.name} has already been imported. Delete it from imported_files to re-import.")

    cards = []
    in_mainboard = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            in_mainboard = line.lower() == "# mainboard"
            continue
        if not in_mainboard:
            continue
        upsert_card(conn, name=line, quantity=1, label=label)
        cards.append({"name": line, "quantity": 1, "set_code": None, "collector_number": None})

    mark_imported(conn, path.name)
    conn.commit()
    return cards


def import_xml(path: Path, conn: sqlite3.Connection, label: str = "Proxies") -> list[dict]:
    if is_already_imported(conn, path.name):
        raise ValueError(f"{path.name} has already been imported. Delete it from imported_files to re-import.")

    tree = ET.parse(path)
    root = tree.getroot()

    cards = []
    for card_el in root.findall(".//fronts/card"):
        card = _parse_card(card_el)
        if card["name"]:
            upsert_card(conn, label=label, **card)
            cards.append(card)

    mark_imported(conn, path.name)
    conn.commit()
    return cards
