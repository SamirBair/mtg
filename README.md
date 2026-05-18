# MTG Collection Manager

Local Magic: The Gathering collection tracker. Imports card data from mpcfill.com XML exports into a SQLite database, with Google Sheets sync planned.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Import a collection

Drop your mpcfill XML file into `data/imports/`, then:

```bash
python scripts/import_xml.py data/imports/order.xml
```

The database is created automatically at `data/mtg.db`.

## Inspect the database

```bash
sqlite3 data/mtg.db "SELECT name, set_code, quantity FROM cards ORDER BY name;"
```

## Project layout

```
mtg/          Python package
  db.py       SQLite schema + upsert helpers
  importer.py mpcfill XML parser
  sheets.py   Google Sheets sync (stub)
scripts/
  import_xml.py  CLI importer
data/
  imports/    Drop XML files here (gitignored)
  mtg.db      SQLite database (gitignored)
```
