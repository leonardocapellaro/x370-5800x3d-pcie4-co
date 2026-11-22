#!/usr/bin/env python3
"""Extract the main DXE firmware volume from an 8902-family CAP image.

The big volumes are stored as one LZMA ALONE stream behind a GUID-defined
section. Measured container layout (task 49):
    GUID(16) + u16 DataOffset + u16 Attributes + u8[5] props + u64 usize + stream
i.e. the LZMA ALONE stream (starting with the 5 property bytes: lc/lp/pb
byte + u32 dictionary size) begins right AFTER the 4 bytes that follow the
GUID — at `guid_offset + 20` — regardless of the DataOffset field value.
The script scans every occurrence of the LZMA GUID, tries to decompress each,
and writes the LARGEST payload (the main DXE FV) to the output file.

Usage: fv_decompress.py <cap> <out_fv.bin>"""
import sys, lzma, hashlib

GUID_LZMA_ALT = bytes.fromhex('98584eee143959429d6edc7bd79403cf')

def main(cap_path, out_path):
    b = open(cap_path, 'rb').read()
    hits = []
    i = 0
    while True:
        i = b.find(GUID_LZMA_ALT, i)
        if i < 0:
            break
        hits.append(i)
        i += 1
    best = None
    for off in hits:
        raw = b[off + 20:]
        try:
            d = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
            data = d.decompress(raw)
        except Exception as e:
            print('  off %#x failed: %s' % (off, e))
            continue
        print('  LZMA GUID @%#x: decompressed %d B' % (off, len(data)))
        if best is None or len(data) > len(best[1]):
            best = (off, data)
    assert best, 'no valid LZMA section found'
    off, data = best
    open(out_path, 'wb').write(data)
    print('largest payload: @%#x -> %d B sha %s' %
          (off, len(data), hashlib.sha256(data).hexdigest()[:12]))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
