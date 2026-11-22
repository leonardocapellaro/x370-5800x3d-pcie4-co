#!/usr/bin/env python3
"""Thumb function prologue scanner + containing-function outline.

What: scans a raw Thumb blob for function prologues — `push {regs,lr}` in the
16-bit encodings (0xB5xx, plus 0xB5F0/0xB5FF) and the 32-bit `0xE92D` push
with the LR bit set — then (given a target address) reports the candidate
function that contains it: the last prologue before the target, disassembled
forward with bl/b branch targets resolved to absolute blob offsets.
Why: PSP/OS ARM blobs carry no symbols. Locating the function around a call
site (the dispatch switch, a handler, a doorbell store) by walking back to its
prologue was our standard first step in the chain analysis (docs/09). This is
the reusable core of that method — the campaign run pointed it at the driver
function calling the executor.
How: `python3 -I thumb_funcmap.py <body.bin> [target_hex [end_hex]]`.
Without a target it prints the prologue table (offsets + kind). Requires
capstone.
"""
import sys, struct
from capstone import Cs, CS_ARCH_ARM, CS_MODE_LITTLE_ENDIAN, CS_MODE_THUMB

body = open(sys.argv[1], 'rb').read()
target = int(sys.argv[2], 16) if len(sys.argv) > 2 else None
end = int(sys.argv[3], 16) if len(sys.argv) > 3 else None
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_LITTLE_ENDIAN)

# prologues: push {…, lr}  =>  0xB5xx (16-bit) or 0xE92D with the lr bit
# (0x4000) in the second halfword
prologues = []
for i in range(0, len(body) - 4, 2):
    hw = struct.unpack_from("<H", body, i)[0]
    if (hw & 0xFF00) == 0xB500 or hw == 0xB5F0 or hw == 0xB5FF:
        prologues.append((i, "push16"))
    elif hw == 0xE92D:
        hw2 = struct.unpack_from("<H", body, i + 2)[0]
        if hw2 & 0x4000:  # lr present in the push
            prologues.append((i, "push32"))


def disasm(start, stop):
    for ins in md.disasm(body[start:stop], start):
        txt = f"{ins.mnemonic} {ins.op_str}"
        if ins.mnemonic in ("bl", "b", "b.w") and ins.op_str.startswith("#"):
            d = int(ins.op_str[1:], 0)
            if d & 0x80000000:
                d -= 0x100000000
            base = (ins.address + 4) & ~3 if ins.mnemonic == "bl" else ins.address + 4
            txt = f"{ins.mnemonic} {base + d:#x}"
        print(f"  {ins.address:#06x}  {txt}")


if target is None:
    print(f"{len(prologues)} prologues in {len(body)} bytes")
    for p, k in prologues[:200]:
        print(f"  {p:#06x} {k}")
else:
    prev = [p for p, _ in prologues if p <= target]
    print(f"prologues before {target:#x} (last 8): {[hex(p) for p in prev[-8:]]}")
    fn_start = prev[-1] if prev else None
    print(f"candidate function containing the caller: {fn_start:#x}")
    if fn_start is not None:
        stop = end if end is not None else min(fn_start + 0x100, len(body))
        print(f"\n== function from {fn_start:#x} to {stop:#x} ==")
        disasm(fn_start, stop)
