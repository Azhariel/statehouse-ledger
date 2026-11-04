"""Dump simplified governor-table rows from a Wikipedia wikitext file.
Usage: python -I dump_rows.py <file.wiki> [table_index ...]
"""
import re
import sys

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
DATE_RE = re.compile(r"(?:(%s)\s+(\d{1,2}),?\s+(\d{4}))|(?:(%s)\s+(\d{4}))|\b(1[789]\d\d|20\d\d)\b" % (MONTHS, MONTHS))


def strip_balanced(text, opener, closer, pred):
    out = []
    i = 0
    while i < len(text):
        if text.startswith(opener, i) and pred(text, i):
            depth = 0
            j = i
            while j < len(text):
                if text.startswith(opener, j):
                    depth += 1
                    j += len(opener)
                elif text.startswith(closer, j):
                    depth -= 1
                    j += len(closer)
                    if depth == 0:
                        break
                else:
                    j += 1
            i = j
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def clean(t):
    t = re.sub(r"<ref[^>/]*/>", "", t)
    t = re.sub(r"<ref[^>]*>.*?</ref>", "", t, flags=re.S)
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    t = strip_balanced(t, "{{", "}}", lambda s, i: re.match(r"\{\{\s*(sfn|efn|refn|r\||cite|harvnb|NoteTag|Efn)", s[i:], re.I) is not None)
    t = strip_balanced(t, "[[", "]]", lambda s, i: re.match(r"\[\[\s*(File|Image):", s[i:], re.I) is not None)
    return t


def link_labels(c):
    return [m.group(2) or m.group(1) for m in re.finditer(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", c)]


def main():
    path = sys.argv[1]
    want = [int(x) for x in sys.argv[2:]]
    text = open(path, encoding="utf-8").read()
    text = clean(text)
    # split tables (top-level only, naive)
    tables = re.findall(r"^\{\|.*?^\|\}", text, flags=re.S | re.M)
    for ti, tb in enumerate(tables):
        if want and ti not in want:
            continue
        print("######## TABLE", ti)
        rows = re.split(r"^\|-.*$", tb, flags=re.M)
        for r in rows[1:]:
            lines = [l for l in r.split("\n") if l.strip()]
            cells = []
            for l in lines:
                if l.startswith("|") or l.startswith("!"):
                    for c in re.split(r"\|\||!!", l[1:]):
                        cells.append(c)
                elif cells:
                    cells[-1] += " " + l
            out = []
            for c in cells:
                titles = re.findall(r'title="([^"]*)"', c)
                # drop attributes prefix
                m = re.match(r'^([^\[\]{}|]*=[^\[\]|]*)\|(.*)$', c, flags=re.S)
                body = m.group(2) if m else c
                body = re.sub(r"<br\s*/?>", " ", body)
                body = re.sub(r"\{\{[Ss]mall\|\(([^)]*)\)\}\}", "", body)
                if titles:
                    out.append("T:" + ";".join(titles))
                b = body.strip()
                if b and b != "&nbsp;":
                    b = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", b)
                    b = re.sub(r"\[\[([^\]]+)\]\]", r"\1", b)
                    b = re.sub(r"\s+", " ", b)
                    out.append(b[:110])
            print(" | ".join(out))


if __name__ == "__main__":
    main()
