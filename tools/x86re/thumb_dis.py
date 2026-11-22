#!/usr/bin/env python3
"""Thumb (16-bit ARM instructions, little-endian) disassembler for a raw blob.

What: decodes [start, start+length) of a raw file as Thumb and prints
`address  mnemonic  operands` per instruction.
Why: the PSP BL/OS drivers and the ARM-side SMU bodies in this firmware are
Thumb/ARM; this is the quick look-window used before scripting Ghidra
(docs/09). For bl/b target resolution see tools/psp/thumb_funcmap.py.
How: `python3 -I thumb_dis.py <blob.bin> <start_hex> <length_hex>`.
Requires capstone.
"""
import sys
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_LITTLE_ENDIAN

body = open(sys.argv[1], 'rb').read()
start = int(sys.argv[2], 16)
length = int(sys.argv[3], 16)
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_LITTLE_ENDIAN)
for i in md.disasm(body[start:start + length], start):
    print("%08x  %-12s %s" % (i.address, i.mnemonic, i.op_str))
