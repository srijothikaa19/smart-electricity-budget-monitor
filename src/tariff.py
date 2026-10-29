# PLACEHOLDER tariff. These are NOT any real utility's rates. The user edits them.
DEFAULT_TARIFF = {
    "fixed_charge": 50.0,
    "slabs": [{"upto": 100, "rate": 3.0},
              {"upto": 200, "rate": 5.0},
              {"upto": None, "rate": 8.0}],      # None = all remaining units
}

def bill_for_units(units, tariff=None):
    t = tariff or DEFAULT_TARIFF
    units = max(0.0, float(units))
    total, prev = 0.0, 0.0
    for s in t["slabs"]:
        upto = s["upto"]
        top = units if upto is None else min(units, float(upto))
        if top > prev:
            total += (top - prev) * float(s["rate"])
        if upto is None or units <= float(upto):
            break
        prev = float(upto)
    return round(total + float(t.get("fixed_charge", 0.0)), 2)

def units_for_budget(budget, tariff=None):
    """Most units you can use and still stay within the budget."""
    if budget < bill_for_units(0, tariff):
        return 0.0
    lo, hi = 0.0, 100000.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if bill_for_units(mid, tariff) <= budget:
            lo = mid
        else:
            hi = mid
    return round(lo, 2)

def budget_status(budget, bill_now, bill_proj, bill_high, stale=False, cold_start=False):
    if budget is None:
        return {"level": "NONE", "message": "Set a budget to enable warnings."}
    if bill_now >= budget:
        level, msg = "RED", "Budget already reached this cycle."
    elif bill_proj > budget:
        level, msg = "RED", "Projected bill will exceed your budget."
    elif bill_proj >= 0.9 * budget or bill_high > budget:
        level, msg = "AMBER", "Projected bill is close to your budget."
    else:
        level, msg = "GREEN", "On track to stay within budget."
    if stale:
        msg += " (Data is stale: no accepted reading for 48 hours.)"
    if cold_start:
        msg += " (Early in the cycle: the estimate is rough.)"
    return {"level": level, "message": msg}