#!/usr/bin/env python3
"""
Check a deck list against your collection.

Usage:
    python scripts/check_deck.py <deck.txt> [--plan]

Outputs (written to data/output/):
    <deck>_missing.txt      cards still needed for this deck (one file per deck)
    order_check.html        combined report for all decks checked this session

With --plan:
    Cards already queued in data/order_plan.txt count as virtually owned.
    This deck's missing cards are added to the plan for future checks.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mtg.db import connect
from mtg.deck_check import build_combined_html, build_missing_txt, check_deck
from mtg.order_plan import add_to_plan, load_plan

OUTPUT_DIR   = Path(__file__).parent.parent / "data" / "output"
SESSION_FILE = OUTPUT_DIR / "order_session.json"
HTML_FILE    = OUTPUT_DIR / "order_check.html"


def load_session() -> list[dict]:
    if SESSION_FILE.exists():
        return json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    return []


def save_session(session: list[dict]) -> None:
    SESSION_FILE.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")


def result_to_json(result: dict) -> dict:
    return {
        "owned":   [list(t) for t in result["owned"]],
        "planned": [list(t) for t in result["planned"]],
        "partial": [list(t) for t in result["partial"]],
        "missing": [list(t) for t in result["missing"]],
    }


def result_from_json(d: dict) -> dict:
    return {
        "owned":   [tuple(t) for t in d["owned"]],
        "planned": [tuple(t) for t in d["planned"]],
        "partial": [tuple(t) for t in d["partial"]],
        "missing": [tuple(t) for t in d["missing"]],
    }


def main():
    args = sys.argv[1:]
    use_plan = "--plan" in args
    paths = [a for a in args if not a.startswith("--")]

    if not paths:
        print("Usage: python scripts/check_deck.py <path/to/deck.txt> [--plan]")
        sys.exit(1)

    deck_path = Path(paths[0])
    if not deck_path.exists():
        print(f"File not found: {deck_path}")
        sys.exit(1)

    plan = load_plan() if use_plan else None

    conn = connect()
    result = check_deck(deck_path, conn, plan=plan)
    conn.close()

    owned   = result["owned"]
    planned = result["planned"]
    partial = result["partial"]
    missing = result["missing"]
    total_cards = len(owned) + len(planned) + len(partial) + len(missing)

    print(f"\nDeck check: {deck_path.name}")
    print(f"{'─' * 40}")
    print(f"  {len(owned)} / {total_cards} unique cards fully owned")
    if use_plan:
        print(f"  {len(planned)} covered by order plan")
    print(f"  {len(partial)} partially owned  |  {len(missing)} not owned at all")

    if planned:
        print("\n── Covered by order plan ──")
        for name, needed, have_db, have_plan in sorted(planned):
            print(f"  {name}: {have_db} owned + {have_plan} on order = {needed} needed")

    if partial:
        print("\n── Partial (need more copies) ──")
        for name, needed, have_db, have_plan in sorted(partial):
            have_total = have_db + have_plan
            print(f"  {name}: have {have_total}, need {needed}  → still need {needed - have_total}")

    if missing:
        print("\n── Missing (not in collection) ──")
        for name, needed in sorted(missing):
            print(f"  {name}  ×{needed}")

    if owned and not planned and not partial and not missing:
        print("\n  You own every card in this deck.")

    if use_plan:
        additions = []
        for name, needed, have_db, have_plan in partial:
            deficit = needed - have_db - have_plan
            if deficit > 0:
                additions.append((name, deficit))
        for name, needed in missing:
            additions.append((name, needed))

        if additions:
            _, new_copies = add_to_plan(additions)
            print(f"\n  Order plan updated: +{len(additions)} cards ({new_copies} copies) added")
        else:
            print("\n  Order plan unchanged — no new cards needed for this deck")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = deck_path.stem

    # Per-deck missing TXT
    missing_txt = build_missing_txt(result)
    if missing_txt:
        txt_path = OUTPUT_DIR / f"{stem}_missing.txt"
        txt_path.write_text(missing_txt, encoding="utf-8")
        need_count = sum(n - db - pl for _, n, db, pl in partial) + sum(n for _, n in missing)
        print(f"\n  Missing list → {txt_path}")
        print(f"  ({need_count} total copies to acquire for this deck)")
    else:
        print("\n  Nothing to acquire for this deck.")

    # Combined HTML — upsert this deck into the session, regenerate
    session = load_session()
    entry = {"deck_name": stem, **result_to_json(result)}
    session = [e for e in session if e["deck_name"] != stem]  # replace if re-checked
    session.append(entry)
    save_session(session)

    html_data = [{"deck_name": e["deck_name"], **result_from_json(e)} for e in session]
    HTML_FILE.write_text(build_combined_html(html_data), encoding="utf-8")
    print(f"  HTML report  → {HTML_FILE}")
    print()


if __name__ == "__main__":
    main()
