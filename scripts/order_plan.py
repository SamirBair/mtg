#!/usr/bin/env python3
"""
View or clear the active order plan.

Usage:
    python scripts/order_plan.py          # show current plan
    python scripts/order_plan.py --clear  # wipe plan after placing order
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pathlib import Path

from mtg.order_plan import PLAN_PATH, clear_plan, load_plan_display

SESSION_FILE = Path(__file__).parent.parent / "data" / "output" / "order_session.json"
HTML_FILE    = Path(__file__).parent.parent / "data" / "output" / "order_check.html"


def main():
    if "--clear" in sys.argv:
        clear_plan()
        for f in (SESSION_FILE, HTML_FILE):
            if f.exists():
                f.unlink()
        print("Order plan and session cleared.")
        return

    plan = load_plan_display()
    if not plan:
        print("Order plan is empty. Run check_deck.py with --plan to build it.")
        return

    total_cards  = len(plan)
    total_copies = sum(plan.values())

    print(f"\nOrder plan  ({total_cards} unique cards, {total_copies} total copies)")
    print(f"{'─' * 42}")
    for name, qty in sorted(plan.items()):
        print(f"  {qty}x  {name}")
    print(f"\n  Plan file: {PLAN_PATH}")
    print()


if __name__ == "__main__":
    main()
