import sys
from db import get_store
STR_KEYS = {"owner_uid"}
INT_KEYS = {"decimals", "cycle_start_day", "cycle_months"}
device, pairs = sys.argv[1], sys.argv[2:]
fields = {}
for p in pairs:
    k, v = p.split("=", 1)
    fields[k] = v if k in STR_KEYS else int(v) if k in INT_KEYS else float(v)
get_store().update_device(device, **fields)
print("updated", device, fields)