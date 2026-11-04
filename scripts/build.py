"""Merge raw governor/congress data into data/dataset.js for index.html.

Usage: python -I scripts/build.py <project_dir>

A year counts for whoever held office on the reference date (July 1),
i.e. whoever held it for most of the year.
"""
import glob
import json
import os
import re
import sys
from collections import Counter
from datetime import date

START_YEAR = 1856
END_YEAR = 2026
REF_MONTH, REF_DAY = 7, 1

# Exact party_raw overrides, applied before the generic rules below.
# Keys are lowercased with dashes normalized to "-".
PARTY_OVERRIDES = {
    # No party: vacancies, military rule, presidential provisional appointees.
    "none": "N",
    "nonpartisan": "N",
    "non-partisan": "N",
    "provisional governor appointed by president": "N",
    # Reconstruction-era names of the Southern Democratic parties.
    "conservative": "D",
    "citizens ticket": "D",
    "democratic-farmer-labor": "D",
    # Civil War Union coalitions were Republican-led.
    "national union": "R",
    "union": "R",
    "unconditional union": "R",
    "liberal republican": "O",
    "silver republican": "O",
    "democratic-republican": "O",
}

# Per-state exceptions, checked before PARTY_OVERRIDES.
STATE_PARTY_OVERRIDES = {
    # Kentucky's Unionists were ex-Whigs and Union Democrats opposed to Lincoln's Republicans.
    ("KY", "union"): "O",
}

# Ratification dates for original states whose raw file left "admitted" empty.
ADMITTED_FALLBACK = {"NH": "1788-06-21", "NJ": "1787-12-18", "NY": "1788-07-26", "NC": "1789-11-21"}

# Postal code -> FIPS, used by the map (us-atlas ids are FIPS).
FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08", "CT": "09",
    "DE": "10", "FL": "12", "GA": "13", "HI": "15", "ID": "16", "IL": "17", "IN": "18",
    "IA": "19", "KS": "20", "KY": "21", "LA": "22", "ME": "23", "MD": "24", "MA": "25",
    "MI": "26", "MN": "27", "MS": "28", "MO": "29", "MT": "30", "NE": "31", "NV": "32",
    "NH": "33", "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39",
    "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46", "TN": "47",
    "TX": "48", "UT": "49", "VT": "50", "VA": "51", "WA": "53", "WV": "54", "WI": "55",
    "WY": "56",
}


def norm_key(raw):
    return " ".join(raw.lower().replace("–", "-").replace("—", "-").split())


def party_code(raw, state=None):
    """Map a Wikipedia party label to D, R, O (other) or N (no party / vacant)."""
    if not raw:
        return "N"
    key = norm_key(raw)
    if (state, key) in STATE_PARTY_OVERRIDES:
        return STATE_PARTY_OVERRIDES[(state, key)]
    if key in PARTY_OVERRIDES:
        return PARTY_OVERRIDES[key]
    has_d = "democrat" in key
    has_r = "republican" in key
    if has_d and not has_r:
        return "D"
    if has_r and not has_d:
        return "R"
    return "O"


def parse_date(s):
    return date.fromisoformat(s) if s else None


def ref_date(year):
    return date(year, REF_MONTH, REF_DAY)


def term_at(terms, d):
    """Index of the term in office on date d (latest start wins on overlaps)."""
    found = None
    for i, t in enumerate(terms):
        start, end = parse_date(t["start"]), parse_date(t["end"])
        if start <= d and (end is None or end > d):
            found = i
    return found


def build_states(raw_dir, party_counts):
    states = {}
    for path in sorted(glob.glob(os.path.join(raw_dir, "governors_g*.json"))):
        with open(path, encoding="utf-8") as f:
            states.update(json.load(f))

    out = {}
    for code in sorted(states):
        s = states[code]
        terms = s["terms"]
        s["admitted"] = s.get("admitted") or ADMITTED_FALLBACK[code]
        admitted = parse_date(s["admitted"])
        codes, gov_idx = [], []
        for year in range(START_YEAR, END_YEAR + 1):
            d = ref_date(year)
            if admitted > d:
                codes.append("-")
                gov_idx.append(-1)
                continue
            i = term_at(terms, d)
            if i is None:
                codes.append("N")
                gov_idx.append(-1)
            else:
                codes.append(party_code(terms[i]["party_raw"], code))
                gov_idx.append(i)
        for t in terms:
            party_counts[(t["party_raw"], party_code(t["party_raw"], code))] += 1
        out[code] = {
            "name": s["state_name"],
            "fips": FIPS[code],
            "admitted": s["admitted"],
            "source": s.get("source"),
            "codes": "".join(codes),
            "gov": gov_idx,
            "terms": [
                {
                    "name": t["name"],
                    "party": party_code(t["party_raw"], code),
                    "party_raw": t["party_raw"],
                    "start": t["start"],
                    "end": t["end"],
                    "acting": t.get("acting", False),
                }
                for t in terms
            ],
            "legislature": None,
        }
    add_legislature(raw_dir, out)
    return out


def clean_seats(text):
    text = re.sub(r"<ref.*?(</ref>|/>)|<!--.*?-->|\{\{efn.*?\}\}|\{\{efn.*$|&nbsp;", " ", text or "", flags=re.I | re.S)
    text = re.sub(r"<br\s*/?>", " ", text)
    text = re.sub(r"\[\[(?:[^]|]*\|)?([^]]*)\]\]|'{2,}|\{\{[^}]*\}\}", r"\1", text)
    return " ".join(text.split())[:40]


def two_of_three(gov, sen, house):
    """D/R if a party holds 2 of governor, Senate, House; S if split.
    Falls back to the governor when the legislature is nonpartisan or unknown."""
    if sen in ("N", "?") and house in ("N", "?"):
        return gov
    votes = [gov, sen, house]
    if votes.count("D") >= 2:
        return "D"
    if votes.count("R") >= 2:
        return "R"
    return "S"


def add_legislature(raw_dir, states):
    """Attach state Senate/House majorities (D/R/O/T/N/?) and the 2-of-3 codes."""
    path = os.path.join(raw_dir, "legislature.json")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        leg = json.load(f)
    for code, s in states.items():
        sen, house, sen_txt, house_txt, codes2 = [], [], [], [], []
        for i, year in enumerate(range(START_YEAR, END_YEAR + 1)):
            row = leg.get(code, {}).get(str(year), {})
            if "senate" not in row and "unicameral" in row:
                row = {"senate": row["unicameral"], "house": row["unicameral"]}
            gov = s["codes"][i]
            if gov == "-":
                sen.append("-"); house.append("-"); sen_txt.append(""); house_txt.append(""); codes2.append("-")
                continue
            if code == "NE" and year >= 1937:
                row = {k: {"code": "N", "text": "nonpartisan unicameral"} for k in ("senate", "house")}
            sc = (row.get("senate") or {}).get("code") or "?"
            hc = (row.get("house") or {}).get("code") or "?"
            sen.append(sc); house.append(hc)
            sen_txt.append(clean_seats((row.get("senate") or {}).get("text")))
            house_txt.append(clean_seats((row.get("house") or {}).get("text")))
            codes2.append(two_of_three(gov, sc, hc))
        s["legislature"] = {"senate": "".join(sen), "house": "".join(house), "senate_seats": sen_txt, "house_seats": house_txt}
        s["codes2"] = "".join(codes2)


def build_federal(raw_dir, party_counts):
    with open(os.path.join(raw_dir, "congress.json"), encoding="utf-8") as f:
        c = json.load(f)
    congresses = c["congresses"]
    presidents = c["presidents"]

    years = []
    for year in range(START_YEAR, END_YEAR + 1):
        d = ref_date(year)
        cong = next(
            (x for x in congresses if parse_date(x["start"]) <= d < parse_date(x["end"])),
            None,
        )
        entry = {"year": year}
        if cong:
            entry["congress"] = cong["number"]
            for chamber in ("senate", "house"):
                ch = cong[chamber]
                majority = ch["majority"]
                for change in cong.get("changes", []):
                    if change.get("chamber", chamber) == chamber and parse_date(change["date"]) <= d:
                        majority = change.get("majority", majority)
                entry[chamber] = {
                    "majority": majority,
                    "majority_raw": ch.get("majority_raw"),
                    "D": ch.get("D"),
                    "R": ch.get("R"),
                    "O": ch.get("O"),
                }
        pres_i = term_at(presidents, d)
        if pres_i is not None:
            p = presidents[pres_i]
            code = "O" if p["name"] == "Andrew Johnson" else party_code(p["party_raw"])  # Democrat on the National Union ticket
            party_counts[(p["party_raw"], party_code(p["party_raw"]))] += 1
            entry["president"] = {"name": p["name"], "party": code, "party_raw": p["party_raw"]}
        years.append(entry)
    return years


def main():
    project = sys.argv[1]
    raw_dir = os.path.join(project, "data", "raw")
    party_counts = Counter()
    data = {
        "startYear": START_YEAR,
        "endYear": END_YEAR,
        "refDate": f"{REF_MONTH:02d}-{REF_DAY:02d}",
        "states": build_states(raw_dir, party_counts),
        "federal": build_federal(raw_dir, party_counts),
    }

    with open(os.path.join(project, "data", "governors.json"), "w", encoding="utf-8") as f:
        json.dump({k: {kk: v[kk] for kk in ("name", "admitted", "source", "terms")} for k, v in data["states"].items()},
                  f, ensure_ascii=False, indent=1)
    # A .js file (not .json) so index.html works straight from file:// without fetch/CORS issues.
    with open(os.path.join(project, "data", "dataset.js"), "w", encoding="utf-8") as f:
        f.write("window.GOV_DATA = ")
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")

    print(f"states: {len(data['states'])}")
    print("party_raw -> code (term count):")
    for (raw, code), n in sorted(party_counts.items(), key=lambda kv: (kv[0][1], -kv[1])):
        print(f"  {code}  {n:4d}  {raw}")


if __name__ == "__main__":
    main()
