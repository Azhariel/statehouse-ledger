"""Dump cleaned table rows from a wikitext file, starting at a given line.
Usage: python -I dump_rows.py <file> <start_line> [end_line]
"""
import re, sys

def strip_nested(s, open_, close_, pred=lambda inner: True):
    # remove {{...}} templates matching predicate, handling nesting
    out = []
    i = 0
    while i < len(s):
        if s.startswith(open_, i):
            depth = 0
            j = i
            while j < len(s):
                if s.startswith(open_, j):
                    depth += 1; j += len(open_); continue
                if s.startswith(close_, j):
                    depth -= 1; j += len(close_)
                    if depth == 0: break
                    continue
                j += 1
            inner = s[i + len(open_): j - len(close_)]
            if pred(inner):
                out.append(TEMPLATE_REPL(inner))
            else:
                out.append(s[i:j])
            i = j
        else:
            out.append(s[i]); i += 1
    return ''.join(out)

def TEMPLATE_REPL(inner):
    name = inner.split('|', 1)[0].strip().lower()
    parts = inner.split('|')
    if name in ('small', 'nowrap', 'nobr', 'big'):
        return parts[1] if len(parts) > 1 else ''
    if name == 'sortname':
        p = [x for x in parts[1:] if '=' not in x]
        return ' '.join(p[:2])
    if name in ('dts', 'date', 'start date', 'end date'):
        return ' '.join(parts[1:])
    if name in ('ndash', 'snd', 'spaced ndash'):
        return '–'
    if name in ('party shading', 'party color'):
        return ''
    return ''

def clean(s):
    s = re.sub(r'<ref[^>]*/>', '', s)
    s = re.sub(r'<ref[^>]*>.*?</ref>', '', s, flags=re.S)
    s = re.sub(r'<!--.*?-->', '', s, flags=re.S)
    s = strip_nested(s, '{{', '}}')
    s = re.sub(r'\[\[(?:File|Image):[^\[\]]*(?:\[\[[^\]]*\]\][^\[\]]*)*\]\]', '', s)
    s = re.sub(r'\[\[([^\]|]*)\|([^\]]*)\]\]', r'\2', s)
    s = re.sub(r'\[\[([^\]]*)\]\]', r'\1', s)
    s = re.sub(r'<br\s*/?>', ' / ', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = s.replace("'''", '').replace("''", '').replace('&nbsp;', ' ').replace('&ndash;', '–')
    return re.sub(r'\s+', ' ', s).strip()

def split_cells(row_lines):
    cells = []
    for ln in row_lines:
        if not ln or ln[0] not in '|!':
            if cells:
                cells[-1] += '\n' + ln
            continue
        body = ln[1:]
        sep = '||' if ln[0] == '|' else '!!'
        for part in body.split(sep) if sep in body and '[[' not in body.split(sep)[0][-3:] else [body]:
            cells.append(part)
    out = []
    for c in cells:
        # attribute|content split: first single '|' not inside [[ ]] or {{ }}
        depth = 0; idx = -1; k = 0
        while k < len(c):
            if c.startswith('[[', k) or c.startswith('{{', k): depth += 1; k += 2; continue
            if c.startswith(']]', k) or c.startswith('}}', k): depth -= 1; k += 2; continue
            if c[k] == '|' and depth == 0: idx = k; break
            k += 1
        attr, content = (c[:idx], c[idx+1:]) if idx >= 0 else ('', c)
        if idx >= 0 and ('=' not in attr and 'scope' not in attr):
            attr, content = '', c
        rs = re.search(r'rowspan\s*=\s*"?(\d+)', attr)
        out.append((int(rs.group(1)) if rs else 1, content))
    return out

def rows(text, start, end):
    lines = text.split('\n')[start-1:end]
    cur = None; res = []
    for ln in lines:
        if ln.startswith('|-') or ln.startswith('|}'):
            if cur is not None: res.append(cur)
            cur = [] if ln.startswith('|-') else None
            continue
        if ln.startswith('{|'):
            cur = None; continue
        if cur is not None:
            cur.append(ln)
    if cur: res.append(cur)
    return res

if __name__ == '__main__':
    f, a = sys.argv[1], int(sys.argv[2])
    b = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
    text = open(f, encoding='utf-8').read()
    for r in rows(text, a, b):
        cells = split_cells(r)
        print(' ¦ '.join(f'[{rs}]{clean(c)}' if rs > 1 else clean(c) for rs, c in cells)[:400])
