"""Extract state Senate / House majority per year from Wikipedia "Political party strength in X" pages.

Usage: python -I scripts/legislature.py <wikitext_dir> <out.json>

Each page has a year-by-year table where every cell carries a {{Party shading/X}}
template for the controlling party, plus seat counts like "29R, 1D". Cells use
rowspan/colspan, so the table is rebuilt as a full grid before reading columns.
"""
import json
import os
import re
import sys

STATES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA",
    "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT",
    "Nebraska": "NE", "Nevada": "NV", "New_Hampshire": "NH", "New_Jersey": "NJ", "New_Mexico": "NM",
    "New_York": "NY", "North_Carolina": "NC", "North_Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode_Island": "RI", "South_Carolina": "SC",
    "South_Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
    "Virginia": "VA", "Washington": "WA", "West_Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}
FIRST_YEAR, LAST_YEAR = 1856, 2026

SHADING = re.compile(r"\{\{\s*party shading\s*/\s*([^}|]+?)\s*[|}]", re.I)
YEAR_ROW = re.compile(r"^!\s*(?:[^|!]*\|)?\s*'*(\d{4})\b")


def split_top(s, sep):
    """Split on sep, ignoring separators inside [[...]] or {{...}}."""
    out, depth, buf, i = [], 0, [], 0
    while i < len(s):
        two = s[i:i + 2]
        if two in ("[[", "{{"):
            depth += 1; buf.append(two); i += 2; continue
        if two in ("]]", "}}"):
            depth = max(0, depth - 1); buf.append(two); i += 2; continue
        if depth == 0 and s.startswith(sep, i):
            out.append("".join(buf)); buf = []; i += len(sep); continue
        buf.append(s[i]); i += 1
    out.append("".join(buf))
    return out


def parse_cell(text):
    """Return (attrs, content, rowspan, colspan) for one wikitext cell."""
    parts = split_top(text, "|")
    if len(parts) >= 2 and re.search(r"(rowspan|colspan|style|class|\{\{\s*party shading)", parts[0], re.I):
        attrs, content = parts[0], "|".join(parts[1:])
    else:
        attrs, content = "", text
    rs = re.search(r"rowspan\s*=\s*\"?(\d+)", attrs)
    cs = re.search(r"colspan\s*=\s*\"?(\d+)", attrs)
    return attrs, content.strip(), int(rs.group(1)) if rs else 1, int(cs.group(1)) if cs else 1


def row_cells(lines):
    cells = []
    for line in lines:
        if line.startswith("!"):
            cells += [("!", c) for c in split_top(line[1:], "!!")]
        elif line.startswith("|") and not line.startswith(("|-", "|}", "|+")):
            cells += [("|", c) for c in split_top(line[1:], "||")]
        elif cells:  # continuation of a multi-line cell
            kind, c = cells[-1]
            cells[-1] = (kind, c + "\n" + line)
    return cells


def tables(text):
    depth, cur, out = 0, [], []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("{|"):
            depth += 1
            if depth == 1:
                cur = []
                continue
        if s.startswith("|}"):
            depth -= 1
            if depth == 0:
                out.append(cur)
                continue
        if depth >= 1:
            cur.append(s)
    return out


def classify(label):
    l = label.lower()
    if any(k in l for k in ("u.s.", "united states", "congress", "electoral", "president", "senator")):
        return None
    if "senate" in l:
        return "senate"
    if any(k in l for k in ("house", "assembly", "delegates", "representatives")):
        return "house"
    if "legislature" in l and "state legislature" not in l:
        return "unicameral"
    return None


def party_from_cell(attrs, content):
    m = SHADING.search(attrs) or SHADING.search(content)
    if m:
        return m.group(1).strip()
    return None


def parse_table(rows):
    """rows: list of line-lists. Returns {year: {"senate": (shade, text), "house": ...}} or None."""
    header_rows, data_rows = [], []
    for r in rows:
        cells = row_cells(r)
        if not cells:
            continue
        first_kind, first = cells[0]
        if data_rows or (first_kind == "!" and YEAR_ROW.match("!" + first.strip())):
            data_rows.append(cells)
        else:
            header_rows.append(cells)
    if not data_rows or not header_rows:
        return None

    # Rebuild header grid -> label stack per column.
    labels, pending = {}, {}
    for cells in header_rows:
        col, it = 0, iter(cells)
        placed = {}
        while True:
            while col in pending and pending[col][0] > 0:
                pending[col][0] -= 1
                col += 1
            try:
                _, c = next(it)
            except StopIteration:
                break
            attrs, content, rs, cs = parse_cell(c)
            for k in range(cs):
                labels.setdefault(col + k, []).append(content)
                if rs > 1:
                    pending[col + k] = [rs - 1]
            col += cs
    kinds = {col: classify(" / ".join(stack)) for col, stack in labels.items()}
    if not any(kinds.values()):
        return None

    # Every row goes through the same grid logic; the year cell is column 0.
    # A year with rowspan > 1 (mid-year changes) covers column 0 of its sub-rows.
    result, pending, year = {}, {}, None
    ncols = max(labels) + 1
    for cells in data_rows:
        grid, col, it, exhausted = {}, 0, iter(cells), False
        while col < ncols:
            if col in pending and pending[col][0] > 0:
                pending[col][0] -= 1
                grid[col] = pending[col][1]
                col += 1
                continue
            if exhausted:
                col += 1
                continue
            try:
                kind, c = next(it)
            except StopIteration:
                exhausted = True
                continue
            attrs, content, rs, cs = parse_cell(c)
            if col == 0:
                m = YEAR_ROW.match("!" + c.strip())
                year = int(m.group(1)) if m else year
            val = (party_from_cell(attrs, content), re.sub(r"\s+", " ", content))
            for k in range(cs):
                grid[col + k] = val
                if rs > 1:
                    pending[col + k] = [rs - 1, val]
            col += cs
        if year is None:
            continue
        entry = result.setdefault(year, {})
        for col, kind in kinds.items():
            if kind and col in grid and kind not in entry:
                entry[kind] = grid[col]
    return {y: e for y, e in result.items() if e}


SEAT = re.compile(r"(\d+)\s*([A-Za-z?]+)")


UNION_SHADES = ("unionist", "unconditional unionist", "national union", "union")
# NPL and the IVA were factions inside the North Dakota GOP, matching the governor data.
REPUBLICAN_FACTIONS = ("npl", "independent voters association")


def majority_code(shade, text, state=None):
    """D / R / O (other party) / T (tie or coalition) / N (nonpartisan) / None (no data)."""
    t = re.sub(r"<ref.*?(</ref>|/>)|\{\{efn.*?\}\}|&nbsp;", " ", text or "", flags=re.I | re.S)
    if shade:
        s = shade.lower().replace("/current", "").strip()
        if "nonpartisan" in s or "non-partisan" in s:
            return "N"
        if s in ("tie", "coalition"):
            return "T"
        if s in UNION_SHADES:
            return "O" if state == "KY" else "R"
        if s in REPUBLICAN_FACTIONS:
            return "R"
        if s in ("dfl", "conservative"):
            return "D"
        if "democrat" in s and "republican" not in s:
            return "D"
        if "republican" in s and "democrat" not in s:
            return "R"
        return "O"
    if re.search(r"nonpartisan|non-partisan", t, re.I):
        return "N"
    counts = {}
    for n, p in SEAT.findall(t):
        p = p.upper()
        if p.startswith("VAC") or p == "?":
            continue
        counts[p] = counts.get(p, 0) + int(n)
    if not counts:
        return None
    top = sorted(counts.items(), key=lambda kv: -kv[1])
    if len(top) > 1 and top[0][1] == top[1][1]:
        return "T"
    p = top[0][0]
    return p if p in ("D", "R") else "O"


def main():
    src_dir, out_path = sys.argv[1], sys.argv[2]
    out = {}
    for fname, code in STATES.items():
        text = open(os.path.join(src_dir, fname + ".txt"), encoding="utf-8").read()
        merged = {}
        for t in tables(text):
            rows, cur = [], []
            for line in t:
                if line.startswith("|-"):
                    rows.append(cur); cur = []
                else:
                    cur.append(line)
            rows.append(cur)
            parsed = parse_table(rows)
            if parsed:
                for y, e in parsed.items():
                    merged.setdefault(y, {}).update({k: v for k, v in e.items() if k not in merged.get(y, {})})
        years = {}
        for y in range(FIRST_YEAR, LAST_YEAR + 1):
            e = merged.get(y, {})
            row = {}
            for kind in ("senate", "house", "unicameral"):
                if kind in e:
                    shade, txt = e[kind]
                    row[kind] = {"code": majority_code(shade, txt, code), "shade": shade, "text": txt[:120]}
            years[y] = row
        out[code] = years
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=0)

    # Coverage report
    print(f"{'st':3} {'sen':>4} {'hse':>4} {'uni':>4}  first_sen  shades")
    for code, years in out.items():
        sen = sum(1 for r in years.values() if r.get("senate", {}).get("code"))
        hse = sum(1 for r in years.values() if r.get("house", {}).get("code"))
        uni = sum(1 for r in years.values() if r.get("unicameral", {}).get("code"))
        first = next((y for y, r in years.items() if r.get("senate", {}).get("code")), None)
        shades = sorted({(r[k]["shade"] or "-") for r in years.values() for k in r if r[k]["code"] not in ("D", "R")})
        print(f"{code:3} {sen:4} {hse:4} {uni:4}  {first}  {shades[:6]}")


if __name__ == "__main__":
    main()
