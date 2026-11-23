# Getting PCIe Gen4 and Curve Optimizer on an X370 board with a Ryzen 5800X3D

A complete, documented reverse-engineering case study of ASUS BIOS 8902 for the
**ROG Crosshair VI Hero (X370)** running a **Ryzen 7 5800X3D** — including the
firmware paths that decide PCIe link speed, what the chipset/PSP validation
actually does, how AMD's menu capability flags work, and roughly **70 offline
built+validated BIOS builds** behind ~40 board flashes (every flash done
manually by the human owner, zero bricks, zero fuse touches).

This repository contains **analysis, tools and hashes — no firmware**. You
supply your own BIOS images; the tools never embed any.

## The two results people actually want

Start from what the board **ships with**, because it frames everything below: on stock
firmware, an X370 board with a Ryzen 5000 CPU such as the 5800X3D has **neither** feature —
PCIe is clamped to Gen3 (no official BIOS of this board — or of X370/X470 generally, in any
manufacturer — ever offered Gen4 with Ryzen 5000), and Curve Optimizer is not in the menus at
all on X3D parts (the capability gate is zeroed). We got each half working on this board;
the story is what it took, and why the two halves cannot meet.

| | PCIe Gen4 | Curve Optimizer / PBO | How |
|---|---|---|---|
| **Stock 8902** (starting point) | Gen3 — the chipset check writes the anti-Gen4 strap every boot | **absent from the menus** on X3D (capability flag zeroed) | nothing — this is the "neither" every owner of this combo lives with |
| **Build "RC1"** (V2 era) | **works** (x16 GPU + x4 NVMe, measured) | refused by SMU (`0x000000FF`) | PSP validation request 9 is skipped (`SKIP_PSP`) and the "BIOS boot done" mailbox call is NOPed — the chipset/strap check never runs, and with it the check that would feed the CO state |
| **Build "A36"** (final build; the accepted daily line was A28/A23) | Gen3 (stock clamp intact) | **works, natively, in the menus** (per the IFR analysis; the A36 on-board confirmation — flash 39 — was pending at log close, docs/13) | official 8902 + exactly **37 bytes** of x86 patches in unsigned DXE modules: 6 capability-flag stores NOPed (PBO + Curve Optimizer pages appear) + boost base `:= 4550 MHz` with a ±200 menu range |

The headline negative — and the most useful part of this study: **Gen4 + CO in
one BIOS is excluded by construction** on this platform/BIOS. The same signed
PSP transaction that validates the platform writes the anti-Gen4 strap; every
attempt to decouple them closed with measurements — a 30-entry dead-end
registry (M1–M30), from SMN reachability maps to a PSP-driver re-audit. See
[docs/05](docs/05-gen4-the-clamp.md) and the [M-registry](docs/10-negative-results.md).

## Contents

- [01 — Overview & conclusions first](docs/01-overview.md)
- [02 — Methodology (multi-AI offline workflow, prediction matrices, errata discipline)](docs/02-methodology.md)
- [03 — Firmware anatomy](docs/03-firmware-anatomy.md) (FV map, LZMA envelope, FFS checksums, the VZL1 "compression" that isn't, PSP directory)
- [04 — Boot timeline](docs/04-boot-timeline.md) (SEC→PEI→DXE→PSP/SMU, the 38-request mailbox sequence with the clamp call measured)
- [05 — The Gen4 clamp](docs/05-gen4-the-clamp.md) (who clamps Gen3, where, and why the writer is out of reach)
- [06 — The skip path & the era problem](docs/06-gen4-skip-and-era.md) (how RC1 got Gen4, why CO dies there, the 7306→7403 official policy shift)
- [07 — Curve Optimizer & PBO](docs/07-co-pbo-menus.md) (hidden menus, capability flags, boost formula, `.CMO` profiles, the 37-byte build)
- [08 — SMN probes](docs/08-smn-probes.md) (read-only CF8/CFC probing from custom DXE/PEI modules; reachability map)
- [09 — Reverse-engineering the PSP side](docs/09-psp-driver-re.md) (Xtensa drivers, the `ctx[3]` gate, commit mechanism, two censuses that found nothing — and what that proves)
- [10 — Negative results, all of them](docs/10-negative-results.md) (M1–M30 registry + 15 closing doors)
- [11 — Build catalog](docs/11-build-catalog.md) (every CAP we made: base, sha, flash number, verdict)
- [12 — Timeline](docs/12-timeline.md) (nine days, task by task, flash by flash)
- [13 — Open questions](docs/13-open-questions.md)
- [14 — Tooling](docs/14-tooling.md) (what's in `tools/`, how to run/reproduce)
- [15 — Memory training F9 notes](docs/15-memory-f9.md)
- [16 — Glossary](docs/16-glossary.md)

## Reproduce the final build yourself (no firmware in this repo)

```bash
# You provide ASUS's official image (8902 for C6H):
python3 tools/build/fvmain_bytepatch.py CROSSHAIR-VI-HERO-ASUS-8902.CAP out.CAP
# Expected: "FV diff: 37 bytes" and
# sha256(out.CAP) == f87ba18d677e6ae79c8a3a5118be87fcebba97f5958690718521f89efbd87a22
```

Reference hashes: official 8902 base
`04ddae2d0650353ec7bafa50a281528791a74694960f2104ac9d53657b0b6bba`; daily-line
build A28 `ec3277b38da8f6b692445bbe548693f0bda6199395a50fc9f5e27b4ce1da2168`;
Gen4 skip anchor (V2) `8b19a729…` (full sha in
[docs/11](docs/11-build-catalog.md)).

## Hardware under test

ASUS ROG Crosshair VI Hero (X370, AMD AM4), BIOS 8902, Ryzen 7 5800X3D
(Vermeer, 8 cores), 4×16 GB G.Skill dual-rank DDR4 (two mixed 2×16 kits).
Everything was done on this one machine.

## Rules we kept (and you should too)

- Flashing/BIOS work is **at your own risk**; nothing here is endorsed by AMD or ASUS.
- **No fuse, OTP or authorization state was ever touched** — they are irreversible.
- AMD-signed content (SMU, PSP BL/TOS/drivers) was left **byte-identical** in every
  "daily" build; experimental patches to signed content were only discussed, never
  shipped as a daily.
- Every experiment had a written prediction and a decision criterion *before*
  the flash; dead ends are documented here with the same care as successes.

## License

Code MIT, documentation CC BY 4.0 — see [LICENSE](LICENSE). Firmware binaries
belong to AMD/AMI/ASUS and are (and will be) absent from this repository.
