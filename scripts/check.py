"""Sanity checks on data/dataset.js. Usage: python -I scripts/check.py <project_dir>"""
import json, os, sys
src = open(os.path.join(sys.argv[1], "data", "dataset.js"), encoding="utf-8").read()
data = json.loads(src[src.index("=") + 1:].rstrip().rstrip(";"))
Y0 = data["startYear"]

def label(codes):
    d = r = 0
    for c in codes:
        d += c == "D"; r += c == "R"
    net = d - r
    leader = "D" if net > 0 else "R" if net < 0 else None
    holder = codes[-1]
    color = "white" if leader in (None, holder) else ("blue" if leader == "D" else "red")
    return d, r, abs(net), color

# The two examples from the spec.
assert label("R" * 40 + "D" * 10)[2:] == (30, "red"), label("R" * 40 + "D" * 10)
assert label("D" * 10 + "R" * 5 + "D")[2:] == (6, "white")
assert label("D" * 10 + "R" * 5)[2:] == (5, "blue")
print("spec examples OK\n")

print(f"{'st':3} {'D':>4} {'R':>4} {'oth':>4} {'N/vac':>5}  2026 label    holder 2026")
for k, s in sorted(data["states"].items()):
    codes = s["codes"]
    d, r, n, color = label([c for c in codes if c != "-"])
    other = codes.count("O"); vac = codes.count("N")
    print(f"{k:3} {d:4} {r:4} {other:4} {vac:5}  {color:>5} {n:<4}  {codes[-1]}  {s['terms'][s['gov'][-1]]['name']}")

f = data["federal"]
print("\nfederal rows missing data:", [e["year"] for e in f if not all(k in e for k in ("senate", "house", "president"))])
for y in (1856, 1865, 1867, 1881, 1995, 2001, 2002, 2021, 2025, 2026):
    e = f[y - Y0]
    print(y, e["president"]["name"], e["president"]["party"], "S", e["senate"]["majority"], "H", e["house"]["majority"])
