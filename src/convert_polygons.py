import os, glob, shutil, sys

src_root = sys.argv[1]      # e.g. data\raw\ds1
dst_root = sys.argv[2]      # e.g. data\labeled\display_ds1
class_name = "display"

def clamp(v):
    return max(0.0, min(1.0, v))

stats = {"box": 0, "polygon": 0, "skipped": 0, "empty": 0}

for split in ["train", "valid", "test"]:
    img_dir = os.path.join(src_root, split, "images")
    lbl_dir = os.path.join(src_root, split, "labels")
    out_img = os.path.join(dst_root, split, "images")
    out_lbl = os.path.join(dst_root, split, "labels")
    os.makedirs(out_img, exist_ok=True)
    os.makedirs(out_lbl, exist_ok=True)

    for img_path in glob.glob(os.path.join(img_dir, "*")):
        base = os.path.splitext(os.path.basename(img_path))[0]
        lbl_path = os.path.join(lbl_dir, base + ".txt")
        new_lines = []
        if os.path.exists(lbl_path):
            for line in open(lbl_path):
                p = line.split()
                if not p:
                    continue
                vals = [float(x) for x in p[1:]]
                if len(vals) == 4:                      # already a box
                    cx, cy, w, h = vals
                    x1, y1, x2, y2 = cx - w/2, cy - h/2, cx + w/2, cy + h/2
                    stats["box"] += 1
                elif len(vals) >= 6 and len(vals) % 2 == 0:   # polygon
                    xs, ys = vals[0::2], vals[1::2]
                    x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
                    stats["polygon"] += 1
                else:
                    stats["skipped"] += 1
                    continue
                x1, y1, x2, y2 = map(clamp, (x1, y1, x2, y2))
                w, h = x2 - x1, y2 - y1
                if w < 0.01 or h < 0.01:
                    stats["skipped"] += 1
                    continue
                new_lines.append(f"0 {(x1+x2)/2:.6f} {(y1+y2)/2:.6f} {w:.6f} {h:.6f}")
        if not new_lines:
            stats["empty"] += 1
            continue                                    # drop images with no usable label
        shutil.copy(img_path, os.path.join(out_img, os.path.basename(img_path)))
        with open(os.path.join(out_lbl, base + ".txt"), "w") as f:
            f.write("\n".join(new_lines) + "\n")

with open(os.path.join(dst_root, "data.yaml"), "w") as f:
    f.write(f"nc: 1\nnames: ['{class_name}']\n")

print("Done:", stats)