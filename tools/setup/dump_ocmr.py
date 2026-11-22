#!/usr/bin/env python3
"""List the option values of the VARSTORE_OCMR_SETTINGS section (varstore 0x20)
of a decompressed .CMO profile, cross-referenced with the decoded IFR dump
(produced by tools/setup/ifr_dump.py).

Usage: dump_ocmr.py <profile.bin> <setup_ifr_all.txt> [all]
Without `all`, only values that differ from the IFR default are shown."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cmo_parse

sec = cmo_parse.parse(open(sys.argv[1], 'rb').read())['VARSTORE_OCMR_SETTINGS'][2]
show_all = len(sys.argv) > 3
L = open(sys.argv[2], errors='replace').read().split('\n')
re_q = re.compile(r'^\S+\s+(ONEOF|NUMERIC|STRING|CHECKBOX) prompt=0x[0-9a-f]+"(.*?)" help=.*? qid=(0x[0-9a-f]+) vs=0x20 off=(0x[0-9a-f]+)(?:.*? size=(\d+))?')
re_opt = re.compile(r'^\S+\s+OPTION text=0x[0-9a-f]+"(.*?)" flags=(0x[0-9a-f]+) type=\d+ val=(-?\d+)')
seen = {}
i = 0
while i < len(L):
    m = re_q.match(L[i])
    if not m:
        i += 1
        continue
    kind, name, qid, off, size = m.group(1), m.group(2).strip(), m.group(3), int(m.group(4), 16), int(m.group(5) or 1)
    opts = []
    j = i + 1
    if kind == 'ONEOF':
        while j < len(L):
            t = L[j].split()
            if len(t) > 1 and t[1] in ('ONEOF', 'NUMERIC', 'STRING', 'CHECKBOX', 'FORM', 'REF', 'SUBTITLE', 'TEXT'):
                break
            mo = re_opt.match(L[j])
            if mo:
                opts.append((mo.group(1), int(mo.group(2), 16), int(mo.group(3))))
            j += 1
    key = (kind, off, name)
    e = seen.setdefault(key, {'size': size, 'opts': [], 'line': i + 1})
    for x in opts:
        if x not in e['opts']:
            e['opts'].append(x)
    i += 1
for (kind, off, name), e in sorted(seen.items(), key=lambda kv: kv[1]['line']):
    if kind == 'STRING':
        raw = sec[off:off + 40]
        s = raw.decode('utf-16-le', errors='replace').split('\0')[0]
        if show_all or (s and s.lower() != 'auto'):
            print('STR  %#06x  %-46s = "%s"' % (off, name, s))
    elif kind == 'ONEOF':
        v = int.from_bytes(sec[off:off + e['size']], 'little')
        cur = [t for t, f, val in e['opts'] if val == v]
        dfl = [t for t, f, val in e['opts'] if f & 0x10]
        if show_all or (cur[:1] != dfl[:1] and not (cur and cur[0] in dfl)):
            print('ONE  %#06x  %-46s = %s (%d)   [default: %s]' % (off, name, cur[0] if cur else '?', v, '/'.join(dict.fromkeys(dfl)) or '?'))
    elif kind == 'NUMERIC' and name:
        v = int.from_bytes(sec[off:off + e['size']], 'little')
        if show_all or v:
            print('NUM  %#06x  %-46s = %d' % (off, name, v))
