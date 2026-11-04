"""Build governors_g2.json from downloaded wikitext.

Usage: python -I build_g2.py <wikitext_dir> <out_json>
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_gov  # noqa: E402

START = "1856-01-01"
TODAY = "2026-11-04"

STATES = {
    "GA": ("Georgia", "1788-01-02"),
    "HI": ("Hawaii", "1959-08-21"),
    "ID": ("Idaho", "1890-07-03"),
    "IL": ("Illinois", "1818-12-03"),
    "IN": ("Indiana", "1816-12-11"),
    "IA": ("Iowa", "1846-12-28"),
    "KS": ("Kansas", "1861-01-29"),
    "KY": ("Kentucky", "1792-06-01"),
}

NOTES = {
    "GA": [
        "James Johnson (1865-06-17 to 1865-12-19) was a provisional governor appointed by President Andrew Johnson; Wikipedia gives no party (party column reads 'Provisional governor appointed by President', colored Nonpartisan), recorded as party_raw 'Nonpartisan'.",
        "James Johnson stayed until 1865-12-19, five days after Charles J. Jenkins was sworn in on 1865-12-14 (per Wikipedia footnote); the 5-day overlap is kept as listed.",
        "1868-01-13 to 1868-07-04: Wikipedia lists Thomas H. Ruger, a U.S. Army officer appointed provisional governor by Gen. George Meade under military occupation (party column 'Military occupation'). Recorded as '(military rule)' with party_raw 'None'; wiki_name field keeps Ruger's name.",
        "Charles J. Jenkins was removed by the military on 1868-01-13 (refused to fund the 1867-68 constitutional convention).",
        "Rufus Bullock (Republican) was appointed by Gen. Meade on 1868-07-04 and then served under the 1868 constitution until resigning 1871-10-30.",
        "Acting governors (marked acting) are those Wikipedia's Election column labels 'President of the Senate acting': Benjamin F. Conley (1871-72), James S. Boynton (1883), John M. Slaton (1911-12).",
        "1947 'three governors controversy': Wikipedia's main list gives Herman Talmadge 1947-01-14 to 1947-03-19 (chosen by the legislature, later ruled unconstitutional), then Melvin E. Thompson 1947-03-19 to 1948-11-17. Ellis Arnall also claimed the office in early 1947; followed the main list.",
        "Eugene Talmadge's 1946 row ('Died before taking office', no dates) is skipped since he never served that term.",
        "Civil War: Joseph E. Brown (Democratic) governed throughout; no rival Union government existed in Georgia, so no choice needed.",
        "Wikipedia's table also lists governor-elect Keisha Lance Bottoms (Democratic, from the 2026 election, taking office 2027-01-11); excluded per instructions.",
    ],
    "HI": [
        "Starts at statehood (1959-08-21). Territorial governors (incl. Quinn's prior territorial tenure) excluded.",
    ],
    "ID": [
        "Admitted 1890-07-03. Wikipedia's state table starts George L. Shoup's state term on 1890-12-08 (first legislature convened); a footnote says some sources use 1890-10-01 (his election). Shoup (Republican) was the territorial governor from before statehood until then, so the 1890-07-03 to 1890-12-08 gap was filled by the same Republican as territorial governor. Kept Wikipedia's date; the gap is intentional, not missing data.",
    ],
    "IL": [
        "Illinois' Wikipedia list labels lieutenant governors who succeeded on a vacancy as 'Lieutenant governor acting' (John Wood 1860, John Lourie Beveridge 1873, John Marshall Hamilton 1883, John Henry Stelle 1940, Samuel Shapiro 1968); marked acting: true to match Wikipedia, although they held the full office. Pat Quinn (2009) is labeled 'Succeeded from lieutenant governor' (not acting).",
    ],
    "IN": [
        "Oliver P. Morton is labeled Republican and Conrad Baker 'Union' in Wikipedia's party column; recorded as given.",
        "Lieutenant governors who succeeded are labeled 'Succeeded from lieutenant governor', not acting.",
    ],
    "IA": [
        "Wikipedia's table also lists governor-elect Rob Sand (Democratic, from the 2026 election, taking office 2027-01-15); excluded per instructions.",
    ],
    "KS": [
        "Admitted 1861-01-29; first state governor Charles L. Robinson took office 1861-02-09 (11-day gap, under territorial administration). Territorial governors excluded.",
    ],
    "KY": [
        "Civil War: a Confederate shadow government (governors George W. Johnson and Richard Hawes) was formed at Russellville in 1861 but never controlled Frankfort; Wikipedia lists them in a separate 'Confederate governors' section. Used the Union-side government in Frankfort (Magoffin, Robinson, Bramlette).",
        "James Fisher Robinson (1862) and Preston Leslie (1871) are labeled 'Succeeded from president of the Senate', not acting; recorded acting: false.",
        "1899-1900 disputed election: Wikipedia lists William S. Taylor (Republican, 1899-12-12 to 1900-01-31) then William Goebel (Democratic, 1900-01-31 to 1900-02-03, died after being shot), then J. C. W. Beckham. Followed the main list.",
        "Thomas E. Bramlette's party is labeled 'Union Democratic' and Charles S. Morehead's 'American' (Know Nothing) in Wikipedia; recorded as given.",
    ],
}


def to_term(r):
    dates = r["dates"]
    start, sprec = dates[0]
    if r["incumbent"] or len(dates) < 2:
        end, eprec = None, "day"
    else:
        end, eprec = dates[1]
    t = {
        "name": r["name"],
        "party_raw": r["party"],
        "start": start,
        "end": end,
        "acting": "acting" in r["election"].lower(),
    }
    if sprec != "day" or eprec != "day":
        t["date_precision"] = sprec if sprec != "day" else eprec
    return t


def main():
    wdir, out = sys.argv[1], sys.argv[2]
    result = {}
    for code, (sname, admitted) in STATES.items():
        text = open(os.path.join(wdir, sname + ".txt"), encoding="utf-8").read()
        rows = parse_gov.extract(text)
        terms = []
        for r in rows:
            if not r["dates"]:
                print("NO DATES", code, r["name"], r["term"], file=sys.stderr)
                continue
            t = to_term(r)
            if t["start"] > TODAY:
                continue  # governor-elect
            if t["end"] is not None and t["end"] < START:
                continue
            terms.append(t)
        # Georgia special cases
        if code == "GA":
            for t in terms:
                if t["name"] == "James Johnson":
                    t["party_raw"] = "Nonpartisan"
                    t["acting"] = False
                if t["name"] == "Thomas H. Ruger":
                    t["wiki_name"] = t["name"]
                    t["name"] = "(military rule)"
                    t["party_raw"] = "None"
        result[code] = {
            "state_name": sname,
            "admitted": admitted,
            "source": "https://en.wikipedia.org/wiki/List_of_governors_of_" + sname,
            "terms": terms,
            "notes": NOTES.get(code, []),
        }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
