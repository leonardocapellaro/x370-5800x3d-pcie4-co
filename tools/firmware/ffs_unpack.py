#!/usr/bin/env python3
"""Extract one FFS module from a decompressed main FV and split its sections,
decompressing GUID_DEFINED (LZMA) sections.

Usage: ffs_unpack.py <fv.bin> <guid-prefix> <out-stem>
Writes <out-stem>.ffs (raw file) and <out-stem>.bin (concatenated section bodies).

Input convention: the volume as produced by fv_decompress.py (the leading
16 bytes of the payload are skipped before reading the FV header fields).
GUID_DEFINED section layout (measured, task 49): section header 4 B +
GUID 16 B + u16 DataOffset + u16 Attributes + LZMA ALONE payload — the
payload (props byte first) starts right after those 24 bytes; the DataOffset
field is not used as the payload offset here (measured on official images).
props_ok() validates the 5 LZMA ALONE property bytes (lc/lp/pb + dict size)
and clamps them like the firmware does; if a direct decode fails, the payload
window is scanned for a valid property start (some odd sections carry extra
prefix bytes)."""
import sys, struct, uuid, lzma, hashlib

G_LZMA = bytes.fromhex('98584eee143959429d6edc7bd79403cf')

def align(n, a=8):
    return (n + a - 1) & ~(a - 1)

def sections(b):
    """Yield (offset, type, raw_section) for the sections of an FFS file.
    Note: in this firmware the raw PE32 section type is 0x10 (AMI convention,
    not EDK2's 0x01); 0x02 is GUID_DEFINED; 0x13 is DXE_DEPEX."""
    o = 24
    while o + 4 <= len(b):
        n = int.from_bytes(b[o:o + 3], 'little')
        t = b[o + 3]
        if n < 4 or o + n > len(b):
            return
        yield o, t, b[o:o + n]
        o = align(o + n, 4)

def props_ok(p):
    """Validate LZMA ALONE property bytes; return decoder kwargs or None."""
    if len(p) < 5 or p[0] >= 9 * 5 * 5:
        return None
    lc = p[0] % 9
    r = p[0] // 9
    lp = r % 5
    pb = r // 5
    dsz = struct.unpack_from('<I', bytes(p) + b'\0', 1)[0]
    if dsz == 0xFFFFFFFF:
        dsz = 1 << 26
    elif dsz == 0:
        dsz = 1 << 12
    else:
        dsz = dsz if not (dsz & (dsz - 1)) else 1 << max(12, (dsz - 1).bit_length())
        if dsz > 1 << 26:
            dsz = 1 << 26
    return dict(lc=min(lc, 4), lp=lp, pb=pb, dict_size=1 << 26)

def base_for(fv):
    """Return the volume with the 16-byte AMI prefix removed (if present)."""
    for h in (0x10, 0x00):
        if fv[h + 40:h + 44] == b'_FVH':
            return fv[h:]
    raise SystemExit('no _FVH signature found')

def find_file(fv, guid_prefix):
    """Locate the first file whose GUID starts with guid_prefix (build.py
    walk recipe — same as fv_ls.py)."""
    length = struct.unpack_from('<Q', fv, 32)[0]
    extoff = struct.unpack_from('<H', fv, 52)[0]
    if extoff:
        eh = struct.unpack_from('<I', fv, extoff + 16)[0]
        pos = (extoff + eh + 7) & ~7
    else:
        pos = (struct.unpack_from('<H', fv, 48)[0] + 7) & ~7
    while pos + 24 <= length and fv[pos:pos + 24] != b'\xff' * 24:
        h = fv[pos:pos + 24]
        n = int.from_bytes(h[20:23], 'little')
        if n < 24 or pos + n > length:
            break
        if str(uuid.UUID(bytes_le=h[:16])).startswith(guid_prefix):
            return pos, n
        pos = (pos + n + 7) & ~7
    return None

def main(fv_path, guid_prefix, out_path):
    fv = base_for(open(fv_path, 'rb').read())
    found = find_file(fv, guid_prefix)
    assert found, 'module %s not found' % guid_prefix
    p, n = found
    f = fv[p:p + n]
    print('module %s @%#x size=%d sha=%s' %
          (guid_prefix, p, n, hashlib.sha256(f).hexdigest()[:12]))
    open(out_path + '.ffs', 'wb').write(f)
    parts = []
    for o, t, sec in sections(f):
        print('  section @+%#x type=%#x size=%d' % (o, t, len(sec)))
        if t == 0x02:
            g = sec[4:20]
            payload = sec[24:]
            pr = props_ok(payload[:5])
            if pr:
                try:
                    d = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(payload)
                    parts.append((t, d))
                    print('    LZMA ok -> %d B' % len(d))
                    continue
                except Exception as e:
                    print('    lzma failed (%s); scanning window' % str(e)[:60])
            ok = False
            for ppos in range(20, min(60, len(sec))):
                if props_ok(sec[ppos:ppos + 5]) is None:
                    continue
                try:
                    d = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(sec[ppos:])
                except Exception:
                    continue
                parts.append((t, d))
                print('    LZMA @+%#x -> %d B' % (ppos, len(d)))
                ok = True
                break
            if not ok:
                parts.append((t, sec[24:]))
        else:
            parts.append((t, sec[4:]))
    with open(out_path + '.bin', 'wb') as fh:
        for t, d in parts:
            fh.write(d)
    print('  total decompressed: %d B' % sum(len(d) for _, d in parts))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
