import os
from datetime import datetime, timedelta, timezone
import numpy as np
from tariff import bill_for_units, units_for_budget, budget_status

TZ = timezone(timedelta(hours=5.5))     # IST. Change for another region.
MIN_RF_DAYS = 14        # need this many complete days before using the Random Forest
BLEND_N = int(os.environ.get("BLEND_N", "30"))       # RF weight w = min(1, history_days / BLEND_N)
STALE_HOURS = 48
OK_STATUSES = ("ACCEPTED", "ACCEPTED_FIRST", "ACCEPTED_ROLLOVER", "DUPLICATE_NO_CHANGE")

def _parse(ts):
    dt = datetime.fromisoformat(ts)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

def cumulative(readings):
    """Running total of kWh from accepted readings (uses each record's consumption,
    so rollovers are handled by the validator, not here)."""
    rows = sorted((r for r in readings if r.get("status") in OK_STATUSES),
                  key=lambda r: _parse(r["captured_at"]))
    pts, cum = [], 0.0
    for r in rows:
        cum += float(r.get("consumption") or 0.0)
        pts.append((_parse(r["captured_at"]), cum))
    return pts

def cum_at(pts, t):
    if not pts or t <= pts[0][0]:
        return 0.0
    if t >= pts[-1][0]:
        return pts[-1][1]
    for (t0, c0), (t1, c1) in zip(pts, pts[1:]):
        if t0 <= t <= t1:
            return c1 if t1 == t0 else c0 + (c1 - c0) * ((t - t0) / (t1 - t0))
    return pts[-1][1]

def daily_series(pts):
    """kWh per complete local day. Assumes steady use between two readings."""
    if len(pts) < 2:
        return []
    first = pts[0][0].astimezone(TZ)
    day = (first + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    last_t, out = pts[-1][0], []
    while day + timedelta(days=1) <= last_t:
        nxt = day + timedelta(days=1)
        out.append((day.date(), max(0.0, cum_at(pts, nxt) - cum_at(pts, day))))
        day = nxt
    return out

def cycle_bounds(t, start_day=1, months=1):
    tl = t.astimezone(TZ)
    start_day = max(1, min(28, int(start_day)))
    y, m = tl.year, tl.month
    if tl.day < start_day:
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    start = datetime(y, m, start_day, tzinfo=TZ)
    em = m - 1 + months
    end = datetime(y + em // 12, em % 12 + 1, start_day, tzinfo=TZ)
    return start, end

def run_rate(so_far, elapsed_days, remaining_days, recent_daily):
    rate = so_far / elapsed_days
    proj = so_far + rate * remaining_days
    sd = float(np.std(recent_daily)) if len(recent_daily) >= 7 else 0.5 * rate
    low = so_far + max(0.0, rate - sd) * remaining_days     # rough band, not a
    high = so_far + (rate + sd) * remaining_days            # statistical interval
    return proj, low, high

def _features(hist, d):
    return [d.weekday(), d.day, hist[-1], hist[-2], hist[-3], hist[-7],
            float(np.mean(hist[-3:])), float(np.mean(hist[-7:]))]

def rf_remaining(daily, future_dates, seed=0):
    from sklearn.ensemble import RandomForestRegressor
    vals = [v for _, v in daily]
    X = [_features(vals[:i], daily[i][0]) for i in range(7, len(vals))]
    y = vals[7:]
    if len(X) < 7:
        return None
    model = RandomForestRegressor(n_estimators=200, min_samples_leaf=2, random_state=seed)
    model.fit(X, y)
    hist, total = list(vals), 0.0
    for d in future_dates:                                   # recursive prediction
        p = float(model.predict([_features(hist, d)])[0])
        hist.append(p)
        total += p
    return total

def project(readings, tariff=None, budget=None, start_day=1, months=1, now=None):
    now = now or datetime.now(timezone.utc)
    pts = cumulative(readings)
    if len(pts) < 2:
        return {"ok": False, "reason": "NEED_AT_LEAST_2_READINGS"}
    t_last = pts[-1][0]
    start, end = cycle_bounds(t_last, start_day, months)
    eff_start = max(start, pts[0][0])
    covers_full_cycle = pts[0][0] <= start
    so_far = cum_at(pts, t_last) - cum_at(pts, eff_start)
    elapsed = (t_last - eff_start).total_seconds() / 86400
    remaining = max(0.0, (end - t_last).total_seconds() / 86400)
    if elapsed <= 0:
        return {"ok": False, "reason": "NO_TIME_ELAPSED"}

    daily = daily_series(pts)
    recent = [v for _, v in daily][-14:]
    rr, rr_low, rr_high = run_rate(so_far, elapsed, remaining, recent)

    rf_total, w = None, 0.0
    if len(daily) >= MIN_RF_DAYS:
        d, end_d = t_last.astimezone(TZ).date(), end.astimezone(TZ).date()
        dates = []
        while d < end_d:
            dates.append(d)
            d += timedelta(days=1)
        today_start = datetime.combine(t_last.astimezone(TZ).date(),
                                       datetime.min.time(), tzinfo=TZ)
        used_today = cum_at(pts, t_last) - cum_at(pts, today_start)
        r = rf_remaining(daily, dates)
        if r is not None:
            rf_total = so_far + max(0.0, r - used_today)
            w = min(1.0, len(daily) / BLEND_N)

    proj = rr if rf_total is None else w * rf_total + (1 - w) * rr
    low, high = min(rr_low, proj), max(rr_high, proj)

    bill_now, bill_proj = bill_for_units(so_far, tariff), bill_for_units(proj, tariff)
    bill_low, bill_high = bill_for_units(low, tariff), bill_for_units(high, tariff)
    stale = (now - t_last) > timedelta(hours=STALE_HOURS)
    cold = elapsed < 3
    out = {
        "ok": True, "cycle_start": start.isoformat(), "cycle_end": end.isoformat(),
        "last_reading_time": t_last.isoformat(),
        "units_so_far": round(so_far, 2), "projected_units": round(proj, 2),
        "units_low": round(low, 2), "units_high": round(high, 2),
        "bill_so_far": bill_now, "projected_bill": bill_proj,
        "bill_low": bill_low, "bill_high": bill_high,
        "run_rate_units": round(rr, 2),
        "rf_units": None if rf_total is None else round(rf_total, 2),
        "rf_weight": round(w, 2), "history_days": len(daily),
        "days_elapsed": round(elapsed, 2), "days_remaining": round(remaining, 2),
        "covers_full_cycle": covers_full_cycle, "cold_start": cold, "stale": stale,
        "budget": budget,
    }
    out["daily"] = [{"d": str(d), "kwh": round(v, 2)} for d, v in daily[-60:]]
    if budget is not None:
        left = units_for_budget(budget, tariff) - so_far
        out["daily_allowance_units"] = round(max(0.0, left) / remaining, 2) if remaining > 0 else 0.0
    out["alert"] = budget_status(budget, bill_now, bill_proj, bill_high, stale, cold)
    return out

def update_forecast(store, device_id, now=None):
    dev = store.get_device(device_id)
    readings = store.list_where("readings", "device_id", device_id, 5000)
    out = project(readings, tariff=dev.get("tariff"), budget=dev.get("budget"),
                  start_day=int(dev.get("cycle_start_day", 1)),
                  months=int(dev.get("cycle_months", 1)), now=now)
    out["device_id"] = device_id
    out["updated_at"] = datetime.now(timezone.utc).isoformat()
    store.put("forecasts", device_id, out)
    return out