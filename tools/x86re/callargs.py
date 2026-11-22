#!/usr/bin/env python3
"""Per-direct-call-site argument survey of a PE32+ module (capstone, x64).

What: for every direct `call <imm>` in executable sections, records the call
site and the most recent immediate `mov` into the argument registers
(edx/ecx/r8d/r9d/rdx/rcx) made within the previous 0x30 bytes (the window is
reset by any call/jmp/ret). Run without a target it prints the 25 most-called
direct targets; with a target it prints each call site of that function and
the argument-register immediates still "hot" at the call.
Why: when Ghidra names a helper but the per-call semantics come from the
constant arguments, this tabulates them in one pass (e.g. which qid/flag each
caller passes before reaching a menu-gating routine).
How: `python3 -I callargs.py <pe.bin> [target_hex]`. Requires capstone.
"""
import sys, struct, collections
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

d = open(sys.argv[1], 'rb').read()
tgt = int(sys.argv[2], 16) if len(sys.argv) > 2 else None
pe = struct.unpack_from('<I', d, 0x3c)[0]
ns = struct.unpack_from('<H', d, pe + 6)[0]
oh = struct.unpack_from('<H', d, pe + 20)[0]
st = pe + 24 + oh
md = Cs(CS_ARCH_X86, CS_MODE_64)
md.skipdata = True
cnt = collections.defaultdict(list)
for i in range(ns):
    vs, va, rs, ro = struct.unpack_from('<IIII', d, st + 40 * i + 8)
    ch = struct.unpack_from('<I', d, st + 40 * i + 36)[0]
    if not ch & 0x20000000:  # IMAGE_SCN_MEM_EXECUTE
        continue
    last = {}
    for ins in md.disasm(d[ro:ro + min(vs, rs)], va):
        s = ins.op_str
        if ins.mnemonic == 'mov' and ',' in s:
            a, b = [x.strip() for x in s.split(',', 1)]
            # NOTE: precedence kept exactly as in the original tool
            # (the `and` binds the first `in`; `or` covers decimal immediates).
            if a in ('edx', 'ecx', 'r8d', 'r9d', 'rdx', 'rcx') and b.startswith('0x') or (a in ('edx', 'ecx', 'r8d', 'r9d') and b.isdigit()):
                last[a] = (int(b, 0), ins.address)
        if ins.mnemonic == 'call' and s.startswith('0x'):
            t = int(s, 16)
            cnt[t].append((ins.address, {k: hex(v[0]) for k, v in last.items() if ins.address - v[1] < 0x30}))
            last = {}
        elif ins.mnemonic in ('call', 'ret', 'jmp'):
            last = {}
if tgt is None:
    for t, l in sorted(cnt.items(), key=lambda kv: -len(kv[1]))[:25]:
        print(hex(t), len(l))
else:
    for a, l in cnt[tgt]:
        print('%06x' % a, l)
