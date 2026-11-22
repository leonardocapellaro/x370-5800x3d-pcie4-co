#!/usr/bin/env python3
"""Active-PSP-directory attribution on a BIOS image (task 16 of the campaign).

What: given a raw 8902-family CAP image, prints (1) the version header of the
SMU blob carried under each PSP directory entry (compare against the kernel's
`ryzen_smu: SMU vX.Y.Z` line to name the ACTIVE directory), (2) the magic and
version of the PSP driver found at the inert Zen2 directory entry, (3) a
Thumb disassembly of that driver's strap-commit function (svc 0x7c =
write(addr,value,size); svc 0x7b = read(addr,buf,size)) and of its single
caller (gated on ctx[3]), with PC-relative literal values decoded inline, and
(4) the 24-entry x 12-byte chipset whitelist (devid FCH | flags b0 b1 b2 b3 |
selector; b3=1 => the entry reaches for the commit function).
Why: this script is the one that proved the chipset-check gate and the
Gen4-suppressing commit live together inside ONE signed PSP driver, which is
the structural reason Gen4+CO is excluded by construction (docs/05, docs/09).
It is also the worked example of the "$PSP directory parse" method (docs/03).
How: `python3 -I psp_active_dir.py <image.CAP>` (read-only; no write path).
Requires capstone.
"""
import sys, struct
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB

cap = open(sys.argv[1], 'rb').read()
# SMU blob locations per PSP directory entry (measured on 8902; docs/03)
SMUS = {'0xBC0B0500 sub1 @0x421400': 0x421400, '0xBC0B0500 sub0 @0x518400': 0x518400,
        '0xBC0C0140 @0x82be00 (e03)': 0x82be00, '0xBC0C0000 @0x6abe00': 0x6abe00}
print('== SMU version (header at +0x60); compare with the kernel `ryzen_smu: SMU vX.Y.Z`')
for n, o in SMUS.items():
    b = cap[o + 0x60:o + 0x64]
    print('  %-30s %d.%d.%d' % (n, b[2], b[1], b[0]))
O, S = 0x469f00, 0x1a790
blob = cap[O:O + S]
print('== PSP driver @CAP %#x: magic %r, ver %s, signed=%#x B + %#x B of signature' % (
    O, blob[0x10:0x14], blob[0x60:0x64][::-1].hex(), struct.unpack_from('<I', blob, 0x14)[0],
    S - 0x100 - struct.unpack_from('<I', blob, 0x14)[0]))
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)

def dis(a, b):
    while a < b:
        for i in md.disasm(blob[a:b], a):
            x = ''
            if i.mnemonic.startswith('ldr') and '[pc' in i.op_str:
                d = int(i.op_str.split('#')[1].rstrip(']'), 16)
                x = ' ; =%#x' % struct.unpack_from('<I', blob, ((i.address + 4) & ~3) + d)[0]
            print('   %#06x %s %s%s' % (i.address, i.mnemonic, i.op_str, x)); a = i.address + i.size
        if a < b: print('   %#06x .w16 %s' % (a, blob[a:a + 2].hex())); a += 2

print('== function 0x3230 (svc 0x7c = write(addr,value,size); svc 0x7b = read(addr,buf,size))')
dis(0x3230, 0x3366)
print('== sole caller (gated on ctx[3], ctx=0xe16ac0)')
dis(0xa9dc, 0xaa66)
print('== whitelist @CAP 0x480a70: devid FCH | flags b0 b1 b2 b3 | selector   (b3=1 => calls 0x3230)')
t = 0x480a70 - O
for k in range(24):
    e = blob[t + k * 12:t + k * 12 + 12]
    print('   %2d  %#06x | %s | %d   @CAP %#x' % (k, struct.unpack_from('<I', e)[0], e[4:8].hex(' '), e[8], 0x480a70 + k * 12))
