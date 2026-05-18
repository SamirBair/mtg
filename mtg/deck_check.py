import re
import sqlite3
from pathlib import Path

from mtg.db import find_card

_QTY_RE = re.compile(r"^(\d+)x?\s+(.+)$", re.IGNORECASE)

_SECTION_MAINBOARD = {"# mainboard", "mainboard", "main", "deck", "# main", "# deck"}
_SECTION_SIDEBOARD = {"# sideboard", "sideboard", "sb", "# sb", "# side"}

BASIC_LANDS = {"island", "plains", "swamp", "forest", "mountain"}


def parse_deck(path: Path) -> list[tuple[str, int, str]]:
    """Return list of (name, quantity, section) from a deck list file."""
    entries = []
    section = "mainboard"
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        lower = line.lower().rstrip(":")
        if lower in _SECTION_MAINBOARD:
            section = "mainboard"
            continue
        if lower in _SECTION_SIDEBOARD:
            section = "sideboard"
            continue
        if line.startswith("#"):
            continue
        m = _QTY_RE.match(line)
        if m:
            entries.append((m.group(2).strip(), int(m.group(1)), section))
    return entries


def check_deck(
    deck_path: Path,
    conn: sqlite3.Connection,
    plan: dict[str, int] | None = None,
) -> dict:
    """
    Compare deck list against collection (and optional order plan).

    Returns:
        owned:   [(name, needed, have_db)]
        planned: [(name, needed, have_db, have_plan)]   # only when plan provided
        partial: [(name, needed, have_db, have_plan)]   # have_plan=0 when no plan
        missing: [(name, needed)]
    """
    entries = parse_deck(deck_path)

    totals: dict[str, int] = {}
    for name, needed, section in entries:
        if name.lower() in BASIC_LANDS:
            continue
        totals[name] = totals.get(name, 0) + needed

    owned, planned_list, partial, missing = [], [], [], []

    for name, needed in totals.items():
        have_db   = find_card(conn, name)
        have_plan = (plan or {}).get(name.lower(), 0)
        have_total = have_db + have_plan

        if have_db >= needed:
            owned.append((name, needed, have_db))
        elif plan is not None and have_total >= needed:
            planned_list.append((name, needed, have_db, have_plan))
        elif have_total > 0:
            partial.append((name, needed, have_db, have_plan))
        else:
            missing.append((name, needed))

    return {
        "owned":   owned,
        "planned": planned_list,
        "partial": partial,
        "missing": missing,
    }


def build_html_report(deck_name: str, result: dict) -> str:
    owned   = result["owned"]
    planned = result["planned"]
    partial = result["partial"]
    missing = result["missing"]
    total   = len(owned) + len(planned) + len(partial) + len(missing)
    need_count = (
        sum(n - (db + pl) for _, n, db, pl in partial)
        + sum(n for _, n in missing)
    )

    def card_rows(cards, mode="owned"):
        rows = []
        for entry in sorted(cards, key=lambda x: x[0]):
            name   = entry[0]
            needed = entry[1]
            if mode == "owned":
                have_db = entry[2]
                col = f"{have_db} / {needed}"
                note = ""
            elif mode == "planned":
                have_db, have_plan = entry[2], entry[3]
                col = f"{have_db}+{have_plan} / {needed}"
                note = f"<span class='plan-note'>{have_plan} on order</span>"
            elif mode == "partial":
                have_db, have_plan = entry[2], entry[3]
                have_total = have_db + have_plan
                deficit = needed - have_total
                col = f"{have_db}+{have_plan} / {needed}"
                note = f"<span class='deficit'>still need {deficit} more</span>"
            else:  # missing
                col = f"0 / {needed}"
                note = ""
            rows.append(f"<tr><td>{name}</td><td class='qty'>{col}</td><td>{note}</td></tr>")
        return "\n".join(rows)

    def section(title, css_class, cards, mode="owned"):
        if not cards:
            return ""
        return f"""
    <div class="section {css_class}">
      <h2>{title} <span class="count">({len(cards)})</span></h2>
      <table>
        <thead><tr><th>Card</th><th>Have / Need</th><th></th></tr></thead>
        <tbody>{card_rows(cards, mode)}</tbody>
      </table>
    </div>"""

    plan_note = " &nbsp;·&nbsp; <em>order plan active</em>" if planned or result.get("_plan_active") else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Deck check — {deck_name}</title>
<style>
  body {{ font-family: sans-serif; max-width: 860px; margin: 2rem auto; padding: 0 1rem; color: #222; }}
  h1   {{ font-size: 1.4rem; margin-bottom: .25rem; }}
  .stats {{ color: #555; margin-bottom: 2rem; font-size: .95rem; }}
  .section {{ margin-bottom: 2rem; }}
  h2   {{ font-size: 1.1rem; margin-bottom: .5rem; border-bottom: 2px solid currentColor; padding-bottom: .2rem; }}
  .count {{ font-weight: normal; font-size: .9rem; }}
  table {{ border-collapse: collapse; width: 100%; font-size: .9rem; }}
  th   {{ text-align: left; padding: .3rem .6rem; background: #f4f4f4; }}
  td   {{ padding: .25rem .6rem; border-bottom: 1px solid #eee; }}
  .qty {{ text-align: right; width: 7rem; font-variant-numeric: tabular-nums; }}
  .deficit   {{ color: #c05000; font-size: .85rem; }}
  .plan-note {{ color: #0070a0; font-size: .85rem; }}
  .owned   h2 {{ color: #2a7a2a; }}
  .planned h2 {{ color: #0070a0; }}
  .partial h2 {{ color: #b06000; }}
  .missing h2 {{ color: #a02020; }}
</style>
</head>
<body>
<h1>Deck check — {deck_name}</h1>
<p class="stats">
  {len(owned)} of {total} unique cards fully owned &nbsp;·&nbsp;
  {len(planned)} covered by order plan &nbsp;·&nbsp;
  {len(partial)} partial &nbsp;·&nbsp;
  {len(missing)} missing &nbsp;·&nbsp;
  <strong>{need_count} copies still to acquire</strong>{plan_note}
</p>
{section("Owned", "owned", owned, "owned")}
{section("Covered by order plan", "planned", planned, "planned")}
{section("Partial — need more copies", "partial", partial, "partial")}
{section("Missing — not in collection", "missing", [(n, needed, 0, 0) for n, needed in missing], "missing")}
</body>
</html>
"""


def build_combined_html(session: list[dict]) -> str:
    """Build one HTML page summarising all deck checks in the current session."""

    total_to_acquire = sum(
        sum(n - db - pl for _, n, db, pl in d["partial"])
        + sum(n for _, n in d["missing"])
        for d in session
    )
    unique_to_acquire = len({
        name
        for d in session
        for name, *_ in d["partial"]
    } | {
        name
        for d in session
        for name, *_ in d["missing"]
    })

    def card_rows(cards, mode):
        rows = []
        for entry in sorted(cards, key=lambda x: x[0]):
            name   = entry[0]
            needed = entry[1]
            if mode == "owned":
                col, note = f"{entry[2]} / {needed}", ""
            elif mode == "planned":
                db, pl = entry[2], entry[3]
                col  = f"{db}+{pl} / {needed}"
                note = f"<span class='plan-note'>{pl} on order</span>"
            elif mode == "partial":
                db, pl = entry[2], entry[3]
                deficit = needed - db - pl
                col  = f"{db}+{pl} / {needed}"
                note = f"<span class='deficit'>still need {deficit}</span>"
            else:
                col, note = f"0 / {needed}", ""
            rows.append(f"<tr><td>{name}</td><td class='qty'>{col}</td><td>{note}</td></tr>")
        return "\n".join(rows)

    def subsection(title, css_class, cards, mode):
        if not cards:
            return ""
        return f"""
        <div class="subsection {css_class}">
          <h3>{title} <span class="count">({len(cards)})</span></h3>
          <table>
            <thead><tr><th>Card</th><th>Have / Need</th><th></th></tr></thead>
            <tbody>{card_rows(cards, mode)}</tbody>
          </table>
        </div>"""

    def deck_section(d):
        name    = d["deck_name"]
        owned   = d["owned"]
        planned = d["planned"]
        partial = d["partial"]
        missing = d["missing"]
        total   = len(owned) + len(planned) + len(partial) + len(missing)
        need    = sum(n - db - pl for _, n, db, pl in partial) + sum(n for _, n in missing)
        return f"""
  <div class="deck">
    <h2>{name.replace("_", " ")}</h2>
    <p class="deck-stats">
      {len(owned)} / {total} owned &nbsp;·&nbsp;
      {len(planned)} on order &nbsp;·&nbsp;
      {len(partial)} partial &nbsp;·&nbsp;
      {len(missing)} missing &nbsp;·&nbsp;
      <strong>{need} copies to acquire</strong>
    </p>
    {subsection("Owned", "owned", owned, "owned")}
    {subsection("Covered by order plan", "planned", planned, "planned")}
    {subsection("Partial", "partial", partial, "partial")}
    {subsection("Missing", "missing", [(n, needed, 0, 0) for n, needed in missing], "missing")}
  </div>"""

    decks_html = "\n".join(deck_section(d) for d in session)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Order check</title>
<style>
  body  {{ font-family: sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; color: #222; }}
  h1   {{ font-size: 1.5rem; margin-bottom: .2rem; }}
  .summary {{ color: #555; margin-bottom: 2.5rem; font-size: .95rem; }}
  .deck {{ border: 1px solid #ddd; border-radius: 6px; padding: 1.2rem 1.4rem; margin-bottom: 2rem; }}
  h2   {{ font-size: 1.15rem; margin: 0 0 .3rem; }}
  .deck-stats {{ color: #555; font-size: .9rem; margin: 0 0 1rem; }}
  .subsection {{ margin-bottom: 1.2rem; }}
  h3   {{ font-size: .95rem; margin-bottom: .4rem; border-bottom: 2px solid currentColor; padding-bottom: .15rem; display: inline-block; }}
  .count {{ font-weight: normal; font-size: .85rem; }}
  table {{ border-collapse: collapse; width: 100%; font-size: .88rem; margin-top: .3rem; }}
  th   {{ text-align: left; padding: .25rem .5rem; background: #f4f4f4; }}
  td   {{ padding: .2rem .5rem; border-bottom: 1px solid #eee; }}
  .qty {{ text-align: right; width: 7rem; font-variant-numeric: tabular-nums; }}
  .deficit   {{ color: #c05000; font-size: .82rem; }}
  .plan-note {{ color: #0070a0; font-size: .82rem; }}
  .owned   h3 {{ color: #2a7a2a; }}
  .planned h3 {{ color: #0070a0; }}
  .partial h3 {{ color: #b06000; }}
  .missing h3 {{ color: #a02020; }}
</style>
</head>
<body>
<h1>Order check</h1>
<p class="summary">
  {len(session)} deck{"s" if len(session) != 1 else ""} checked &nbsp;·&nbsp;
  {unique_to_acquire} unique cards to acquire &nbsp;·&nbsp;
  <strong>{total_to_acquire} total copies to order</strong>
</p>
{decks_html}
</body>
</html>
"""


def build_missing_txt(result: dict) -> str:
    """Format the cards still needed (after plan) as a plain list."""
    entries = []
    for name, needed, have_db, have_plan in result["partial"]:
        deficit = needed - have_db - have_plan
        if deficit > 0:
            entries.append((name, deficit))
    for name, needed in result["missing"]:
        entries.append((name, needed))

    lines = [f"{qty}x {name}" for name, qty in sorted(entries)]
    return "\n".join(lines) + "\n" if lines else ""
