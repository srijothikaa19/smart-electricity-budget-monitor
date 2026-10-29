import sys, os
os.environ["BLEND_N"] = "30"
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from tariff import bill_for_units, units_for_budget, budget_status
from forecast import project

IST = timezone(timedelta(hours=5.5))

# --- tariff (placeholder slabs: 100@3, 100@5, rest@8, fixed 50) ---
assert bill_for_units(0) == 50
assert bill_for_units(100) == 350
assert bill_for_units(150) == 600
assert bill_for_units(250) == 1250
assert abs(units_for_budget(600) - 150) < 0.05
assert units_for_budget(10) == 0.0

# --- budget logic ---
assert budget_status(1000, 200, 1200, 1300)["level"] == "RED"
assert budget_status(1000, 200, 950, 990)["level"] == "AMBER"
assert budget_status(1000, 200, 700, 800)["level"] == "GREEN"
assert budget_status(1000, 1000, 700, 800)["level"] == "RED"
assert budget_status(None, 0, 0, 0)["level"] == "NONE"

# --- forecast on a known constant load of 10 kWh/day ---
def make(start, blocks, per_block):
    recs = [{"device_id": "T", "captured_at": start.astimezone(timezone.utc).isoformat(),
             "consumption": 0.0, "status": "ACCEPTED_FIRST"}]
    for k in range(1, blocks + 1):
        t = start + timedelta(hours=6 * k)
        recs.append({"device_id": "T", "captured_at": t.astimezone(timezone.utc).isoformat(),
                     "consumption": per_block, "status": "ACCEPTED"})
    return recs

# long history: Sep 1 -> Oct 10 12:00; cycle is Oct 1 -> Nov 1 (31 days)
recs = make(datetime(2026, 9, 1, tzinfo=IST), 158, 2.5)
t_last = datetime(2026, 10, 10, 12, tzinfo=IST)
o = project(recs, budget=1500, now=t_last)
assert o["ok"] and o["covers_full_cycle"] and not o["cold_start"] and not o["stale"]
assert abs(o["units_so_far"] - 95) < 0.5, o["units_so_far"]
assert abs(o["projected_units"] - 310) < 1.0, o["projected_units"]
assert o["rf_units"] is not None and o["rf_weight"] == 1.0
assert o["projected_bill"] == bill_for_units(o["projected_units"])

# cold start: only 2 days of data, cycle just began
recs = make(datetime(2026, 10, 1, tzinfo=IST), 8, 2.5)
o = project(recs, now=datetime(2026, 10, 3, tzinfo=IST))
assert o["cold_start"] and o["rf_units"] is None
assert abs(o["projected_units"] - 310) < 1.0, o["projected_units"]

# stale data
o = project(recs, now=datetime(2026, 10, 8, tzinfo=IST))
assert o["stale"]

# too little data
assert project(recs[:1])["ok"] is False

print("all tariff and forecast tests passed")