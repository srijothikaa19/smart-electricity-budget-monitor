import sys, os
from datetime import datetime, timedelta
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from validator import vote_frames, validate_reading

t0 = datetime(2026, 10, 1, 8, 0)
def last(r): return {"reading": r, "time": t0}
def after(h): return t0 + timedelta(hours=h)

# --- 3-frame voting ---
assert vote_frames(["012345", "012345", "012845"]) == ("012345", "OK")
assert vote_frames(["012345", "012845", None])[1] == "REJECT_NO_CONSENSUS"
assert vote_frames([None, None, None])[1] == "REJECT_NO_VALID_FRAME"

# --- validation ---
assert validate_reading("012345", t0)["status"] == "ACCEPTED_FIRST"

r = validate_reading("012347", after(2), last("012345"))
assert r["status"] == "ACCEPTED" and r["consumption"] == 2

assert validate_reading("012345", after(2), last("012345"))["status"] == "DUPLICATE_NO_CHANGE"
assert validate_reading("013345", after(1), last("012345"))["status"] == "QUARANTINED_JUMP"
assert validate_reading("012300", after(2), last("012345"))["status"] == "REJECT_DECREASE"

r = validate_reading("000005", after(2), last("999990"))
assert r["status"] == "ACCEPTED_ROLLOVER" and r["consumption"] == 15

assert validate_reading("12347", after(2), last("012345"))["status"] == "REJECT_DIGIT_COUNT_CHANGED"
assert validate_reading("012347", t0, last("012345"))["status"] == "REJECT_BAD_TIMESTAMP"
assert validate_reading("01234x", after(2), last("012345"))["status"] == "REJECT_INVALID_READING"

# meter with one decimal digit: 0123450 means 12345.0 kWh
r = validate_reading("0123470", after(2), last("0123450"), decimals=1)
assert r["status"] == "ACCEPTED" and r["consumption"] == 2.0

print("all validator tests passed")