#!/usr/bin/env python3
"""
Import a card file (mpcfill XML or plaintext list) into the local SQLite collection.

Usage:
    python scripts/import_xml.py <file.xml|file.txt> [--label Proxies] [--clear-plan]

Options:
    --label <name>   Card label to assign (default: Proxies). Future values: Official
    --clear-plan     Clear the order plan after importing (use when the full order has arrived)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mtg.db import connect
from mtg.importer import import_txt, import_xml
from mtg.order_plan import clear_plan

IMPORTERS = {
    ".xml": import_xml,
    ".txt": import_txt,
}


def main():
    args = sys.argv[1:]
    clear_after = "--clear-plan" in args
    label_idx = next((i for i, a in enumerate(args) if a == "--label"), None)
    label = args[label_idx + 1] if label_idx is not None else "Proxies"
    paths = [a for a in args if not a.startswith("--") and a != (args[label_idx + 1] if label_idx is not None else None)]

    if not paths:
        print("Usage: python scripts/import_xml.py <path/to/file.xml|file.txt> [--label Proxies] [--clear-plan]")
        sys.exit(1)

    path = Path(paths[0])
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    importer = IMPORTERS.get(path.suffix.lower())
    if not importer:
        print(f"Unsupported file type: {path.suffix}  (supported: {', '.join(IMPORTERS)})")
        sys.exit(1)

    conn = connect()
    cards = importer(path, conn, label=label)
    conn.close()

    processed_dir = path.parent / "processed"
    if path.parent.name != "processed":
        processed_dir.mkdir(exist_ok=True)
        path.rename(processed_dir / path.name)
        moved_msg = f"Moved to {processed_dir / path.name}"
    else:
        moved_msg = None

    total_copies = sum(c["quantity"] for c in cards)
    print(f"Imported {len(cards)} unique cards ({total_copies} total copies) from {path.name}  [{label}]")
    if moved_msg:
        print(moved_msg)
    for c in cards:
        set_info = f" [{c['set_code']}]" if c["set_code"] else ""
        print(f"  {c['quantity']}x  {c['name']}{set_info}")

    if clear_after:
        clear_plan()
        print("\nOrder plan cleared.")


if __name__ == "__main__":
    main()
