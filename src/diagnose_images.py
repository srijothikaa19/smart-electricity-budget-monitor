import csv, os, sys
import cv2
from ultralytics import YOLO
import settings

folder = sys.argv[1] if len(sys.argv) > 1 else r"data\own_photos"
dm, gm = YOLO("models/display.pt"), YOLO("models/digits.pt")
out = os.path.join("docs", "diag")
os.makedirs(out, exist_ok=True)

for r in csv.DictReader(open(os.path.join(folder, "truth.csv"))):
    name = r["filename"]
    img = cv2.imread(os.path.join(folder, name))
    if img is None:
        print(name, "UNREADABLE"); continue
    H, W = img.shape[:2]
    d = dm.predict(img, conf=0.10, device=settings.DEVICE, verbose=False)[0]
    boxes = sorted(zip(d.boxes.conf.tolist(), d.boxes.xyxy.tolist()), reverse=True)[:3]
    line = f"{name[:40]:40} true={r['true_reading']:>8} img={W}x{H}"
    if not boxes:
        print(line, "| display: none even at conf 0.10"); continue
    desc = [f"conf {c:.2f} area {((b[2]-b[0])*(b[3]-b[1]))/(W*H):.2f}" for c, b in boxes]
    c, b = boxes[0]
    x1, y1, x2, y2 = map(int, b)
    pad = int(0.08 * (x2 - x1)), int(0.08 * (y2 - y1))
    crop = img[max(0, y1-pad[1]):min(H, y2+pad[1]), max(0, x1-pad[0]):min(W, x2+pad[0])]
    g = gm.predict(crop, conf=0.25, device=settings.DEVICE, verbose=False)[0]
    digs = sorted(zip(g.boxes.xyxy[:, 0].tolist(), g.boxes.cls.tolist(), g.boxes.conf.tolist()))
    s = "".join(gm.names[int(k)] for _, k, _ in digs)
    print(line, "| display:", "; ".join(desc), "| digits:", s or "-")
    cv2.imwrite(os.path.join(out, os.path.splitext(name)[0] + "_crop.jpg"), g.plot())
    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 3)
    cv2.imwrite(os.path.join(out, os.path.splitext(name)[0] + "_display.jpg"), img)