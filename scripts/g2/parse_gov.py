"""Parse a Wikipedia 'List of governors of X' wikitext into rows (grid-aware).

Usage: python -I parse_gov.py <wikitext_file> [--tsv]
Prints JSON list of rows from the state governor table (first table whose
header has Party and Election columns).
"""
import json
import re
import sys

MONTHS = ("January February March April May June July August September "
          "October November December").split()
MON_RE = "|".join(MONTHS)


def strip_templates(text, names):
    """Remove {{name ...}} templates (brace-aware, case-insensitive)."""
    out = []
    i = 0
    low = text.lower()
    while i < len(text):
        if text.startswith("{{", i):
            m = re.match(r"\{\{\s*([^|}]+)", text[i:])
            nm = m.group(1).strip().lower() if m else ""
            if nm in names:
                depth = 0
                j = i
                while j < len(text):
                    if text.startswith("{{", j):
                        depth += 1
                        j += 2
                    elif text.startswith("}}", j):
                        depth -= 1
                        j += 2
                        if depth == 0:
                            break
                    else:
                        j += 1
                i = j
                continue
        out.append(text[i])
        i += 1
    return "".join(out)


def strip_refs(text):
    text = re.sub(r"<ref[^>/]*/>", "", text)
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    return strip_templates(text, {"efn", "sfn", "refn", "efn-ua", "sfnm",
                                  "cn", "citation needed", "abbr"})


def split_attr(cell):
    """Split 'attrs|content' at the first depth-0 single pipe."""
    depth_sq = depth_br = 0
    i = 0
    while i < len(cell):
        if cell.startswith("[[", i):
            depth_sq += 1; i += 2; continue
        if cell.startswith("]]", i):
            depth_sq -= 1; i += 2; continue
        if cell.startswith("{{", i):
            depth_br += 1; i += 2; continue
        if cell.startswith("}}", i):
            depth_br -= 1; i += 2; continue
        if cell[i] == "|" and depth_sq == 0 and depth_br == 0:
            return cell[:i], cell[i + 1:]
        i += 1
    return "", cell


def clean(s):
    s = re.sub(r"\[\[File:[^\]]*\]\]", "", s)
    s = re.sub(r"\{\{\s*(?:small|nowrap|nobr)\s*\|", "{{X|", s, flags=re.I)
    # unwrap simple templates {{X|content}}
    for _ in range(5):
        s = re.sub(r"\{\{X\|([^{}]*)\}\}", r"\1", s)
    s = re.sub(r"\{\{\s*sortname\s*\|([^|}]*)\|([^|}]*)[^}]*\}\}", r"\1 \2", s, flags=re.I)
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("'''", "").replace("''", "")
    s = s.replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", s).strip()


def parse_tables(text):
    tables = []
    lines = text.split("\n")
    cur = None
    for ln in lines:
        if ln.startswith("{|"):
            cur = {"rows": [], "row": None}
            continue
        if cur is None:
            continue
        if ln.startswith("|}"):
            if cur["row"] is not None:
                cur["rows"].append(cur["row"])
            tables.append(cur["rows"])
            cur = None
            continue
        if ln.startswith("|-"):
            if cur["row"] is not None:
                cur["rows"].append(cur["row"])
            cur["row"] = []
            continue
        if ln.startswith("|+"):
            continue
        if ln.startswith("|") or ln.startswith("!"):
            if cur["row"] is None:
                cur["row"] = []
            body = ln[1:]
            sep = "!!" if ln.startswith("!") else "||"
            for part in body.split(sep):
                cur["row"].append(part)
        else:
            if cur["row"]:
                cur["row"][-1] += "\n" + ln
    return tables


def build_grid(rows):
    grid = []
    pending = {}  # col -> (remaining, cellinfo)
    for r in rows:
        out = []
        col = 0
        cells = list(r)
        while cells or any(c >= col for c in pending):
            if col in pending:
                rem, info = pending[col]
                out.append(info)
                if rem - 1 <= 0:
                    del pending[col]
                else:
                    pending[col] = (rem - 1, info)
                col += 1
                continue
            if not cells:
                break
            raw = cells.pop(0)
            attr, content = split_attr(raw)
            rs = re.search(r'rowspan\s*=\s*"?(\d+)', attr)
            cs = re.search(r'colspan\s*=\s*"?(\d+)', attr)
            rs = int(rs.group(1)) if rs else 1
            cs = int(cs.group(1)) if cs else 1
            info = {"attr": attr, "raw": content}
            for k in range(cs):
                out.append(info)
                if rs > 1:
                    pending[col] = (rs - 1, info)
                col += 1
        grid.append(out)
    return grid


DATE_RE = re.compile(r"(?:(%s)\s+(?:(\d{1,2}),\s*)?)?(\d{4})" % MON_RE)


def parse_dates(s):
    found = []
    for m in DATE_RE.finditer(s):
        mon, day, yr = m.groups()
        if mon and day:
            found.append(("%s-%02d-%02d" % (yr, MONTHS.index(mon) + 1, int(day)), "day"))
        elif mon:
            found.append(("%s-%02d-01" % (yr, MONTHS.index(mon) + 1), "month"))
        else:
            found.append(("%s-01-01" % yr, "year"))
    return found


def extract(text):
    tables = parse_tables(text)
    target = None
    for t in tables:
        hdr = " ".join(" ".join(r) for r in t[:2])
        if "Party" in hdr and "Election" in hdr and "Term in office" in hdr:
            target = t
            break
    grid = build_grid(target)
    res = []
    for row in grid:
        if len(row) < 6:
            continue
        name_cell = row[3]["raw"]
        if "'''" not in name_cell and "[[" not in name_cell:
            continue
        if row[3] is row[2] or row[3] is row[1]:
            pass
        term_raw = strip_refs(row[4]["raw"])
        term = clean(term_raw)
        dates = [d for d in parse_dates(term)]
        name = clean(strip_refs(name_cell))
        name = re.sub(r"\s*\([^()]*\d{4}[^()]*\)\s*", " ", name).strip()
        party = clean(strip_refs(row[5]["raw"]))
        elect = clean(strip_refs(row[6]["raw"])) if len(row) > 6 else ""
        color_title = re.search(r'title="([^"]*)"', row[2]["attr"])
        sd = re.search(r'data-sort-value="(\d+)"', row[4]["attr"])
        res.append({
            "sortdays": int(sd.group(1)) if sd else None,
            "id": id(row[3]),
            "name": name,
            "term": term,
            "dates": dates,
            "incumbent": "incumbent" in term.lower(),
            "party": party,
            "election": elect,
            "color_title": color_title.group(1) if color_title else "",
        })
    # dedupe rows that are continuations of rowspan name cells
    out = []
    seen = set()
    for r in res:
        if r["id"] in seen:
            continue
        seen.add(r["id"])
        del r["id"]
        out.append(r)
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    out = extract(open(sys.argv[1], encoding="utf-8").read())
    if "--tsv" in sys.argv:
        for r in out:
            print("\t".join([r["name"], " | ".join(d[0] for d in r["dates"][:2]),
                             r["party"], r["election"][:60], r["color_title"]]))
    else:
        print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
