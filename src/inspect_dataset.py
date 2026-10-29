import sys, os, glob, random
from collections import Counter
import yaml, cv2

root = sys.argv[1]
name = os.path.basename(os.path.normpath(root))

with open(os.path.join(root, "data.yaml")) as f:
    cfg = yaml.safe_load(f)
names = cfg["names"]
if isinstance(names, dict):
    names = [names[k] for k in sorted(names)]
print("Classes:", names)

out_dir = os.path.join("docs", "previews", name)
os.makedirs(out_dir, exist_ok=True)

all_imgs = []
for split in ["train", "valid", "test"]:
    imgs = []
    for ext in ("jpg", "jpeg", "png"):
        imgs += glob.glob(os.path.join(root, split, "images", "*." + ext))
    counts = Counter()
    odd = 0
    for lf in glob.glob(os.path.join(root, split, "labels", "*.txt")):
        for line in open(lf):
            p = line.split()
            if not p:
                continue
            if len(p) != 5:
                odd += 1
            counts[int(p[0])] += 1
    print(f"{split}: {len(imgs)} images, {sum(counts.values())} boxes, "
          f"{odd} non-box labels")
    for k in sorted(counts):
        print(f"    {names[k]}: {counts[k]}")
    all_imgs += imgs

random.seed(0)
for path in random.sample(all_imgs, min(12, len(all_imgs))):
    img = cv2.imread(path)
    if img is None:
        continue
    h, w = img.shape[:2]
    lab = path.replace(os.sep + "images" + os.sep, os.sep + "labels" + os.sep)
    lab = os.path.splitext(lab)[0] + ".txt"
    if os.path.exists(lab):
        for line in open(lab):
            p = line.split()
            if len(p) != 5:
                continue
            c, cx, cy, bw, bh = int(p[0]), *map(float, p[1:])
            x1, y1 = int((cx - bw / 2) * w), int((cy - bh / 2) * h)
            x2, y2 = int((cx + bw / 2) * w), int((cy + bh / 2) * h)
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(img, names[c], (x1, max(y1 - 4, 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    cv2.imwrite(os.path.join(out_dir, os.path.basename(path)), img)
print("Previews saved to", out_dir)