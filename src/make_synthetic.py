import json, math, os, random, sys
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.dirname(__file__))

TZ = timezone(timedelta(hours=5.5))
DEVICE = "SYNTHETIC_meter"
DAYS = int(os.environ.get("SYN_DAYS", "90"))
FRAC = [0.15, 0.25, 0.25, 0.35]        # share of a day's use in each 6-hour block
random.seed(7)

def rec(t, c, status):
    return {"device_id": DEVICE, "captured_at": t.astimezone(timezone.utc).isoformat(),
            "consumption": round(c, 4), "status": status, "synthetic": True}

end_day = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
start = end_day - timedelta(days=DAYS)
recs, truth = [rec(start, 0.0, "ACCEPTED_FIRST")], {}
for k in range(DAYS):
    day = start + timedelta(days=k)
    base = 8.0 * (1.25 if day.weekday() >= 5 else 1.0)
    base *= 1 + 0.25 * math.sin(2 * math.pi * (day.timetuple().tm_yday - 150) / 365)
    daily = max(1.0, base * random.lognormvariate(0, 0.15))
    truth[day.date().isoformat()] = round(daily, 3)
    for j, f in enumerate(FRAC):
        recs.append(rec(day + timedelta(hours=6 * (j + 1)), daily * f, "ACCEPTED"))

os.makedirs("data/synthetic", exist_ok=True)
json.dump(recs, open("data/synthetic/SYNTHETIC_readings.json", "w"))
json.dump(truth, open("data/synthetic/SYNTHETIC_daily_truth.json", "w"))
print("SYNTHETIC records:", len(recs))

if "--to-store" in sys.argv:
    from db import get_store
    store = get_store()
    for r in recs:
        store.save_reading(r)
    print("written to backend", os.environ.get("DB_BACKEND", "local"))