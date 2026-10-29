import cv2
from ultralytics import YOLO
import settings

# --- settings (move to config\config.yaml later) ---
DEVICE = settings.DEVICE   # "0" for your GPU, "cpu" otherwise (from .env)
DISPLAY_CONF = 0.5         # min confidence for the display box
MIN_DISPLAY_AREA = 0.15    # display must cover at least this fraction of the image
DIGIT_CONF = 0.6           # every digit must be at least this confident
PAD = 0.08                 # padding around the display crop
MIN_DIGITS = 4             # allowed digit count range
MAX_DIGITS = 5
LOCKED_DIGITS = None       # set a number to force one exact count for a known meter
GAP_FACTOR = 1.6           # reject if a gap is bigger than 1.6x the typical spacing
SIZE_TOL = 0.35            # digits must have similar height (+-35%)

display_model = YOLO("models/display.pt")
digit_model = YOLO("models/digits.pt")

def crop_display(img):
    r = display_model.predict(img, conf=DISPLAY_CONF, device=DEVICE, verbose=False)[0]
    if len(r.boxes) == 0:
        return None, "REJECT_NO_DISPLAY"
    i = int(r.boxes.conf.argmax())          # keep the best box only
    x1, y1, x2, y2 = r.boxes.xyxy[i].tolist()
    H, W = img.shape[:2]
    if (x2 - x1) * (y2 - y1) < MIN_DISPLAY_AREA * W * H:
        return None, "REJECT_DISPLAY_TOO_SMALL"
    pw, ph = (x2 - x1) * PAD, (y2 - y1) * PAD
    x1, y1 = max(0, int(x1 - pw)), max(0, int(y1 - ph))
    x2, y2 = min(W, int(x2 + pw)), min(H, int(y2 + ph))
    return img[y1:y2, x1:x2], "OK"

def read_digits(crop):
    r = digit_model.predict(crop, conf=0.25, device=DEVICE, verbose=False)[0]
    dets = []
    for b, c, k in zip(r.boxes.xyxy.tolist(), r.boxes.conf.tolist(),
                       r.boxes.cls.tolist()):
        dets.append({"x1": b[0], "y1": b[1], "x2": b[2], "y2": b[3],
                     "conf": c, "digit": digit_model.names[int(k)]})
    dets.sort(key=lambda d: d["x1"])

    kept = []                               # drop duplicate overlapping boxes
    for d in dets:
        if kept:
            p = kept[-1]
            overlap = min(p["x2"], d["x2"]) - max(p["x1"], d["x1"])
            if overlap > 0.5 * min(p["x2"] - p["x1"], d["x2"] - d["x1"]):
                if d["conf"] > p["conf"]:
                    kept[-1] = d
                continue
        kept.append(d)

    n = len(kept)
    if LOCKED_DIGITS is not None:
        if n != LOCKED_DIGITS:
            return None, 0.0, f"REJECT_DIGIT_COUNT_{n}", n
    elif not (MIN_DIGITS <= n <= MAX_DIGITS):
        return None, 0.0, f"REJECT_DIGIT_COUNT_{n}", n

    hs = sorted(d["y2"] - d["y1"] for d in kept)
    med_h = hs[len(hs) // 2]
    for d in kept:
        if abs((d["y2"] - d["y1"]) - med_h) > SIZE_TOL * med_h:
            return None, 0.0, "REJECT_UNEVEN_DIGIT_SIZE", n
    ycs = sorted((d["y1"] + d["y2"]) / 2 for d in kept)
    if ycs[-1] - ycs[0] > 0.6 * med_h:
        return None, 0.0, "REJECT_NOT_ONE_ROW", n

    xcs = [(d["x1"] + d["x2"]) / 2 for d in kept]
    gaps = [b - a for a, b in zip(xcs, xcs[1:])]
    if gaps:
        med_gap = sorted(gaps)[len(gaps) // 2]
        if max(gaps) > GAP_FACTOR * med_gap:
            return None, 0.0, "REJECT_GAP_MISSING_DIGIT", n

    min_conf = min(d["conf"] for d in kept)
    if min_conf < DIGIT_CONF:
        return None, min_conf, "REJECT_LOW_CONFIDENCE", n
    return "".join(d["digit"] for d in kept), min_conf, "OK", n

def read_image(img):
    crop, status = crop_display(img)
    if crop is None:
        return {"reading": None, "status": status, "min_conf": 0.0, "n_digits": 0}
    reading, conf, status, n = read_digits(crop)
    return {"reading": reading, "status": status, "min_conf": conf, "n_digits": n}

def read_meter(path):
    img = cv2.imread(path)
    if img is None:
        return {"reading": None, "status": "REJECT_UNREADABLE_FILE",
                "min_conf": 0.0, "n_digits": 0}
    return read_image(img)

if __name__ == "__main__":
    import sys
    print(read_meter(sys.argv[1]))