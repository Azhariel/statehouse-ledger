"""Build governors_g3.json from the downloaded wikitext.

Usage: python -I build.py <wikitext_dir> <output_json>
"""
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("g3parse", os.path.join(HERE, "parse.py"))
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)

STATES = {
    "LA": ("Louisiana", "1812-04-30"),
    "ME": ("Maine", "1820-03-15"),
    "MD": ("Maryland", "1788-04-28"),
    "MA": ("Massachusetts", "1788-02-06"),
    "MI": ("Michigan", "1837-01-26"),
    "MN": ("Minnesota", "1858-05-11"),
    "MS": ("Mississippi", "1817-12-10"),
    "MO": ("Missouri", "1821-08-10"),
}

PARTY_FIX = {
    "Democratic- Farmer-Labor": "Democratic–Farmer–Labor",
    "Farmer-Labor": "Farmer–Labor",
    "Independent- Republican": "Independent-Republican",
    "Reform/ Independence": "Reform/Independence",
}

NO_PARTY_LABELS = {
    "Military governor",
    "Appointed by military occupation",
    "Provisional governor appointed by President",
    "Provisional governor appointed by military occupation",
}


def parse_rows(path):
    raw = open(path, encoding="utf-8").read()
    rows = re.split(r"\n\|-[^\n]*", raw)
    out = []
    cur = None
    for row in rows:
        row = P.clean(row)
        cells = []
        for l in row.split("\n"):
            if not (l.startswith("|") or l.startswith("!")):
                continue
            if l.startswith("|}") or l.startswith("{|") or l.startswith("|+"):
                continue
            cells.append(P.split_attr(l[1:]))
        gov = [c for c in cells if c[1].lstrip().startswith("'''[[")]
        if gov:
            name = P.plain(gov[0][1].split("<br")[0])
            idx = cells.index(gov[0])
            term = party = elec = None
            for k in range(idx + 1, len(cells)):
                c = cells[k][1]
                if P.DATE_RE.search(c):
                    term = c
                    party = P.plain(cells[k + 1][1]) if k + 1 < len(cells) else None
                    elec = P.plain(cells[k + 2][1]) if k + 2 < len(cells) else None
                    break
            dates = [P.iso(m) for m in P.DATE_RE.finditer(term or "")]
            cur = {"name": name, "dates": dates, "party": party, "elec": elec or "",
                   "later_elec": [], "incumbent": "Incumbent" in (term or "")}
            out.append(cur)
        elif cur is not None:
            for a, c in cells:
                if "gubernatorial" in c and "election" in c:
                    cur["later_elec"].append(P.plain(c))
    return out


def to_term(r):
    party = PARTY_FIX.get(r["party"], r["party"])
    t = {"name": r["name"], "party_raw": party, "start": r["dates"][0],
         "end": None if r["incumbent"] else r["dates"][1],
         "acting": ("acting" in r["elec"]) and not r["later_elec"]}
    if party in NO_PARTY_LABELS:
        t["party_raw"] = "None"
        t["wiki_label"] = party
        if "military" in party.lower():
            t["military_appointee"] = True
    return t


def find(terms, name, start=None):
    for i, t in enumerate(terms):
        if t["name"] == name and (start is None or t["start"] == start):
            return i
    raise KeyError((name, start))


def build_state(code, path):
    state_name, admitted = STATES[code]
    rows = parse_rows(path)
    terms = []
    for r in rows:
        if len(r["dates"]) < (1 if r["incumbent"] else 2):
            continue
        t = to_term(r)
        if t["start"] < admitted:
            continue
        if t["end"] is not None and t["end"] < "1856-01-01":
            continue
        terms.append(t)
    notes = []
    fix = FIXES.get(code)
    if fix:
        fix(terms, notes)
    terms.sort(key=lambda t: (t["start"], t["end"] or "9999"))
    return {
        "state_name": state_name,
        "admitted": admitted,
        "source": "https://en.wikipedia.org/wiki/List_of_governors_of_" + state_name,
        "terms": terms,
        "notes": notes,
    }


def fix_la(terms, notes):
    i = find(terms, "Thomas Overton Moore")
    terms[i]["end"] = "1862-07-02"
    notes.append("Civil War: Wikipedia lists both lines (Confederate: Moore to 1864-01-25, then Henry Watkins Allen "
                 "1864-01-25 to 1865-06-02; Union: Shepley, Hahn, Wells). New Orleans fell 1862-04-25 and Baton Rouge "
                 "was occupied in May 1862; Moore's government fled to Opelousas/Shreveport. Used the Union line from "
                 "Shepley's appointment (1862-07-02): Moore's end truncated to 1862-07-02 and Allen excluded.")
    i = find(terms, "Henry Watkins Allen")
    del terms[i]
    i = find(terms, "George Foster Shepley")
    terms[i]["name"] = "George Foster Shepley"
    notes.append("Shepley (1862-07-02 to 1864-03-04) was a Union military governor (Wikipedia party cell: 'Military "
                 "governor'); recorded with party_raw None and military_appointee true. Flanders and Baker "
                 "(1867-1868) were 'Appointed by military occupation'; also party_raw None.")
    i = find(terms, "John McEnery")
    del terms[i]
    notes.append("1873 dual government: John McEnery (Democratic, 1873-01-13 to 1873-05-22) excluded; William Pitt "
                 "Kellogg (Republican) held the statehouse in New Orleans with federal recognition and troops.")
    i = find(terms, "Stephen B. Packard")
    del terms[i]
    notes.append("1877 dual government: Stephen B. Packard (Republican, 1877-01-08 to 1877-04-25) excluded. Packard "
                 "was confined to the St. Louis Hotel statehouse under federal protection while Francis T. Nicholls' "
                 "(Democratic) government took control of New Orleans and the state; judgment call, Nicholls used "
                 "from 1877-01-08.")
    notes.append("Michael Hahn's party is labelled 'Union Free Trade (Republican)' and James Madison Wells' is "
                 "'Citizens Ticket' (linked to the Louisiana Democratic Party; colour cell Democratic). Kept as labelled.")
    i = find(terms, "Henry Clay Warmoth")
    terms[i] = {"name": "Henry Clay Warmoth", "party_raw": "Republican", "start": terms[i]["start"],
                "end": terms[i]["end"], "acting": False}
    notes.append("Henry Clay Warmoth: first ~16 days (1868-06-27 appointment to 1868-07-13 inauguration) labelled "
                 "'Appointed by military occupation'; recorded as Republican for the whole term.")
    notes.append("Buddy Roemer was elected as a Democrat and switched to Republican late in his term (1991); "
                 "Wikipedia labels him Democratic, kept as Democratic.")
    notes.append("Murphy J. Foster labelled 'Anti-Lottery Democratic'.")


def fix_md(terms, notes):
    i = find(terms, "Marvin Mandel")
    terms[i]["end"] = "1977-06-04"
    terms.append({"name": "Marvin Mandel", "party_raw": "Democratic", "start": "1979-01-15",
                  "end": "1979-01-17", "acting": False})
    i = find(terms, "Blair Lee III")
    terms[i]["acting"] = True
    notes.append("Mandel (1969-01-07 to 1979-01-17 in the table) designated Lt. Gov. Blair Lee III acting governor "
                 "1977-06-04 to 1979-01-15; Mandel split into two terms around Lee's acting term. Lee was briefly "
                 "acting again on 1979-01-16 (ignored).")


def fix_me(terms, notes):
    notes.append("John H. Reed (1959-12-30) succeeded as President of the Senate acting, then won the 1960 special "
                 "and 1962 elections; recorded as one non-acting term. Senate presidents who only served out a "
                 "vacancy are acting: true.")
    notes.append("James B. Longley and Angus King are labelled 'Independent'.")


def fix_ma(terms, notes):
    notes.append("Roger Wolcott (1896), Francis Sargent (1969) and Paul Cellucci (1997) began as Lieutenant governor "
                 "acting and were later elected; recorded as one non-acting term each. Thomas Talbot (1874-75) and "
                 "Jane Swift (2001-03) were acting only.")
    notes.append("Henry Gardner (in office 1856-01-01) labelled 'Know Nothing'.")


def fix_mi(terms, notes):
    notes.append("Michigan list uses January 1 for most inaugurations; recorded as given (day precision).")


def fix_mn(terms, notes):
    notes.append("Statehood 1858-05-11; first state governor Henry Hastings Sibley took office 1858-05-24 "
                 "(13-day gap, territorial governor Samuel Medary excluded).")
    notes.append("Party labels: Wikipedia displays 'Democratic-Farmer-Labor' / 'Farmer-Labor' with hyphens in the "
                 "governor rows (links go to 'Democratic–Farmer–Labor Party' / 'Farmer–Labor Party'); recorded with "
                 "en dashes as 'Democratic–Farmer–Labor' and 'Farmer–Labor'. Al Quie and Arne Carlson labelled "
                 "'Independent-Republican' (the MN GOP's name 1975-1995). Jesse Ventura labelled "
                 "'Reform/Independence' (Reform Party of Minnesota, renamed Independence Party in 2000).")


def fix_ms(terms, notes):
    terms.append({"name": "(military rule)", "party_raw": "None", "start": "1865-05-22",
                  "end": "1865-06-13", "acting": False})
    notes.append("Gap 1865-05-22 (Charles Clark removed by Union forces) to 1865-06-13 (Sharkey appointed) filled "
                 "with a '(military rule)' term.")
    notes.append("William L. Sharkey (1865) 'Provisional governor appointed by President' and Adelbert Ames "
                 "(1868-1870) 'Provisional governor appointed by military occupation' recorded with party_raw None "
                 "(wiki_label holds the exact text). Ames's later 1874-1876 term is Republican.")
    notes.append("Benjamin G. Humphreys (1865-1868) labelled 'Non-partisan' (the 1865 election was officially "
                 "non-partisan).")
    notes.append("John Marshall Stone (1876) and Fielding L. Wright (1946) succeeded as acting and were later "
                 "elected; recorded as one non-acting term each.")
    notes.append("Confederate governors Pettus and Clark kept per the main list; no rival Union civil government "
                 "is listed for Mississippi.")


def fix_mo(terms, notes):
    notes.append("Civil War: Claiborne Fox Jackson (Democratic, pro-Confederate) ended 1861-07-31 when the state "
                 "convention replaced him with Hamilton Rowan Gamble (Union, provisional) in Jefferson City. The "
                 "Confederate government-in-exile (Jackson, then Thomas Caute Reynolds) is not in the main list "
                 "and is excluded.")
    notes.append("Benjamin Gratz Brown labelled 'Liberal Republican'; Gamble and Willard P. Hall labelled 'Union'.")


FIXES = {"LA": fix_la, "MD": fix_md, "ME": fix_me, "MA": fix_ma, "MI": fix_mi,
         "MN": fix_mn, "MS": fix_ms, "MO": fix_mo}


def main(wdir, out):
    data = {}
    for code, (name, _) in STATES.items():
        data[code] = build_state(code, os.path.join(wdir, name + ".wiki"))
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
