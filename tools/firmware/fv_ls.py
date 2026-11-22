#!/usr/bin/env python3
"""List the FFS files of a decompressed firmware volume (FVMAIN-style).

The image starts with a 16-byte AMI prefix (its ZeroVector), then the
standard EFI_FIRMWARE_FILE_SYSTEM2 header: FsGuid, FvLength(u64), Signature
'_FVH', Attributes, HeaderLength(u16), Checksum, ExtHeaderOffset(u8).
The file store begins after the volume EXTENDED header when present (this
is how the firmware itself walks it — recipe used unchanged by every CAP
build we shipped).

Usage: fv_ls.py <fv.bin> <listing.txt>"""
import sys, hashlib, struct, uuid

def align(n, a):
    return (n + a - 1) & ~(a - 1)

def base_for(fv):
    """Return the volume with the 16-byte AMI prefix removed (if present):
    detect the standard header by '_FVH' at prefix+40."""
    for h in (0x10, 0x00):
        if fv[h + 40:h + 44] == b'_FVH':
            return fv[h:]
    raise SystemExit('no _FVH signature found')

def files(fv):
    """Yield (offset, GUID string, size, file_type) — build.py recipe."""
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
        out.append((pos, str(uuid.UUID(bytes_le=bytes(h[:16]))), n, h[18]))
        pos = (pos + n + 7) & ~7
    return out

def main(path, out):
    fv = base_for(open(path, 'rb').read())
    fl = files(fv)
    with open(out, 'w') as f:
        f.write('FV %s len=%d\n' % (path, len(fv)))
        for p, g, sz, t in fl:
            f.write('%#010x %s type=%#x size=%d sha=%s\n' %
                    (p, g, t, sz, hashlib.sha256(fv[p:p + sz]).hexdigest()[:16]))
    print('%d files in %s' % (len(fl), path))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
