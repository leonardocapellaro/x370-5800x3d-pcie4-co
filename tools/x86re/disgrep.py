#!/usr/bin/env python3
"""Regex-grep a disassembly of a PE32/PE32+ module (capstone, x86/x64).

What: walks every section marked executable, linearly disassembles it
(skipdata on, so data islands never abort the pass) and prints every
instruction whose text matches a Python regex:
    address  raw-bytes  mnemonic operands
Why: locate stores/calls by instruction shape in seconds, before opening
Ghidra. This is how we found the two capability-flag zeroing stores
(`mov byte ptr [rbx+0xdf],bpl`) that A36 NOPs out, and how we survey any
x86 module extracted with tools/firmware/ffs_unpack.py.
How: `python3 -I disgrep.py <pe.bin> <python-regex>`. The optional third
argument is reserved (accepted, unused) — kept from the original tool.
Requires: capstone (`pip install capstone`).
"""
import sys, re, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_64, CS_MODE_32

d = open(sys.argv[1], 'rb').read()
rx = re.compile(sys.argv[2])
pe = struct.unpack_from('<I', d, 0x3c)[0]
mach = struct.unpack_from('<H', d, pe + 4)[0]
ns = struct.unpack_from('<H', d, pe + 6)[0]
oh = struct.unpack_from('<H', d, pe + 20)[0]
st = pe + 24 + oh
md = Cs(CS_ARCH_X86, CS_MODE_64 if mach == 0x8664 else CS_MODE_32)
md.skipdata = True
for i in range(ns):
    name = d[st + 40 * i:st + 40 * i + 8].rstrip(b'\0').decode('latin1')  # kept for clarity
    vs, va, rs, ro = struct.unpack_from('<IIII', d, st + 40 * i + 8)
    ch = struct.unpack_from('<I', d, st + 40 * i + 36)[0]
    if not ch & 0x20000000:  # IMAGE_SCN_MEM_EXECUTE
        continue
    for ins in md.disasm(d[ro:ro + min(vs, rs)], va):
        s = '%s %s' % (ins.mnemonic, ins.op_str)
        if rx.search(s):
            print('%06x  %-24s %s' % (ins.address, ins.bytes.hex(), s))
