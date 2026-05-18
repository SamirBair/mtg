import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "mtg.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS cards (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT NOT NULL,
    label            TEXT NOT NULL DEFAULT 'Proxies',
    set_code         TEXT,
    collector_number TEXT,
    quantity         INTEGER NOT NULL DEFAULT 0,
    imported_at      TEXT DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_cards_name_label ON cards(name, label);

CREATE TABLE IF NOT EXISTS imported_files (
    source_file TEXT PRIMARY KEY,
    imported_at TEXT DEFAULT (datetime('now'))
);
"""


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def is_already_imported(conn: sqlite3.Connection, source_file: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM imported_files WHERE source_file = ?", (source_file,)
    ).fetchone()
    return row is not None


def mark_imported(conn: sqlite3.Connection, source_file: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO imported_files (source_file) VALUES (?)", (source_file,)
    )


def find_card(conn: sqlite3.Connection, name: str) -> int:
    """Return total owned quantity across all labels (case-insensitive)."""
    row = conn.execute(
        "SELECT SUM(quantity) as qty FROM cards WHERE LOWER(name) = LOWER(?)", (name,)
    ).fetchone()
    return row["qty"] or 0


def upsert_card(
    conn: sqlite3.Connection,
    name: str,
    quantity: int,
    label: str = "Proxies",
    set_code: str | None = None,
    collector_number: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO cards (name, label, set_code, collector_number, quantity)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(name, label) DO UPDATE SET
            quantity         = quantity + excluded.quantity,
            set_code         = COALESCE(excluded.set_code, set_code),
            collector_number = COALESCE(excluded.collector_number, collector_number),
            imported_at      = datetime('now')
        """,
        (name, label, set_code, collector_number, quantity),
    )
