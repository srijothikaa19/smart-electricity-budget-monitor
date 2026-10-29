from collections import Counter

# --- settings (move to config\config.yaml later) ---
MAX_KW = 10.0              # highest plausible average load for this home
JUMP_TOLERANCE = 1.0       # extra units allowed on top of MAX_KW * hours
ROLLOVER_HIGH = 0.90       # last reading must be in the top 10% of the meter's range
ROLLOVER_LOW = 0.10        # new reading must be in the bottom 10%
MIN_VOTES = 2              # frames that must agree (out of 3)

def vote_frames(readings, min_votes=MIN_VOTES):
    """readings: list of strings (or None) from the 3 frames of one capture."""
    valid = [r for r in readings if r]
    if not valid:
        return None, "REJECT_NO_VALID_FRAME"
    top = Counter(valid).most_common(2)
    if top[0][1] < min_votes or (len(top) > 1 and top[0][1] == top[1][1]):
        return None, "REJECT_NO_CONSENSUS"
    return top[0][0], "OK"

def _units(reading, decimals):
    return int(reading) / (10 ** decimals)

def _result(status, value=None, consumption=0.0):
    return {"status": status, "value": value, "consumption": consumption}

def validate_reading(new_reading, new_time, last=None, decimals=0, max_kw=MAX_KW):
    """
    new_reading: digit string, e.g. "012345"
    new_time:    datetime of the capture
    last:        None, or {"reading": "012340", "time": datetime} (last ACCEPTED reading)
    decimals:    how many of the digits are after the decimal point (meter dependent)
    """
    if not new_reading or not new_reading.isdigit():
        return _result("REJECT_INVALID_READING")

    new_v = _units(new_reading, decimals)
    if last is None:
        return _result("ACCEPTED_FIRST", new_v, 0.0)

    if len(new_reading) != len(last["reading"]):
        return _result("REJECT_DIGIT_COUNT_CHANGED")   # misread, or meter replaced: ask the user

    hours = (new_time - last["time"]).total_seconds() / 3600
    if hours <= 0:
        return _result("REJECT_BAD_TIMESTAMP")

    last_v = _units(last["reading"], decimals)
    n = len(new_reading)
    max_v = (10 ** n - 1) / (10 ** decimals)
    modulus = (10 ** n) / (10 ** decimals)
    limit = max_kw * hours + JUMP_TOLERANCE

    if new_v == last_v:
        return _result("DUPLICATE_NO_CHANGE", new_v, 0.0)

    if new_v > last_v:
        delta = round(new_v - last_v, 3)
        if delta > limit:
            return _result("QUARANTINED_JUMP", new_v, delta)
        return _result("ACCEPTED", new_v, delta)

    # new_v < last_v: only a genuine rollover is allowed
    if last_v >= ROLLOVER_HIGH * max_v and new_v <= ROLLOVER_LOW * max_v:
        delta = round((modulus - last_v) + new_v, 3)
        if delta > limit:
            return _result("QUARANTINED_JUMP", new_v, delta)
        return _result("ACCEPTED_ROLLOVER", new_v, delta)
    return _result("REJECT_DECREASE")