# MTG Collection Manager

Local Magic: The Gathering collection tracker. Imports card data from mpcfill.com XML exports into a SQLite database, with Google Sheets sync planned.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

---

## Importing cards into the DB

Drop your mpcfill XML (or plaintext TXT) file into `data/imports/`, then:

```bash
python3 scripts/import_xml.py data/imports/order.xml
```

The file is moved to `data/imports/processed/` after a successful import.
The database is created automatically at `data/mtg.db`.

**Options:**
```bash
# Assign a label (default: Proxies)
python3 scripts/import_xml.py data/imports/order.xml --label Official

# Clear the order plan after importing (use when a full order has arrived)
python3 scripts/import_xml.py data/imports/order.xml --clear-plan
```

---

## Checking a deck against the collection

Create a plain text deck list file in the standard format:

```
Deck
4 Lightning Bolt
2 Counterspell

Sideboard
2 Rest in Peace
```

Then run:

```bash
python3 scripts/check_deck.py path/to/deck.txt
```

This writes two files to `data/output/`:
- `<deck>_missing.txt` — cards you still need, ready to upload to mpcfill
- `order_check.html` — combined visual report for all decks checked this session

**Notes:**
- Basic lands (Island, Plains, Swamp, Forest, Mountain) are always skipped
- Cards appearing in both mainboard and sideboard are counted once with combined quantity

---

## Planning an order across multiple decks

Use `--plan` to track missing cards across several deck checks so the same card is never ordered twice.

```bash
# Check deck 1 — missing cards are added to the order plan
python3 scripts/check_deck.py deck1.txt --plan

# Check deck 2 — cards already in the plan show as "Covered by order plan"
python3 scripts/check_deck.py deck2.txt --plan

# View the consolidated order plan
python3 scripts/order_plan.py

# After placing the order and importing the new cards:
python3 scripts/order_plan.py --clear
```

Each deck produces its own `_missing.txt` for separate upload. The `order_check.html` is updated after every check and shows all decks in one view.

---

## Inspect the database

```bash
sqlite3 data/mtg.db "SELECT name, label, quantity FROM cards ORDER BY name;"
```

---

## Project layout

```
mtg/
  db.py           SQLite schema + query helpers
  importer.py     mpcfill XML and plaintext TXT parser
  deck_check.py   deck vs. collection comparison + HTML/TXT output
  order_plan.py   persistent order plan (data/order_plan.txt)
  sheets.py       Google Sheets sync (stub, not yet implemented)
scripts/
  import_xml.py   import a card file into the DB
  check_deck.py   check a deck list against the collection
  order_plan.py   view or clear the active order plan
data/
  imports/        drop files here to import (gitignored)
  imports/processed/  files moved here after import (gitignored)
  mtg.db          SQLite database (gitignored)
  order_plan.txt  active order plan (gitignored)
  output/         generated missing lists and HTML reports (gitignored)
```
