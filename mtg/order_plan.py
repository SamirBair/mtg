import re
from pathlib import Path

PLAN_PATH = Path(__file__).parent.parent / "data" / "order_plan.txt"

_QTY_RE = re.compile(r"^(\d+)x?\s+(.+)$")


def load_plan(path: Path = PLAN_PATH) -> dict[str, int]:
    """Return {lowercase_name: quantity} from the plan file."""
    if not path.exists():
        return {}
    plan = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        m = _QTY_RE.match(line)
        if m:
            plan[m.group(2).strip().lower()] = int(m.group(1))
    return plan


def load_plan_display(path: Path = PLAN_PATH) -> dict[str, int]:
    """Return {original_case_name: quantity} for display purposes."""
    if not path.exists():
        return {}
    plan = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        m = _QTY_RE.match(line)
        if m:
            plan[m.group(2).strip()] = int(m.group(1))
    return plan


def save_plan(plan: dict[str, int], path: Path = PLAN_PATH) -> None:
    """Write sorted `Nx Card Name` lines, skipping zero/negative quantities."""
    lines = [f"{qty}x {name}" for name, qty in sorted(plan.items()) if qty > 0]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n" if lines else "", encoding="utf-8")


def add_to_plan(additions: list[tuple[str, int]], path: Path = PLAN_PATH) -> tuple[dict[str, int], int]:
    """
    Merge (name, qty) additions into the existing plan.
    Only adds quantities that aren't already covered.
    Returns (updated_display_plan, number_of_new_copies_added).
    """
    display_plan = load_plan_display(path)
    lookup = {k.lower(): k for k in display_plan}  # lowercase → original case

    new_copies = 0
    for name, qty in additions:
        key = name.lower()
        if key in lookup:
            canonical = lookup[key]
            display_plan[canonical] = display_plan[canonical] + qty
        else:
            display_plan[name] = qty
            lookup[key] = name
        new_copies += qty

    save_plan(display_plan, path)
    return display_plan, new_copies


def clear_plan(path: Path = PLAN_PATH) -> None:
    if path.exists():
        path.unlink()
