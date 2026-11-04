"""Build congress.json from saved Wikipedia wikitext.

Usage: python -I build_congress.py <party_divisions.wikitext> <presidents.wikitext> <out.json>
"""
import datetime as dt
import json
import re
import sys

SRC_CONG = "https://en.wikipedia.org/w/index.php?title=Party_divisions_of_United_States_Congresses&action=raw"
SRC_PRES = "https://en.wikipedia.org/w/index.php?title=List_of_presidents_of_the_United_States&action=raw"

SHADE_CODE = {"Democratic": "D", "Republican": "R"}


def strip_refs(s):
    s = re.sub(r"<ref[^>]*/>", "", s)
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.S)
    return s


def cell_parts(line):
    """Return (shading_party, text) for a '|...' table cell line."""
    body = line[1:]
    shade = None
    m = re.search(r"\{\{Party shading/([^}]+)\}\}", body)
    if m:
        shade = m.group(1).strip()
    # value is after the last attribute separator ' |'
    if "|" in body and (m or "rowspan" in body or "style" in body):
        # remove templates first so their pipes don't confuse us
        tmp = re.sub(r"\{\{[^}]*\}\}", "", body)
        tmp = re.sub(r"\[\[[^\]]*\]\]", lambda x: x.group(0).replace("|", "\x00"), tmp)
        if "|" in tmp:
            tmp = tmp.split("|", 1)[1]
        body = tmp.replace("\x00", "|")
    return shade, body.strip()


def first_int(text):
    t = text.replace("'''", "")
    m = re.search(r"\d+", t)
    return int(m.group(0)) if m else 0


def is_bold(text):
    return "'''" in text


def start_date(n):
    if n <= 73:
        return dt.date(1789 + 2 * (n - 1), 3, 4)
    return dt.date(1935 + 2 * (n - 74), 1, 3)


def end_date(n):
    if n < 73:
        return start_date(n + 1) - dt.timedelta(days=1)
    return start_date(n + 1)  # 73rd onward ends Jan 3 (noon handover)


def chamber(cells, shade_total):
    # cells: [D, R/Opp, Others, Vacancies]
    d_shade, d_txt = cells[0]
    r_shade, r_txt = cells[1]
    o_shade, o_txt = cells[2]
    out = {"D": first_int(d_txt), "R": first_int(r_txt), "O": first_int(o_txt)}
    return out, d_txt, r_txt, o_txt


def parse_congress(text):
    text = strip_refs(text)
    rows = re.split(r"\n\|-[^\n]*\n", text)
    result = {}
    for row in rows:
        lines = [l for l in row.split("\n") if l.startswith("|") and not l.startswith("|}")]
        if not lines:
            continue
        m = re.match(r"\|\[\[(\d+)(?:st|nd|rd|th) United States Congress", lines[0])
        if not m:
            continue
        n = int(m.group(1))
        if n < 34 or n > 119:
            continue
        cells = [cell_parts(l) for l in lines]
        years = cells[1][1]
        sen_tot = cells[2]
        sen = cells[3:7]
        hou_tot = cells[7]
        hou = cells[8:12]
        result[n] = {"years": years, "sen_tot": sen_tot, "sen": sen, "hou_tot": hou_tot, "hou": hou}
    return result


def second_col_party(n):
    return "Opposition" if n == 34 else "Republican"


def build_chamber(n, tot, cells, name):
    counts = {"D": first_int(cells[0][1]), "R": 0, "O": first_int(cells[2][1])}
    second = first_int(cells[1][1])
    if n == 34:
        counts["O"] += second  # Opposition coalition counted as other
    else:
        counts["R"] = second
    shade = tot[0]
    if shade == "Democratic":
        maj, raw = "D", "Democratic"
    elif shade == "Republican":
        maj, raw = "R", "Republican"
    else:
        maj, raw = "O", shade
    return {**counts, "majority": maj, "majority_raw": raw}, {
        "total_raw": tot[1], "cells_raw": [c[1] for c in cells], "shade_total": shade,
        "bold": [is_bold(c[1]) for c in cells[:3]],
    }


def parse_presidents(text):
    text = strip_refs(text)
    blocks = re.split(r"\n\|-\s*\n(?=!)", text)
    out = []
    for b in blocks:
        m = re.search(r"\{\{sortname\|([^|}]+)\|([^|}]+)", b)
        if not m or "scope=row" not in b:
            continue
        name = f"{m.group(1)} {m.group(2)}"
        dates = re.findall(r"\{\{dts\|([^}]+)\}\}", b)
        incumbent = "Incumbent" in b.split("{{dts|")[-1][:80] if dates else False
        parties = re.findall(r"^\|(?:rowspan=\d+ ?\|)?\[\[[^\]|]*Party[^\]|]*\|([^\]]+)\]\]", b, flags=re.M)
        parties = list(dict.fromkeys(parties))
        if not parties:
            parties = re.findall(r"^\|(?:rowspan=\d+ ?\|)?(Independent|Unaffiliated)", b, flags=re.M)
        def pd(s):
            return dt.datetime.strptime(s.strip(), "%B %d, %Y").date()
        start = pd(dates[0])
        end = None if incumbent else pd(dates[1])
        out.append({"name": name, "parties": parties, "start": start, "end": end})
    return out


def main(cong_path, pres_path, out_path):
    cong = parse_congress(open(cong_path, encoding="utf-8").read())
    pres = parse_presidents(open(pres_path, encoding="utf-8").read())

    congresses = []
    debug = []
    for n in range(34, 120):
        r = cong[n]
        s = start_date(n)
        e = end_date(n)
        y = re.findall(r"\d{4}", r["years"])
        assert int(y[0]) == s.year and int(y[1]) == e.year, (n, r["years"])
        sen, sdbg = build_chamber(n, r["sen_tot"], r["sen"], "senate")
        hou, hdbg = build_chamber(n, r["hou_tot"], r["hou"], "house")
        congresses.append({"number": n, "start": s.isoformat(), "end": e.isoformat(),
                           "senate": sen, "house": hou, "changes": [], "notes": []})
        debug.append((n, sdbg, hdbg))

    by = {c["number"]: c for c in congresses}

    # Manual annotations grounded in the Wikipedia table footnotes.
    by[34]["house"]["majority_raw"] = "Opposition"
    by[34]["notes"].append("House: Opposition Party (anti-Nebraska coalition of ex-Whigs, Know Nothings/American and early Republicans) organized the chamber; Wikipedia lists 100 Opposition + 51 others, all counted under O here. Senate column 2 (21) is Opposition, also counted under O.")
    by[36]["notes"].append("House: Republicans controlled the House through a coalition with other Opposition parties (Wikipedia footnote); Republicans were a plurality, not a majority.")
    for n in (37, 38):
        by[n]["notes"].append("Others column includes Unionists (Unconditional Unionist, Union, etc.).")
    by[47]["notes"].append("Senate: unshaded/split in Wikipedia (37 D, 37 R, 2 others). Special session March 1881: Republicans held it via VP Arthur tiebreak plus Readjuster William Mahone; lost control May 16, 1881 when both NY Republican senators resigned; from Oct 1881 the Great Senate Deadlock produced shared control (Republicans ran committees, Democrat-caucusing independent David Davis was president pro tempore, Democrats got patronage). Recorded as R.")
    by[47]["senate"]["majority"] = "R"
    by[47]["senate"]["majority_raw"] = "Republican (shared control)"
    by[47]["notes"].append("House: Republicans controlled the House through a plurality that became a majority during the first session (Wikipedia footnote).")
    by[65]["notes"].append("House: Republicans had the most seats (216 vs 210) but Democrats organized the House in coalition with Progressives and a Socialist.")
    by[72]["notes"].append("Senate: Republicans controlled via VP tiebreak. House: 217-217-1 at the start; Democrats gained the majority through special elections before the first session convened (Dec 1931) and held it all term.")
    by[83]["notes"].append("Senate: Republicans controlled via VP tiebreak (and in 1954 a caucus with Independent Wayne Morse) except for a few days at the end of each session per Wikipedia; not recorded as a control change.")
    by[107]["senate"]["majority"] = "D"
    by[107]["senate"]["majority_raw"] = "Democratic"
    by[107]["changes"] = [
        {"chamber": "senate", "date": "2001-01-20", "majority": "R",
         "note": "50-50 split; organization passed to Republicans when VP Dick Cheney took office as tiebreaker."},
        {"chamber": "senate", "date": "2001-06-06", "majority": "D",
         "note": "Jim Jeffords left the GOP to caucus with Democrats (announced May 24, effective June 6, 2001; Wikipedia footnote cites May 24)."},
    ]
    by[107]["notes"].append("Senate 2001-01-03 to 2001-01-20: 50-50 with Democratic VP Al Gore as tiebreaker, so Democrats organized.")
    by[117]["senate"]["majority"] = "R"
    by[117]["senate"]["majority_raw"] = "Republican"
    by[117]["changes"] = [
        {"chamber": "senate", "date": "2021-01-20", "majority": "D",
         "note": "Warnock and Ossoff sworn in giving a 50-50 split (incl. 2 independents caucusing with Democrats); VP Kamala Harris tiebreak gave Democrats control."},
    ]
    by[117]["notes"].append("Senate counts are at start (Jan 3, 2021): Wikipedia lists D 46-48, R 51/50, I 2/3. Republicans controlled Jan 3-20, 2021.")
    by[118]["notes"].append("Senate O counts 3 independents caucusing with Democrats (Sanders, King, Sinema); Democrats organized 51-49 with caucus.")
    for n in range(107, 120):
        if by[n]["senate"]["O"]:
            pass
    for c in congresses:
        for ch in ("senate", "house"):
            c[ch].pop("notes", None)

    # Presidents: start from the one in office on 1856-01-01.
    cutoff = dt.date(1856, 1, 1)
    presidents = []
    for p in pres:
        if p["end"] is not None and p["end"] < cutoff:
            continue
        if p["name"] == "Abraham Lincoln" and p["parties"] == ["Republican", "National Union"]:
            presidents.append({"name": p["name"], "party_raw": "Republican",
                               "start": p["start"].isoformat(), "end": "1865-03-04"})
            presidents.append({"name": p["name"], "party_raw": "National Union",
                               "start": "1865-03-04", "end": p["end"].isoformat(),
                               "note": "2nd term; ran on the National Union ticket in 1864."})
            continue
        entry = {"name": p["name"], "party_raw": p["parties"][0],
                 "start": p["start"].isoformat(),
                 "end": p["end"].isoformat() if p["end"] else None}
        if len(p["parties"]) > 1:
            entry["party_raw_all"] = p["parties"]
            entry["note"] = "Wikipedia lists multiple parties: " + " then ".join(p["parties"]) + "."
        presidents.append(entry)

    data = {
        "sources": [SRC_CONG, SRC_PRES],
        "congresses": congresses,
        "presidents": presidents,
        "notes": [
            "Seat counts are the first number Wikipedia lists for each cell (start of Congress); cells like '46-48' or '53/52' record later changes.",
            "O = all non-D/R members (independents, third parties, Opposition, Unionists, etc.). Independents caucusing with a party are still counted under O.",
            "majority comes from the shading of the chamber's Total cell in the Wikipedia table (the party that organized the chamber at the start of the Congress); mid-Congress control changes are in each Congress's changes array.",
            "Dates: Congresses 34-72 run March 4 to March 3; the 73rd runs 1933-03-04 to 1935-01-03 (20th Amendment); from the 74th on, Congresses run Jan 3 to Jan 3 (the handover happens at noon, so end equals the next start).",
            "Presidential end dates equal the successor's start date (Wikipedia convention).",
        ],
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Debug dump for eyeballing.
    for n, sd, hd in debug:
        c = by[n]
        flag = ""
        for ch, d in (("S", sd), ("H", hd)):
            maj = c["senate" if ch == "S" else "house"]["majority"]
            bold_idx = [i for i, b in enumerate(d["bold"]) if b]
            exp = {0: "D", 1: "R" if n != 34 else "O", 2: "O"}
            bold_maj = sorted({exp[i] for i in bold_idx})
            if bold_maj != [maj]:
                flag += f" {ch}:shade={d['shade_total']} bold={bold_maj}"
        print(n, c["start"], c["end"],
              "S", {k: c["senate"][k] for k in ("D", "R", "O", "majority")},
              "H", {k: c["house"][k] for k in ("D", "R", "O", "majority")}, flag)
    for p in presidents:
        print(p)


if __name__ == "__main__":
    main(*sys.argv[1:4])
