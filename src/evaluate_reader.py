import csv, os, sys
from read_meter import read_meter

folder = sys.argv[1] if len(sys.argv) > 1 else r"data\own_photos"
rows = list(csv.DictReader(open(os.path.join(folder, "truth.csv"))))

exact = rejected = wrong = 0
for r in rows:
    out = read_meter(os.path.join(folder, r["filename"]))
    if out["reading"] is None:
        rejected += 1
        tag = "REJECTED " + out["status"]
    elif out["reading"] == r["true_reading"]:
        exact += 1
        tag = "OK"
    else:
        wrong += 1
        tag = "WRONG"
    print(f'{r["filename"]:25} true={r["true_reading"]} got={out["reading"]} {tag}')

n = len(rows)
accepted = exact + wrong
print(f"\nimages: {n}")
print(f"exact match (of all):        {exact}/{n}")
print(f"rejected:                    {rejected}/{n}")
print(f"wrong readings ACCEPTED:     {wrong}/{n}   <-- push this toward 0")
if accepted:
    print(f"accuracy on accepted:        {exact}/{accepted}")