#!/usr/bin/env python3
"""Read-only literal census for the PSP/SMU banked-window protocol.

What: for every input file (or *.bin under each input directory), records the
exact byte offsets where each watch value appears in little-endian and
big-endian form, with file size + SHA-256, into a JSON report. Watch values
are the banked-window doorbell/status addresses (bank 0 and bank 1 address and
data ports) and the window token 0xFFFE0000 used by the PSP-side commit
prologue (docs/09, docs/10).
Why: the writer census — we scanned every decoded LZMA payload of BOTH board
bases (~74.7 MB decoded, ~5.3 M instructions when combined with the disasm
scan) for anyone holding these constants. Result: zero writers in flash, on
either side — the clamp writer is NBIO on-chip microcode, outside every
offline-readable container (M18/M19, docs/10). This script is the literal
half of that census; it says nothing about executability.
How: `python3 -I census_window_literals.py <report.json> <file|dir> [...]`.
This does not infer that a hit is executable code, nor that an absence
excludes computed addressing. It records exact byte offsets only.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

VALUES = {
    "addr_bank0_address_port_0x090467ac": 0x090467AC,
    "addr_bank0_data_port_0x090467b0": 0x090467B0,
    "addr_bank1_address_port_0x090477ac": 0x090477AC,
    "addr_bank1_data_port_0x090477b0": 0x090477B0,
    "window_token_0xfffe0000": 0xFFFE0000,
}


def offsets(data: bytes, needle: bytes) -> list[int]:
    result, start = [], 0
    while True:
        at = data.find(needle, start)
        if at < 0:
            return result
        result.append(at)
        start = at + 1


def examine(label: str, path: Path) -> dict:
    data = path.read_bytes()
    hits = {}
    for name, value in VALUES.items():
        hits[name] = {
            "le": offsets(data, value.to_bytes(4, "little")),
            "be": offsets(data, value.to_bytes(4, "big")),
        }
    return {
        "label": label,
        "path": str(path),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "hits": hits,
    }


def inputs(paths: list[str]):
    """Yield (label, path) — directories expand to their sorted *.bin set."""
    for a in paths:
        p = Path(a)
        if p.is_dir():
            for q in sorted(p.glob("*.bin")):
                yield p.name, q
        else:
            yield p.stem, p


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit("usage: census_window_literals.py <report.json> <file|dir> [...]")
    out = Path(sys.argv[1])
    records = [examine(label, path) for label, path in inputs(sys.argv[2:])]
    out.write_text(json.dumps({"patterns": VALUES, "records": records}, indent=2) + "\n")
    print(f"wrote {out} ({len(records)} files)")


if __name__ == "__main__":
    main()
