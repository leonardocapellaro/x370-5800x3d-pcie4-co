#!/usr/bin/env python3
"""Produce the corrected .CMO profile for the A36 BIOS (task 93, CMO addendum).

Usage: fix_boost_profile.py <decompressed_profile.bin> <out_decompressed.bin>
(Re-compress afterwards with EDK2's reference compressor — see efitool.c.)

The only change: in section VARSTORE_OCMR_SETTINGS, the ASUS PBO-page item
"Max CPU Boost Clock Override": the hidden number @0x1a7f (stored = typed+1)
1351 -> 201, and the UTF-16 text @0x1a83 "1350" -> "200".
Reason: on A36 the value means "MHz above 4550" with a ceiling of 200; 1350
would be ignored and the stock ceiling would apply.
The section's hex text is re-emitted in the BIOS's exact format — checked by a
byte-identical re-emission of the UNMODIFIED section before any edit."""
import sys, struct, re

src, dst = sys.argv[1], sys.argv[2]
d = open(src, 'rb').read()
SEC = b'VARSTORE_OCMR_SETTINGS'
m = re.search(rb'\$ProfileData\(' + SEC + rb'\)\n', d)
assert m
a = m.end()
e = d.index(b'$End', a)
body = d[a:e]
raw = bytes.fromhex(body.decode())
assert len(raw) == 7611

def emit(b):
    # BIOS format: "%02X " per byte, "%02X\n" at the 16th byte of each line
    out = []
    for i, x in enumerate(b):
        out.append(('%02X\n' if i % 16 == 15 else '%02X ') % x)
    return ''.join(out).encode()

re0 = emit(raw)
assert body.startswith(re0), 're-emission format != original'
tail = body[len(re0):]
print('tail after hex: %r' % tail)
# expected state in the original profile
assert struct.unpack_from('<I', raw, 0x1a7f)[0] == 1351
old_s = '1350'.encode('utf-16-le')
new_s = '200'.encode('utf-16-le') + b'\0\0'
assert raw[0x1a83:0x1a83 + 8] == old_s and raw[0x1a83 + 8:0x1a83 + 40] == b'\0' * 32
n = bytearray(raw)
struct.pack_into('<I', n, 0x1a7f, 201)
n[0x1a83:0x1a83 + 8] = new_s
diff = [i for i in range(len(raw)) if raw[i] != n[i]]
print('changed section bytes:', [hex(i) for i in diff])
assert diff == [0x1a7f, 0x1a80, 0x1a83, 0x1a85, 0x1a87, 0x1a89]
nb = emit(bytes(n)) + tail
assert len(nb) == len(body)
out = d[:a] + nb + d[e:]
assert len(out) == len(d) == struct.unpack_from('<I', d, 0x30)[0]
open(dst, 'wb').write(out)
td = [i for i in range(len(d)) if d[i] != out[i]]
print('changed text characters: %d (offsets %s)' % (len(td), [hex(i) for i in td]))
