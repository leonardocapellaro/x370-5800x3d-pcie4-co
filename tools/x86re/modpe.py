#!/usr/bin/env python3
"""Extract a module's raw PE32 body (and its UI name) from a decompressed
main firmware volume, selected by GUID.

What: given the output of tools/firmware/fv_decompress.py (or any
FVMAIN-style volume), finds the FFS file(s) whose GUID is listed on the
command line, decompresses their GUID_DEFINED (type 0x02) LZMA sections
recursively, and writes <outdir>/<guid8>.pe.bin — the raw PE32 you can feed
to tools/x86re/disgrep.py or callargs.py. The UI name (section type 0x15,
UTF-16LE) is printed with the module SHA-256 (first 12 hex).
Why: one-line "give me the driver" step between FV listing and x86 RE.
How: `python3 -I modpe.py <fvmain.bin> <outdir> <guid> [<guid>...]`.
Note: in this firmware family the raw PE32 section type is 0x10 (AMI
convention), NOT EDK2's 0x01 — see docs/03. The volume walk tolerates the
16-byte AMI ZeroVector prefix (auto-detected via '_FVH' at +40).
"""
import sys, struct, lzma, hashlib, uuid

LZMA_GUID = bytes.fromhex('98584eee143959429d6edc7bd79403cf')

def base_for(fv):
    """Return the volume with the 16-byte AMI prefix removed (if present)."""
    for h in (0x10, 0x00):
        if fv[h + 40:h + 44] == b'_FVH':
            return fv[h:]
    raise SystemExit('no _FVH signature found')

def files(fv):
    """Yield (offset, GUID string, size) — the build.py FFS walk recipe
    (same as tools/firmware/fv_ls.py)."""
    length = struct.unpack_from('<Q', fv, 32)[0]
    extoff = struct.unpack_from('<H', fv, 52)[0]
    if extoff:
        eh = struct.unpack_from('<I', fv, extoff + 16)[0]
        pos = (extoff + eh + 7) & ~7
    else:
        pos = (struct.unpack_from('<H', fv, 48)[0] + 7) & ~7
    out = []
    while pos + 24 <= length and fv[pos:pos + 24] != b'\xff' * 24:
        h = fv[pos:pos + 24]
        n = int.from_bytes(h[20:23], 'little')
        if n < 24 or pos + n > length:
            break
        out.append((pos, str(uuid.UUID(bytes_le=bytes(h[:16]))), n))
        pos = (pos + n + 7) & ~7
    return out

def walk(bl, o=0):
    """Flatten the section list of one FFS file: GUID_DEFINED/LZMA sections
    are decompressed and re-walked; everything else is returned as
    (type, body-past-4-byte-header). Inner sections are 4-byte aligned."""
    r = []
    while o + 4 <= len(bl):
        n = int.from_bytes(bl[o:o + 3], 'little')
        t = bl[o + 3]
        if n < 4 or o + n > len(bl):
            break
        if t == 0x02 and bl[o + 4:o + 20] == LZMA_GUID:
            do = struct.unpack_from('<H', bl, o + 20)[0]
            r += walk(lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
                      .decompress(bl[o + do:o + n]))
        else:
            r.append((t, bl[o + 4:o + n]))
        o = (o + n + 3) & ~3
    return r

def main(fv_path, out, guids):
    buf = base_for(open(fv_path, 'rb').read())
    for o, g, n in files(buf):
        if g in guids:
            secs = walk(buf[o:o + n], 24)
            nm = next((x.decode('utf-16-le').rstrip('\0') for t, x in secs if t == 0x15), '?')
            pe = next((x for t, x in secs if t == 0x10), None)
            if pe is None:
                print(g, nm, 'no PE', [hex(t) for t, _ in secs])
                continue
            p = '%s/%s.pe.bin' % (out, g[:8])
            open(p, 'wb').write(pe)
            print(g, nm, len(pe), hashlib.sha256(pe).hexdigest()[:12], p)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], set(sys.argv[3:]))
