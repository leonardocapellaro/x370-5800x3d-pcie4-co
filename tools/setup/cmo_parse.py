#!/usr/bin/env python3
"""Reader for an ASUS BIOS user profile (a decompressed `.CMO`): header,
schema (typedef text) and the `$ProfileData(NAME)` hex-text sections.
Use `efi11_decompress.py` first to get the plain stream.

Usage: cmo_parse.py <bin>
Prints one line per section: name, text offset range, decoded byte length.
"""
import re, sys

def parse(d):
    """Return {NAME: (text_start, text_end, raw_bytes)} for every section."""
    secs = {}
    it = list(re.finditer(rb'\$ProfileData\((\w+)\)\n', d))
    for k, m in enumerate(it):
        end = it[k + 1].start() if k + 1 < len(it) else len(d)
        body = d[m.end():end].split(b"$End")[0]
        secs[m.group(1).decode()] = (
            m.end(), end,
            bytes.fromhex(body.decode('ascii').replace('\n', ' ').replace('\r', ' ').strip('\0 ')))
    return secs

if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    for n, (a, b, v) in parse(d).items():
        print('%-34s txt %#07x..%#07x  %5d bytes' % (n, a, b, len(v)))
    print('tail:', d[-40:])
