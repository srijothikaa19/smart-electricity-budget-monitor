import json, os, sys
from datetime import timedelta
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from forecast import project, cumulative, cum_at, cycle_bounds, _parse
from tariff import bill_for_units

CHECKPOINTS = [5, 10, 15, 20]     # days into the billing cycle
WARMUP_DAYS = 30                  # history required before the first test cycle
METHODS = ["run_rate", "rf", "blend", "last_cycle"]

recs = json.load(open("data/synthetic/SYNTHETIC_readings.json"))
pts = cumulative(recs)
first, last = pts[0][0], pts[-1][0]

# every complete calendar cycle inside the data
cycles, t = [], first
while True:
    s, e = cycle_bounds(t)
    if e > last:
        break
    if s >= first:
        cycles.append((s, e))
    t = e + timedelta(hours=1)

actual = {s: cum_at(pts, e) - cum_at(pts, s) for s, e in cycles}
tests = [(s, e) for s, e in cycles if s >= first + timedelta(days=WARMUP_DAYS)]
if len(tests) < 3:
    sys.exit("too few test cycles; generate more days (set SYN_DAYS=300)")

budget = float(np.median([bill_for_units(actual[s]) for s, _ in tests]))
print(f"SYNTHETIC data | test cycles: {len(tests)} | budget used for alerts: {budget:.0f}")

res = {k: {m: [] for m in METHODS} for k in CHECKPOINTS}
for s, e in tests:
    prev = actual.get(cycle_bounds(s - timedelta(hours=1))[0])
    for k in CHECKPOINTS:
        tk = s + timedelta(days=k)
        sub = [r for r in recs if _parse(r["captured_at"]) <= tk]     # no future data
        o = project(sub, now=tk)
        if not o.get("ok"):
            continue
        preds = {"run_rate": o["run_rate_units"], "rf": o["rf_units"],
                 "blend": o["projected_units"], "last_cycle": prev}
        for m, p in preds.items():
            if p is not None:
                res[k][m].append((p, actual[s]))

def alert_scores(pairs):
    tp = fp = fn = 0
    for p, a in pairs:
        pa, aa = bill_for_units(p) > budget, bill_for_units(a) > budget
        tp += pa and aa
        fp += pa and not aa
        fn += (not pa) and aa
    return tp, fp, fn

print("\nday  method       n   MAE(units)  MAPE%   MAE(bill)   alert TP/FP/FN")
for k in CHECKPOINTS:
    for m in METHODS:
        pairs = res[k][m]
        if not pairs:
            continue
        p = np.array([x for x, _ in pairs]); a = np.array([y for _, y in pairs])
        mae = np.mean(np.abs(p - a)); mape = np.mean(np.abs(p - a) / a) * 100
        bmae = np.mean([abs(bill_for_units(x) - bill_for_units(y)) for x, y in pairs])
        tp, fp, fn = alert_scores(pairs)
        print(f"{k:>3}  {m:<11}{len(pairs):>3}  {mae:>9.2f}  {mape:>6.1f}  {bmae:>9.1f}   {tp}/{fp}/{fn}")