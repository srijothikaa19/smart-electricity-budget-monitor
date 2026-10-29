import sys, json
from db import get_store
from forecast import update_forecast

out = update_forecast(get_store(), sys.argv[1])
print(json.dumps(out, indent=2, default=str))