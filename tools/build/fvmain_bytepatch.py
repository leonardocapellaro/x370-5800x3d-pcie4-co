#!/usr/bin/env python3
"""A36 / PBO-CO-NATIVE (task 93, front B): the final menu build for the 5800X3D,
kept as the reference example of our CAP pipeline.

Base: the OFFICIAL ASUS 8902 (sha 04ddae2d...). None of the A23/A28 tricks:
no PSP NOPs, no 11 AMIBCP front bytes (TSE) — only x86 DXE code inside FVMAIN.

Three changes, all in x86 modules NOT signed by AMD:

 (1) The "AMD Overclocking" menu driver (trio a2702a3c / 55538d1e / 07d279a1 —
     one copy per family group; the Vermeer one is a2702a3c): its capability
     routine sets AOD_SETUP[0xdf] (PcdVfrForm_AOD_PBO) in the table and then
     ZEROES it at two points (a missing SMU capability bit 1; the read-only
     "OC disabled" fuse read). The two `mov [rbx+0xdf],bpl` stores become NOP.
     Effect: [0xdf] stays 1 => the ASUS PBO link (SUPPRESS_IF qid 0x4f0==1)
     and the AMD PBO page (qid 0x193) open under their ORIGINAL condition;
     inside AMD PBO, Advanced mode, the "Curve Optimizer" link already has
     flag 1.
 (2) The Vermeer SMU DXE driver (9a29bbe9): the base of "Max CPU Boost Clock
     Override" came from a fuse field ((SMN 0x5D2C4 >> 17) & 0xff) * 25; it
     becomes the constant 4550 MHz (the 5800X3D stock Fmax). The menu number
     becomes "MHz above 4550".
 (3) Same code: the ceiling of the positive value drops from 2000 to 200
     (the AMD menu's native range). A stale pre-A36 value >200 left in NVRAM
     => target = 4550 (stock), never 4550+1350.

Pipeline = the A28 one (which booted): decompress the FVMAIN LZMA-ALONE
stream, swap bytes in the raw PE32 sections, recompress FVMAIN with the
ORIGINAL properties, new stream <= original, in-place swap with FF padding.
No other byte of the image changes.

Usage: fvmain_bytepatch.py <official_8902.CAP> <out.CAP>
"""
import struct, lzma, uuid, hashlib, json, sys
from pathlib import Path

INPUT = Path(sys.argv[1])
OUT = Path(sys.argv[2])
INPUT_SHA = '04ddae2d0650353ec7bafa50a281528791a74694960f2104ac9d53657b0b6bba'
LZMA_GUID = bytes.fromhex('98584eee143959429d6edc7bd79403cf')
USIZE = 16162832
NICE = 273
NOP7 = bytes.fromhex('0f1f8000000000')
STORE_DF = bytes.fromhex('4088abdf000000')          # mov byte ptr [rbx+0xdf], bpl
BASE_OLD = bytes.fromhex('41c1eb11410fb6db6bdb19')  # shr r11d,0x11; movzx ebx,r11b; imul ebx,ebx,0x19
BASE_NEW = bytes.fromhex('bbc6110000660f1f440000')  # mov ebx,4550; nop6
LIM_OLD = bytes.fromhex('3dd0070000')               # cmp eax,2000
LIM_NEW = bytes.fromhex('3dc8000000')               # cmp eax,200
# (guid, [(offset in PE, old, new, label)])
PATCHES = [
    ('a2702a3c-62fd-402d-b8c3-1d18f6c6fde5',
     [(0x16ac, STORE_DF, NOP7, 'AOD[0xdf] zeroing by capability'),
      (0x18ad, STORE_DF, NOP7, 'AOD[0xdf] zeroing by fuse read')]),
    ('55538d1e-b4c5-4bd5-b594-9b5ba9774f1e',
     [(0x16ac, STORE_DF, NOP7, 'AOD[0xdf] zeroing by capability'),
      (0x18ad, STORE_DF, NOP7, 'AOD[0xdf] zeroing by fuse read')]),
    ('07d279a1-34e4-4168-993b-178b3acc68ef',
     [(0x175c, STORE_DF, NOP7, 'AOD[0xdf] zeroing by capability'),
      (0x195d, STORE_DF, NOP7, 'AOD[0xdf] zeroing by fuse read')]),
    ('9a29bbe9-74bb-41d3-bcae-6b086e0fe0c5',
     [(0x8e9, BASE_OLD, BASE_NEW, 'boost base := 4550 MHz'),
      (0x90f, LIM_OLD, LIM_NEW, 'boost positive ceiling 2000 -> 200')]),
]

def sha(b):
    return hashlib.sha256(b).hexdigest()

def get_fvmain(cap):
    occ = []
    i = 0
    while True:
        j = cap.find(LZMA_GUID, i)
        if j < 0:
            break
        if struct.unpack_from('<Q', cap, j + 25)[0] == USIZE:
            occ.append(j)
        i = j + 1
    assert len(occ) == 1, 'unique envelope: %r' % occ
    G = occ[0]
    d = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    fv = d.decompress(cap[G + 20:])
    assert d.eof and len(fv) == USIZE
    return G, fv

def stream_len(cap, G):
    lo, hi = 13, len(cap) - G
    while lo < hi:
        mid = (lo + hi) // 2
        d = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
        try:
            d.decompress(cap[G + 20:G + 20 + mid])
            if d.eof:
                hi = mid
            else:
                lo = mid + 1
        except Exception:
            lo = mid + 1
    return lo

def files(fv):
    length = struct.unpack_from('<Q', fv, 32)[0]
    extoff = struct.unpack_from('<H', fv, 52)[0]
    if extoff:
        eh = struct.unpack_from('<I', fv, extoff + 16)[0]
        pos = (extoff + eh + 7) & ~7
    else:
        pos = (struct.unpack_from('<H', fv, 48)[0] + 7) & ~7
    assert length == len(fv)
    out = []
    while pos + 24 <= length and fv[pos:pos + 24] != b'\xff' * 24:
        h = fv[pos:pos + 24]
        n = int.from_bytes(h[20:23], 'little')
        if n < 24 or pos + n > length:
            break
        out.append((pos, str(uuid.UUID(bytes_le=bytes(h[:16]))), n))
        pos = (pos + n + 7) & ~7
    return out

def secs(f):
    out = []
    o = 24
    while o + 4 <= len(f):
        n = int.from_bytes(f[o:o + 3], 'little')
        t = f[o + 3]
        if n < 4 or o + n > len(f):
            break
        out.append((o, n, t))
        o = (o + n + 3) & ~3
    return out

def lz_filters(props5):
    p = props5[0]
    lc = p % 9
    lp = (p // 9) % 5
    pb = (p // 45) % 9
    ds = int.from_bytes(props5[1:5], 'little')
    return [{'id': lzma.FILTER_LZMA1, 'lc': lc, 'lp': lp, 'pb': pb,
             'dict_size': ds, 'nice_len': NICE}]

def main():
    cap = INPUT.read_bytes()
    assert sha(cap) == INPUT_SHA, 'base != official 8902'
    G, fv = get_fvmain(cap)
    slen = stream_len(cap, G)
    print('FVMAIN @%#x stream=%d' % (G, slen))
    sl = fv[16:]
    fl = files(sl)
    fv2 = bytearray(fv)
    rep = []
    for guid, plist in PATCHES:
        hit = [(o, n) for o, g, n in fl if g == guid]
        assert len(hit) == 1, 'unique module %s: %r' % (guid, hit)
        mo, mn = hit[0]
        mf = sl[mo:mo + mn]
        assert mf[19] & 0x40 == 0, '%s has data checksum (attr 0x40)' % guid
        pe = [s for s in secs(mf) if s[2] == 0x10]
        assert len(pe) == 1, 'one PE32 section in %s' % guid
        so, sn, _ = pe[0]
        body = mf[so + 4:so + sn]
        assert body[:2] == b'MZ'
        for off, old, new, label in plist:
            assert len(old) == len(new)
            assert body[off:off + len(old)] == old, \
                '%s @%#x: %s != %s' % (guid, off, body[off:off + len(old)].hex(), old.hex())
            assert body.count(old) <= 2 or old == LIM_OLD
            a = 16 + mo + so + 4 + off
            assert bytes(fv2[a:a + len(old)]) == old
            fv2[a:a + len(new)] = new
            rep.append({'module': guid, 'pe_off': hex(off), 'fv_off': hex(a),
                        'old': old.hex(), 'new': new.hex(), 'what': label})
            print('%s @PE %#x (FV %#x): %s -> %s  [%s]' %
                  (guid[:8], off, a, old.hex(), new.hex(), label))
    assert len(fv2) == USIZE
    nd = sum(1 for i in range(USIZE) if fv2[i] != fv[i])
    print('FV diff: %d bytes' % nd)
    filt = lz_filters(cap[G + 20:G + 25])
    c = lzma.LZMACompressor(format=lzma.FORMAT_RAW, filters=filt)
    raw = c.compress(bytes(fv2)) + c.flush()
    new_stream = cap[G + 20:G + 25] + struct.pack('<Q', USIZE) + raw
    rt = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    assert rt.decompress(new_stream) == bytes(fv2) and rt.eof
    assert len(new_stream) <= slen, 'stream %d > %d' % (len(new_stream), slen)
    print('FVMAIN stream: new %d <= original %d (margin %d)' %
          (len(new_stream), slen, slen - len(new_stream)))
    newcap = bytearray(cap)
    newcap[G + 20:G + 20 + slen] = new_stream + b'\xff' * (slen - len(new_stream))
    assert len(newcap) == len(cap)
    G3, fv3 = get_fvmain(bytes(newcap))
    assert G3 == G and fv3 == bytes(fv2)
    assert bytes(newcap[:G + 20]) == cap[:G + 20] and bytes(newcap[G + 20 + slen:]) == cap[G + 20 + slen:]
    OUT.write_bytes(bytes(newcap))
    out = {'input_sha256': INPUT_SHA, 'base': 'ASUS 8902 official',
           'sha256': sha(newcap), 'bytes': len(newcap), 'fv_diff_bytes': nd,
           'patches': rep,
           'fvmain': {'envelope': hex(G), 'stream_old': slen, 'stream_new': len(new_stream)}}
    OUT.with_name('patch.json').write_text(json.dumps(out, indent=2) + '\n')
    print('sha256:', sha(newcap))

if __name__ == '__main__':
    main()
