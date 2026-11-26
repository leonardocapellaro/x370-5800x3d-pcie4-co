# 19 — The last sweep: what the PSP really demands, the NBIF strap test, and the close (26 Nov, M35–M37)

## Summary

The final day went back to the PSP side with one question: *if* something could show the PSP a different
chipset ID, would that be enough? Reading the active driver again says **no**:

- **M35.** "Curve Optimizer yes, anti-Gen4 strap no" needs a whitelist row of a newer chipset (`43d1`, `43ed`
  or `43ee`) **and a challenge–response passed on function 2 of that same device**. An ID that is not in the
  table gives Gen4 without CO — exactly the RC1 build we already have. Redirecting the PSP to a different
  bus/device/function, by itself, therefore cannot produce the combo.
- That audit left one idea standing (**B10**, a time-of-check/time-of-use swap: let the PSP read a forged ID
  from an internal device, then put the real chipset back before the challenge). Its first gate was "can x86
  code change the device ID of an internal NBIF function through the ID strap register?".
- Two diagnostic builds answered the gate. **A44** (flash 47, guarded write) and **A45** (flash 48, unguarded
  write — the campaign's only blind write, explicitly ordered by the owner) both left the internal device at
  `1022:148a` ⇒ **M36, M37**. B10 is dead with a measurement; its second step was never designed in full or
  built.

The campaign is **closed**. Final state: Curve Optimizer + PBO with Gen3 (build A36), or Gen4 without CO
(build RC1). No founded path to both remains on this board.

## 1. What the active driver requires (M35)

Static reading of the active PSP driver (the one loaded for the 5800X3D, see [docs/09](09-psp-driver-re.md)),
audited against the V2-era hardware capture:

- The PSP reads the chipset's PCI config space **itself**, through ECAM
  (`0x10000000 | bus<<20 | dev<<15 | fn<<12`, memory-mapped); it does not ask the host or the chipset firmware
  for the ID `(src: RASTRO §KKK, §SSS)`.
- The bus/device/function it probes comes from the DXIO packet: the capture shows x86 code rewriting it
  `0x000b → 0x0200` between calls 26 and 27, and the SMU handing `0x0200` back at call 36
  `(src: RASTRO §RRR)`.
- The decision (`0xe0aa74` / `0xe0a9dc`): the "CO yes, clamp no" outcome requires a row `43d1/43ed/43ee`
  **plus** an approved challenge–response on function 2 of the same device (`e0b594`), **or** the "BXB" key
  path below, **or** a non-secured part (fuse state — outside every rule of this project). An ID outside the
  table yields `ctx[0]=0` ⇒ Gen4 without CO, which is what RC1 does by skipping the check
  `(src: RASTRO §RRR)`.

**M35 — redirecting or altering the BDF in the DXIO packet does not give CO + Gen4.** Closed by static
reading, not by a flash `(src: RASTRO §RRR)`.

This also reframes [docs/17](17-chipset-8051-firmware.md)/[18](18-chipset-8051-id-hunt.md): had the 8051
managed to show `43d1`, the outcome would still have depended on the challenge on function 2. The challenge is
the same for every ID and its key is embedded in the driver (and absent from the chipset firmware blobs)
`(src: RASTRO §SSS)`; whether an X370 Promontory answers it the way a newer chipset does was never measured.

### The "BXB" path

A second policy source that involves no chipset probe at all (`e07fcc`, table `0xe16c90`): the policy is
selected by `plat+0x4b4 = key | 0x42584200`. The key is written by the PSP bootloader (`0x4510`; default
`0xAA`) only after it finds device ID `0x148D` behind the bridge and completes an exchange with a 0x20-byte
nonce (`0xf14`). That is attested by hardware before any x86 instruction runs ⇒ dead on this board
`(src: RASTRO §RRR)`.

### Other deliveries of the same round

T104: a complete inverse of the clamp from x86 is not feasible — the clamp has three effects (the
`0xFFF0001C..23` stream, the `0xFFFE0084` / `GEN4_DIS` doorbell, and the OR of bit 21 at `0x914`) and A35 had
undone only the second (label: partial). T105–T108: where the probed BDF comes from, the SMU relay, and the
PEI builder of the packet (all labelled partial). An erratum from that round: a GUID search needle had the
wrong byte order `(src: RASTRO §QQQ, §RRR)`.

## 2. B10 — the time-of-check/time-of-use idea

**Hypothesis.** The PSP reads the device ID once (function 0), then waits for the function-2 challenge
**without a timeout** (`0xe0b60a..0xe0b61c`: loop until byte `+0xdd` has bit 1 = 0 and bit 0 = 1). If x86 code
made "bus 2" point at an internal device whose ID reads `43d1`, and swapped the bus numbers back so the real
Promontory answers the challenge, the PSP would take row `01 01 00 00`: CO yes, clamp no
`(src: RASTRO §SSS)`.

Supporting facts: the PSP's access is ECAM, so it is routed by whatever bus numbers are in force; the x86 side
regains control between PSP calls (in the capture, call `0x1e` takes 1.46 M ticks against 0.18–0.28 M for its
neighbours); and internal function-0 devices exist on this board at `0c:00.0` (`1022:148a`, behind `00:07.1`)
and `0d:00.0` (`1022:1485`, behind `00:08.1`) `(src: RASTRO §SSS)`.

**The gate.** Everything hinges on an internal device showing a forged ID. The lead was a table entry in the
BIOS: `{SMN 0x10134000, mask 0x0000FFFF, value 0x145A}` — a write to the DEVICE_ID field of the NBIF0
function-0 strap register. On inspection that entry exists **only in the Zen 1 module** (PEIM `5f0fbe1b1673`
at `0x3ab1`); no Vermeer-path module writes the ID field. So "x86 writes the device-ID strap" is a mechanism
that exists in this BIOS, not something that happens on this CPU — the first version of our note overstated
it `(src: RASTRO §SSS fact 4, corrected in §TTT)`.

Not measured, and decisive: whether that strap is still writable/effective on Vermeer at that boot phase, and
what the PSP's own writes to config `0xdc..0xef` would do to an internal device. One input the test did
measure for free: byte `0xDD` of the internal devices (it must have bits 0 and 1 clear, or the PSP burns its
100 attempts before the swap and returns "no CO" — harmless) `(src: RASTRO §SSS)`.

## 3. The two strap builds

Delivery reuses the A35 skeleton, which had already booted on the board: a few bytes in padding inside one
unsigned x86 TE module (`21be6180-…`), reached from an existing call in the DXIO loop so the code runs
before each PSP call of that loop (including the vetting call `0x1e`). The strap is accessed the way that
module itself does it, through the SMN index/data pair at config `0xB8/0xBC` of `00:00.0`. Base A36; signed
content byte-identical; diff confined to that one TE file and the checksums above it
`(src: RASTRO §TTT; construcoes/109-a44-strap-id-diag/README.md)`.

| build | SHA-256 | flash | write | reading (owner, from the OS) | verdict |
|---|---|---|---|---|---|
| A44/STRAP-ID | `4a6e4d9979a15440fc7c341b42f1c76bd088876d9bd52f560ca1e48c35222753` | 47 | **guarded**: read the strap; skip if it reads `FFFFFFFF` or already has `43d1`; otherwise set bits [15:0] to `43d1` | `0c:00.0` = `1022:148a`; byte `0xDD` = `00` on `0c:00.0` and `0d:00.0`; strap read from the OS = `ffffffff` | **M36** |
| A45/STRAP-BLIND | `ced7a7c22d03bebbee786008df431522e2bb4abebb48f727666077dc670212f9` | 48 | **unguarded**: if the strap reads `FFFFFFFF`, write `0x100043d1` (ID + function-enable bit); otherwise modify bits [15:0] only | `0c:00.0` = `1022:148a`; `0xDD` = `00` on both; control `SMN 0x03810054` = `001a43b9` (OS read path alive in the same command); strap = `ffffffff` | **M37** |

Both were verified offline before staging by an independent script (diff confinement, the patched sites being
padding after a `ret` inside the section, no relocation touching them, and an instruction-level walk of the
new code against a model of the index/data pair in four scenarios; 24/24 each), and rebuilt twice
byte-identically. No mutation tests were run for these two `(src: construcoes/109…, 110…/verify.py; RASTRO §TTT, §VVV)`.

### Flash 47 and an overclaim in our own reader

The pre-registered matrix for A44 had an `UNREADABLE` branch that the reader script printed as "the guard
aborted, nothing was written". The data did not support that sentence: the OS-side read happens much later,
through `setpci`, and in that first reader had **no positive control in the same command**; it says nothing
about what the patched code read in PEI. What flash 47 measured is only "the ID did not change". Three
explanations stayed unseparated: (a) the page is unreadable in PEI too, so the guard skipped the write;
(b) the write happened but the ID is fixed earlier; (c) the patched code did not run. The reader was corrected
and the error logged `(src: RASTRO §UUU)`.

### Flash 48 — the blind write

Removing explanation (a) needs a write that does not depend on the read — i.e. a blind write, with the upper
bits of the register guessed. That violates this project's echo rule (every write preceded and followed by a
read-back). The owner waived the rule in writing **for this one build only**; the waiver expired with it
`(src: RASTRO §VVV)`.

Result: ID still `148a`. This time the reader carried a control (`0x03810054` = `001a43b9`, the long-known
live NBIO witness), so the strap's `ffffffff` is now a measurement: that SMN page is not readable from x86 at
run time — the same class as M22 ([docs/10](10-negative-results.md)) `(src: RASTRO §WWW)`.

**M37 — writing the NBIF0 device-ID strap `0x10134000` from x86 at the DXIO-loop hook does not change the ID
of `0c:00.0`, guarded (M36) or unguarded.** Honest residue: with no PEI-time log, "the write was discarded"
and "the patched code did not run" are still not separated (the hook is A35's; all three flashes that used it
booted healthy). It does not matter for the decision: without a forgeable ID, step 2 of B10 has nothing to
stand on `(src: RASTRO §WWW)`.

## 4. Closure

| | PCIe | Curve Optimizer / PBO | build |
|---|---|---|---|
| daily option 1 | Gen3 | yes, in the menus | A36 `f87ba18d677e6ae79c8a3a5118be87fcebba97f5958690718521f89efbd87a22` |
| daily option 2 | Gen4 | refused by the SMU | RC1 `8b19a729…` (full sha in [docs/11](11-build-catalog.md)) |
| both | — | — | no founded path |

What would reopen it `(src: RASTRO §RRR, §WWW)`:

- a physical 400/500-series chipset (i.e. a different board);
- a device whose ID is x86-definable, demonstrated by some other route — and then B10's second step would
  still have to be designed, with the function-2 challenge and the PSP's config writes as open risks;
- a double offline proof that the function-2 challenge needs no secret **and** that an x86-controllable
  responder exists at config `0xdc..0xff`.

Not to be repeated: BDF patches in the DXIO packet (any destination); the ID-strap write at this hook; `01:005C`
and `01:8550` in the chipset firmware; a page-01 sweep for ID pairs.

## Open questions

- Did the patched code in A44/A45 run, and what did it read in PEI? Needs a PEI-time log channel that this
  module does not have.
- Is the NBIF ID strap writable at any earlier point on Vermeer (before the internal devices are enumerated)?
  No hook that early was ever shown to run on this board ([docs/04](04-boot-timeline.md), M24).
- Does an X370 Promontory pass the function-2 challenge the way a 400/500-series chip does? The primitive of
  the challenge was not identified.
- How does the SMU react to challenge results 1/2? Not traced.

## Sources

- `biosmod_8902_co/RASTRO.md` §QQQ (external review, task list), §RRR (T104–T108, audit, M35, BXB), §SSS (B10), §TTT (A44, correction), §UUU (flash 47, M36, reader erratum), §VVV (A45, echo waiver), §WWW (flash 48, M37, closure).
- `biosmod_8902_co/revisoes/117-*.md` — coordinator audit and the B10 addendum.
- `biosmod_8902_co/trabalhos/104…110-*.md` — task records.
- `biosmod_8902_co/construcoes/109-a44-strap-id-diag/` and `110-a45-strap-id-cego/` — builders, independent verifiers, readers, and the owner's flash-47/48 readouts.
- `biosmod_8902_co/STATUS.md`, `CLAUDE.md` — closing addenda of 26 Nov.
- Cross-links: [05](05-gen4-the-clamp.md), [09](09-psp-driver-re.md), [10](10-negative-results.md), [17](17-chipset-8051-firmware.md), [18](18-chipset-8051-id-hunt.md).
