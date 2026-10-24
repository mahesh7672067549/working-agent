"""Deterministic local Python tools with strict argument guards."""

INVENTORY = {
    "projector": {"projector", "projectors", "beamer"},
    "wi-fi": {"wi-fi", "wifi", "wi fi", "wireless", "internet"},
    "whiteboard": {"whiteboard", "white board", "whiteboards"},
    "laptops": {"laptops", "laptop", "notebooks"},
}

_ALIAS_TO_CANONICAL = {
    alias: canonical
    for canonical, aliases in INVENTORY.items()
    for alias in aliases
}


def _require_positive_int(name: str, value: int) -> int:
    """Validate positive integer and reject booleans or malformed numbers."""
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"'{name}' must be a positive integer, got: {value}")
    if value > 1_000_000:
        raise ValueError(f"'{name}' exceeds the maximum allowed limit of 1,000,000")
    return value


def calculate_budget(participants: int, days: int, daily_cost_per_person: int, budget: int) -> dict:
    """Estimate total cost and compare it to a budget.

    Args:
        participants: Number of attendees.
        days: Length of workshop in days.
        daily_cost_per_person: Cost in INR per person per day.
        budget: Total allocated budget in INR.
    """
    p = _require_positive_int("participants", participants)
    d = _require_positive_int("days", days)
    cost = _require_positive_int("daily_cost_per_person", daily_cost_per_person)
    b = _require_positive_int("budget", budget)

    total = p * d * cost
    return {
        "currency": "INR",
        "total_estimated_cost": total,
        "budget": b,
        "remaining_budget": b - total,
        "within_budget": total <= b,
    }


def check_resources(required_items: str) -> dict:
    """Check required items against the local inventory.

    Args:
        required_items: Comma-separated item names, e.g. 'projector, Wi-Fi, microphones'.
    """
    if not isinstance(required_items, str) or not required_items.strip():
        raise ValueError("required_items must be a non-empty comma-separated string")

    raw_tokens = [item.strip() for item in required_items.split(",") if item.strip()]
    available = []
    missing = []

    for raw in raw_tokens:
        cleaned = " ".join(raw.lower().split())
        canonical = _ALIAS_TO_CANONICAL.get(cleaned)
        if canonical:
            if canonical not in available:
                available.append(canonical)
        else:
            missing.append(raw)

    return {
        "available": available,
        "missing": missing,
    }