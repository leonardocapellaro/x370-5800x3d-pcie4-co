#!/usr/bin/env python3
"""Xtensa L32R cross-reference scanner (who references this literal slot?).

What: walks a raw Xtensa code image; for every 3-byte L32R candidate (low
nibble of the opcode byte == 1, followed by a 16-bit immediate), computes the
literal-pool slot address  ((PC+3) & ~3) + sign_ext16(imm) << 2  and reports
every occurrence of the requested slot targets.
Why: in the SMU (Xtensa) the doorbell/strap tables are reached through L32R
pooled literals, not direct immediates — so a plain value grep misses them.
This scanner located the code referencing the candidate literal slots and,
with the base guessed correctly, confirmed which load base the blob uses
(task 12 era, docs/09). Run it with the load base you believe and the slot
offsets of interest.
How: `python3 -I l32r_scan.py <image.bin> <base_hex> <slot_hex> [<slot_hex>...]`
(slot addresses are base + slot; one report line per found program counter).
"""
import sys, struct

img = open(sys.argv[1], 'rb').read()
N = len(img)
base = int(sys.argv[2], 16)
targets_off = [int(a, 16) for a in sys.argv[3:]]
if not targets_off:
    sys.exit('usage: l32r_scan.py <image.bin> <base_hex> <slot_hex> [...]')


def signext16(v):
    return v - 0x10000 if v & 0x8000 else v


def scan(base, targets):
    """targets = VAs of literal slots; returns {target: [pcs]}"""
    hits = {t: [] for t in targets}
    for p in range(0, N - 3):
        if img[p] & 0xF != 1:
            continue
        imm = img[p + 1] | (img[p + 2] << 8)
        lit_va = ((base + p + 3) & ~3) + (signext16(imm) << 2)
        if lit_va in hits:
            hits[lit_va].append(p)
    return hits


targets = [base + s for s in targets_off]
h = scan(base, targets)
tot = sum(len(v) for v in h.values())
print(f"base {base:#x}: hits = {tot}")
for t, pcs in h.items():
    if pcs:
        print(f"  slot {t:#x} <- pcs {[hex(p) for p in pcs]}")
