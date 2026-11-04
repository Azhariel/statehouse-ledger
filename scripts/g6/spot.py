"""Spot-check random terms against raw wikitext. Usage: python -I spot.py <json> <wikitext_dir>"""
import json, random, re, sys, os
d = json.load(open(sys.argv[1], encoding="utf-8"))
random.seed(7)
files = {"TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia",
         "WA": "Washington", "WV": "West_Virginia", "WI": "Wisconsin", "WY": "Wyoming"}
for code, s in d.items():
    lines = open(os.path.join(sys.argv[2], files[code] + ".wiki"), encoding="utf-8").read().split("\n")
    for t in random.sample(s["terms"][1:-1], 3):
        print(code, "JSON:", t["name"], t["party_raw"], t["start"], t["end"], t["acting"])
        for i, l in enumerate(lines):
            if "'''[[" in l and t["name"] in l:
                seg = " ".join(lines[i:i + 3])
                seg = re.sub(r"<ref.*?(</ref>|/>)", "", seg)
                seg = re.sub(r"\{\{(sfn|efn)[^{}]*(\{\{[^{}]*\}\}[^{}]*)*\}\}", "", seg)
                print("   RAW:", re.sub(r"\s+", " ", seg)[:420])
