import base64, sys, time, traceback
from forecast import update_forecast
from datetime import datetime
import cv2, numpy as np
import settings
from db import get_store, utcnow_iso
from read_meter import read_image
from validator import vote_frames, validate_reading

def decode(b64):
    arr = np.frombuffer(base64.b64decode(b64), np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)

def process_capture(store, cap):
    device_id = cap["device_id"]
    t = datetime.fromisoformat(cap["captured_at"])
    results = []
    for b64 in cap["frames"]:
        img = decode(b64)
        results.append(read_image(img) if img is not None else
                       {"reading": None, "status": "REJECT_UNREADABLE_FILE",
                        "min_conf": 0.0, "n_digits": 0})
    readings = [r["reading"] for r in results]
    base = {"device_id": device_id, "capture_id": cap["_id"],
            "captured_at": cap["captured_at"], "processed_at": utcnow_iso(),
            "frame_readings": readings,
            "frame_statuses": [r["status"] for r in results]}

    voted, vstatus = vote_frames(readings)
    if voted is None:
        store.save_rejection({**base, "status": vstatus})
        return vstatus

    dev = store.get_device(device_id)
    res = validate_reading(voted, t, store.last_accepted(device_id),
                           decimals=int(dev["decimals"]), max_kw=float(dev["max_kw"]))
    min_conf = min(r["min_conf"] for r in results if r["reading"] == voted)
    rec = {**base, "reading": voted, "value": res["value"],
           "consumption": res["consumption"], "min_conf": round(min_conf, 3),
           "status": res["status"]}

    if res["status"].startswith("ACCEPTED") or res["status"] == "DUPLICATE_NO_CHANGE":
        store.save_reading(rec)
        store.update_device(device_id, last_reading=voted, last_time=cap["captured_at"])
        try:
            update_forecast(store, device_id)
        except Exception:
            traceback.print_exc()          # a forecast error must not fail the capture
    else:
        store.save_rejection(rec)          # rejected or quarantined: not used
    return res["status"]

def main():
    store = get_store()
    once = "--once" in sys.argv
    print("worker started, backend:", settings.DB_BACKEND, " device:", settings.DEVICE)
    while True:
        for cap in store.new_captures():
            try:
                status = process_capture(store, cap)
                store.finish_capture(cap["_id"], "done", status)
                print(cap["device_id"], cap["captured_at"], "->", status)
            except Exception as e:
                traceback.print_exc()
                store.finish_capture(cap["_id"], "error", str(e))
        for dev in store.list_where("devices", "forecast_dirty", True, 20):
            try:
                update_forecast(store, dev["_id"])
                store.update_device(dev["_id"], forecast_dirty=False)
            except Exception:
                traceback.print_exc()            
        if once:
            break
        time.sleep(settings.POLL_SECONDS)

if __name__ == "__main__":
    main()