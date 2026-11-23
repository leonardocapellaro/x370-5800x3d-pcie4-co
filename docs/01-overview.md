# 01 — Overview: the machine, the two results, and why the combo is excluded

## Summary

Start from the stock state, because it is the baseline this whole study exists to change:
an X370 board with a Ryzen 5000 CPU such as the 5800X3D ships with **neither** PCIe Gen4 nor
Curve Optimizer — no official BIOS of this board (and none of any X370/X470 board, from any
manufacturer) ever offered Gen4 with Ryzen 5000 `(src: docs/05 §1)`, and CO is not present
in the menus on X3D parts `(src: docs/07 §1)`. On an ASUS ROG Crosshair VI Hero (X370) running official BIOS 8902 with a Ryzen 7 5800X3D,
this campaign obtained **PCIe Gen4 on both CPU roots — but only in a build where Curve
Optimizer is refused**, and **Curve Optimizer + PBO fully working in the native menus — but
only on Gen3**. The combination in one BIOS is **excluded by construction**: the same
AMD-signed PSP transaction that validates the chipset (the event that opens the CO gate) is
also the transaction that writes the anti-Gen4 strap, and the code that finally applies the
clamp lives in on-chip NBIO microcode, outside anything editable or readable offline. Both
halves are measured, reproducible and documented here; so is every way that failed to
connect them.

## The machine and the question

- **Hardware:** ASUS ROG Crosshair VI Hero (X370, AMD AM4), official BIOS 8902
  (SHA-256 `04ddae2d0650353ec7bafa50a281528791a74694960f2104ac9d53657b0b6bba`), Ryzen 7
  5800X3D (Vermeer, 8 cores), 4×16 GB G.Skill dual-rank DDR4 (two mixed kits). Everything
  was done on this one machine `(src: biosmod_8902_co/HANDOFF-FINAL-20261122.md header; HANDOFF-FINAL §1)`.
- **Question:** is there a demonstrable native control that delivers **GPU Gen4 ×16 + M.2
  Gen4 ×4 + Curve Optimizer −22 on all cores in the same boot**? `(src: biosmod_8902_co/RELATORIO-FINAL-8902.md)`
- **Answer (22/11/2026):** no such control exists on this platform/BIOS. The two halves
  live on different bases; the combo is a measured, reasoned negative
  `(src: biosmod_8902_co/RELATORIO-FINAL-8902.md "Decisão"; HANDOFF-FINAL-20261122.md §3)`.

## The two working halves

| | PCIe Gen4 | Curve Optimizer / PBO | How |
|---|---|---|---|
| **Stock 8902** (the "neither" baseline) | Gen3 — the signed chipset check writes the anti-Gen4 strap every boot | absent from the menus on X3D (capability gate zeroed) | nothing — the state every owner of this CPU/board combo starts from `(src: docs/05 §1–§2; docs/07 §1)`. |
| **GEN4-REL1 / "RC1"** (`8b19a72945703ffaf61a1f6886d82bc2c70100c0f3004666933ea7ecfcb4074f`) | **works** — GPU x16 + M.2 x4 at 16.0 GT/s, measured on board | refused by the SMU (`0x000000FF`) | DXIO `SKIP_PSP`=1 in mailbox request 9 so the PSP chipset-vetting exchange never runs, plus NOP of the one "BIOS boot done" call (PSP mailbox command 6) `(src: docs/06 §1; biosmod_8902_co/frentes/A-gen4-com-skip/)` |
| **"A36"** (`f87ba18d677e6ae79c8a3a5118be87fcebba97f5958690718521f89efbd87a22`) | Gen3 (stock clamp intact) | **works natively in the menus** — CO settable, PBO exposed (build-side by IFR proof; the A36 board confirmation — flash 39 — was pending at log close) | official 8902 + exactly **37 bytes** of x86 patches in unsigned DXE modules: 6 capability-flag stores NOPed across the three AOD driver copies + boost base := `4550 MHz` with a ±200 menu range `(src: docs/07 §7; docs/11 §6; tools/build/fvmain_bytepatch.py)` |

The A36 image is reproducible byte-for-byte from the official BIOS with this repo's tool
(see README "Reproduce the final build yourself"). The accepted daily state at campaign
close was the A28/A23 family (CO −22 + PBO exposed, Gen3) with A31 as a proven recovery
image; the board was left on A35 (= A28 behavior plus a no-effect strap rewrite,
flash 38), healthy `(src: biosmod_8902_co/HANDOFF-FINAL-20261122.md §1, §3; docs/12 flash log rows 35–38)`.

## Why Gen4 + CO in one BIOS is excluded by construction

The argument, in the four links the campaign could verify (full detail in
[docs/05](05-gen4-the-clamp.md); every step is a measurement, not an inference):

1. **One signed transaction does both jobs.** The Gen4 removal fires during SMU mailbox
   **request 30**: the same signed PSP/SMU exchange that validates the chipset — the only
   event that opens the gate Curve Optimizer needs — also writes the anti-Gen4 strap
   (index `0x84`, `GEN4_DIS`). Skipping the transaction (REL1) gets Gen4 *and* loses the CO
   gate automatically; the two are two faces of one check `(src: docs/05 §2; docs/06 §2)`.
2. **x86 cannot touch the gate or the strap.** Every route from firmware running on the CPU
   to the relevant SMN registers was probed or censused — box-12 message QCB, SMU data RAM,
   the `0x0101/0x0301` pages, the `0x0904` PSP-peripheral page: all unreachable (flashes
   10/15/16, M22/M23), and no x86 module anywhere in the flash even contains the mailbox
   submit registers (M16) `(src: docs/05 §6; docs/08 §7; docs/10 part (a))`.
3. **The clamp writer is not in the editable flash.** Whole-image censuses (every expanded
   payload of both bases) found zero code writing the policy proxy `0x03810054` (M17–M21);
   then the two flash-visible appliers of the strap family were **neutralized on the board,
   each in a controlled flash — A31 (e07 restore) and A32 (TE gate) — and the clamp
   persisted both times** (flashes 35/36, roots 8.0/8.0). Editing any *loaded* signed blob
   is separately dead with measurement: A34's two edited bytes in the active PSP driver
   meant **non-POST** — the PSP verifies every blob it loads (flash 37)
   `(src: biosmod_8902_co/HANDOFF-FINAL-20261122.md §2; docs/05 §5)`.
4. **What is left is unreadable.** By elimination the applier is NBIO on-chip microcode or
   hardware — the one component no offline path can read (the only encrypted blob in the
   image, HIC, is inert and identical across bases) `(src: docs/05 §7; docs/09 §8)`.

Every attempt to decouple validation from the strap is catalogued with the measurement that
killed it: the 15 closed routes listed in
[docs/10](10-negative-results.md) part (b), and the complete registry is the
M1–M30 list there.

## Scale and safety record

Nine days (14–22 November 2026: V2 predecessor 14–17 Nov, then this campaign 18–22 Nov),
task chain T01→T58 plus the A16…A36 build sprint, ~70 offline-built and offline-validated
CAPs, board flashes numbered 1–39 (39 was never executed; a few runs were unnumbered). **Every flash, reboot and menu action
was performed by the human owner**; agents built, verified and read logs only. **Zero
fuse/OTP touches, zero signed-content changes shipped, zero bricks** — the images that
refused to boot (flash 7 SWAP7306, F9 storm; flash 18 OBSPEI-A2, hung at POST 61; the
A19 run, stuck at POST 36; flash 37 A34, non-POST) were each recovered by
the owner via clear-CMOS and/or USB FlashBack `(src: docs/12 flash log;
RASTRO.md §B M27 and §O (recovery "clear-CMOS + Flashback, proven twice"); biosmod_8902_co/HANDOFF-FINAL §7)`.
The workflow behind that record is [docs/02](02-methodology.md).

## How to use this repo (three reading paths)

- **Overclocker:** [docs/07](07-co-pbo-menus.md) (hidden menus, capability flags, boost
  formula, `.CMO` profiles, the 37-byte unlock) and [docs/15](15-memory-f9.md) (memory
  "F9" findings), then the README's one-command reproduction of A36; what each build did is
  [docs/11](11-build-catalog.md).
- **Firmware engineer:** [docs/03](03-firmware-anatomy.md) (FV/FFS/LZMA/VZL1/PSP-directory
  layout and offsets), [docs/04](04-boot-timeline.md) (measured boot trace),
  [docs/09](09-psp-driver-re.md) (PSP-side RE), [docs/05](05-gen4-the-clamp.md) and
  [docs/06](06-gen4-skip-and-era.md) (the clamp and the skip),
  [docs/08](08-smn-probes.md) (SMN reachability map).
- **Methodology-curious:** [docs/02](02-methodology.md), [docs/10](10-negative-results.md)
  (what was proven dead, with the closing measurements), [docs/12](12-timeline.md),
  [docs/13](13-open-questions.md).

**No firmware is in this repo** — analysis, tools and hashes only; you supply your own
official images.

## Sources

- `biosmod_8902_co/RELATORIO-FINAL-8902.md` — phase-1 decision table (two halves, anchors).
- `biosmod_8902_co/HANDOFF-FINAL-20261122.md` — endgame map: board state, flashes 35/36, accepted daily BIOS, house rules.
- `biosmod_8902_co/RASTRO.md` — master log: task index, M1–M30 dead ends, front status §FFF.
- `biosmod_8902_co/frentes/README.md` — the two-front master map.
- `biosmod_8902_co/STATUS.md` — contemporaneous diary.
- [docs/05](05-gen4-the-clamp.md), [docs/06](06-gen4-skip-and-era.md), [docs/07](07-co-pbo-menus.md),
  [docs/10](10-negative-results.md), [docs/11](11-build-catalog.md), [docs/12](12-timeline.md) — the
  delivered detail docs summarized above.
