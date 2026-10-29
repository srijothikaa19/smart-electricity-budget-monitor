import os, glob, shutil, random, yaml, re, sys

SOURCES = sys.argv[1:] or [r"data\raw\ds5", r"data\raw\ds6"]
DST = r"data\labeled\digits"
DIGITS = [str(i) for i in range(10)]
random.seed(42)

def load_names(root):
    with open(os.path.join(root, "data.yaml")) as f:
        n = yaml.safe_load(f)["names"]
    return [n[k] for k in sorted(n)] if isinstance(n, dict) else n

items = []      # (group, img_path, [yolo lines])
dropped = 0
for root in SOURCES:
    tag = os.path.basename(os.path.normpath(root))
    names = load_names(root)
    for split in ["train", "valid", "test"]:
        for img in glob.glob(os.path.join(root, split, "images", "*")):
            stem = os.path.splitext(os.path.basename(img))[0]
            lbl = os.path.join(root, split, "labels", stem + ".txt")
            if not os.path.exists(lbl):
                continue
            lines = []
            for line in open(lbl):
                p = line.split()
                if len(p) != 5:
                    dropped += 1
                    continue
                name = names[int(p[0])]
                if name not in DIGITS:
                    dropped += 1
                    continue
                lines.append(f"{DIGITS.index(name)} " + " ".join(p[1:]))
            if lines:
                group = tag + "_" + re.split(r"\.rf\.", stem)[0]
                items.append((group, img, lines))

groups = sorted(set(g for g, _, _ in items))
random.shuffle(groups)
n = len(groups)
cut1, cut2 = int(0.70 * n), int(0.85 * n)
split_of = {g: ("train" if i < cut1 else "valid" if i < cut2 else "test")
            for i, g in enumerate(groups)}

if os.path.exists(DST):
    shutil.rmtree(DST)
counts = {"train": 0, "valid": 0, "test": 0}
for g, img, lines in items:
    s = split_of[g]
    ext = os.path.splitext(img)[1]
    name = f"{os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(img))))}_{counts[s]:05d}"
    os.makedirs(os.path.join(DST, s, "images"), exist_ok=True)
    os.makedirs(os.path.join(DST, s, "labels"), exist_ok=True)
    shutil.copy(img, os.path.join(DST, s, "images", name + ext))
    with open(os.path.join(DST, s, "labels", name + ".txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    counts[s] += 1

with open(os.path.join(DST, "data.yaml"), "w") as f:
    f.write("nc: 10\nnames: ['0','1','2','3','4','5','6','7','8','9']\n")

print("images:", len(items), " original photos (groups):", n)
print("split counts:", counts, " dropped non-digit labels:", dropped)