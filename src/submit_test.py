import argparse, base64, sys
from datetime import datetime, timezone
import cv2
from db import get_store

ap = argparse.ArgumentParser()
ap.add_argument("images", nargs="+")
ap.add_argument("--device", default="meter1")
ap.add_argument("--at", help="UTC time, e.g. 2026-10-28T10:00:00 (for testing)")
a = ap.parse_args()

paths = a.images
if len(paths) == 1:
    print("NOTE: one image repeated 3 times. This is for testing only, not real voting.")
    paths = paths * 3

frames = []
for p in paths[:3]:
    img = cv2.imread(p)
    if img is None:
        sys.exit("cannot read " + p)
    h, w = img.shape[:2]
    if w > 640:
        img = cv2.resize(img, (640, int(h * 640 / w)))
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 70])
    frames.append(base64.b64encode(buf.tobytes()).decode())

total = sum(len(f) for f in frames)
print("payload size:", total, "bytes")
if total > 900_000:
    sys.exit("too big for one Firestore document (limit about 1 MiB)")

at = None
if a.at:
    dt = datetime.fromisoformat(a.at)
    at = (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).isoformat()
print("capture id:", get_store().add_capture(a.device, frames, at))