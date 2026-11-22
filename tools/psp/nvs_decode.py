#!/usr/bin/env python3
"""Decode the zlib-compressed NVS block of an SPI dump and dump its strings.

What: locates the NVS (NVIDIA-style SPI configuration blob carried in this
board family's image) inside one or more raw SPI dumps at region 0x90000..
0xA0000, decompresses the zlib stream behind the 'NVS' tag, prints the
decoded size + SHA-256, a 256-byte hexdump, and every ASCII run of length >=4
(up to 40). Writes the decoded payload to <out-dir>/NVS_<name>.bin.
Why: NVS contents diverged between a boot that cleared configuration and one
that did not; comparing the decoded text lists (names F5/CLRTC never expose)
was how we traced a poisoned settings region (task 05/06 era, docs/12).
How: `python3 -I nvs_decode.py [--out DIR] dump1.bin [dump2.bin ...]`
(the dump file stem is used as <name>; DIR defaults to the current directory).
"""
import argparse, hashlib, re, sys, zlib
from pathlib import Path

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', default='.', help='directory for NVS_<name>.bin')
    ap.add_argument('dumps', nargs='+')
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name in args.dumps:
        p = Path(name)
        buf = p.read_bytes()
        # whole NVS region: scan until the stream end (fixed placement, 8902 family)
        region = buf[0x90000:0xA0000]
        if region[:3] != b'NVS':
            print(f"{p.name}: no 'NVS' tag at 0x90000 — skipping")
            continue
        d = zlib.decompressobj()
        try:
            dec = d.decompress(region[3:])
        except Exception as e:
            print(f"{p.name}: zlib error: {e}")
            continue
        print(f"\n===== NVS {p.stem} =====")
        print(f"decoded: {len(dec)} bytes; sha={hashlib.sha256(dec).hexdigest()}")
        print(f"zlib stream consumed: {len(region) - len(d.unconsumed_tail) - 3} bytes (of {len(region)-3})")
        (out / f'NVS_{p.stem}.bin').write_bytes(dec)
        print("first 256 bytes:")
        for i in range(0, 256, 16):
            chunk = dec[i:i + 16]
            txt = "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)
            print(f"  {i:04x}: {chunk.hex(' '):48s} {txt}")
        # ASCII/UTF16-ish strings in the content
        strs = re.findall(rb"[\x20-\x7e]{4,}", dec)
        print(f"ASCII strings >=4: {len(strs)}")
        for s in strs[:40]:
            print("   ", s.decode())
    return 0

if __name__ == '__main__':
    sys.exit(main())
