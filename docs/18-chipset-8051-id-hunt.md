# 18 — Hunting the chipset device ID from inside the 8051 (25 Nov, A39–A43, M33)

## Summary

[docs/17](17-chipset-8051-firmware.md) ended with "the 8051 wrote `01:005C` and the ID did not change" and no
way to see inside the chip. This doc is the continuation: five more builds (A39–A43, flashes 42–46, all on
25 Nov) that patch **only** the unsigned Promontory firmware (`_PT_`) and use it as a probe. What they
established:

- **A working 8051 → OS side channel.** Bytes the firmware writes to `01:814C..814F` appear in the chipset
  xHCI's PCI config space at `0xF4..0xF7` and survive until the OS. With it, the reset hook, the init hook and
  the main-loop hook were all **proven to execute** after a PSU power cut.
- **M33 — `01:8550` is not the bus-visible ID.** The register that the public ASM2142 map calls
  `PCI_CONFIG_VID_DID` exists on the Promontory, but its device-ID half reads **`1242`** (the ASMedia core's own
  ID), not `43b9`.
- **A complete sweep of hardware page 01 (64 KiB) for the ID byte pair** found the already-known `b9 43` at
  `01:005E..5F` and a single `43 b9` at `01:58A2..58A3` — which the next boot showed to be a **changing
  register**, not a copy of the ID (it read `63 b9`, and never `43 b9` again in 174 polls).
- Replacing two ID literals inside the firmware image does not change the bus-visible ID either.
- A cross-board comparison found that the X470 and B550 chipset firmwares do **not** contain their own device
  IDs as data at all (partial result).

Net: no firmware-accessible source of the PCI-visible device ID was found. That is consistent with an ID fixed
below the firmware (strap / fuse / package option of the AMD wrapper around the ASMedia core), but "hard-wired"
is an inference by elimination, not a measurement. The chipset-firmware line is closed.

## 1. Correction to docs/17

docs/17 called the line closed and leaned on "the source looks like silicon". That was stronger than the data
at the time: A37 had tested exactly one register (`01:005C`) and its execution was never observed. An external
review pointed at an untested candidate (`01:8550`), so **M32 was re-scoped** to "writing `01:005C`" and the
line reopened until the builds below were read `(src: RASTRO §LLL)`.

## 2. Firmware facts gathered on the way (offline analysis)

| fact | value | source |
|---|---|---|
| register map kinship | the Promontory follows the public ASM2142 map in 5 checked points: `01:0050` SVID/SSID, `01:5087` bit 4, doorbells `01:8140/8141`, device-to-host block `01:8148` (8 bytes, copied at `0x1a0d0`), host-to-device block `01:8150` (8 bytes) | RASTRO §LLL (public map: `cyrozap/asmedia-xhc-re`, `regs-asm2142.yaml`) |
| where the ID sits | `01:005C..5D` = vendor ID, `01:005E..5F` = device ID (live reading `22 10 b9 43`) | RASTRO §LLL (correction), flash 46 reading |
| comparison pool | `0xb456..` = `b9 43 00 00 / ba 43 / bb 43 / bc 43`; the firmware only **compares** the ID it reads, never builds it | RASTRO §KKK, §LLL |
| entry points | `main` = `0x0d00` (re-sets `SP=0x7f`); main loop head `0x1634`, free-running (no idle) | RASTRO §MMM |
| vectors | `0x03 → LJMP 5632` (INT0), `0x13 → LJMP a86a` (INT1); both enabled, same priority | RASTRO §LLL, §OOO |
| interrupt stack depth | the two ISRs push 48 bytes (≈62 with calls) ⇒ internal RAM `A0..C4` is **not** free; the stack was measured reaching `C1` | RASTRO §OOO, flash 45 reading |
| XDATA `00:59xx` | rewritten by the running firmware (`00:5902` did not hold a value across reset → main loop) — it is the reserved area of the compiler's data stack, not free RAM | RASTRO §MMM, §NNN, §OOO |
| free code space | `0xb609..0xbfff` (zeros); `0xb287..0xb608` is an init data table; code placed at `0xb700` runs | RASTRO §NNN |
| page `01:58xx` | a hardware block (the firmware uses `01:5800` as a 44-byte block at `0x70c4`); it never addresses `58A2/A3` | RASTRO §PPP |
| host mailbox | the original firmware has a host→8051 message handler (`0x1a040..0x1a14c`); commands not read. Using it live would be a host write to config space — outside our rules, not proposed | RASTRO §LLL |

Two errata recorded with these: a raw-byte search for "no reference to `0x005C`" had used the wrong operand
order (`MOV DPTR,#imm16` is `90 hi lo`), and a census that paired `MOV DPTR` with the following access is
useless on this blob, whose idiom pushes DPTR, loads a pool, sets the page SFR and pops before calling a helper
`(src: RASTRO §KKK)`.

## 3. The side channel: 3–4 bytes from the 8051 to Linux

The device-to-host block at `01:8148` is 8 bytes wide and maps to the xHCI function's config space `0xF0..0xF7`.
The first four bytes carry the firmware's "I am loaded" signature (`aa 55 aa 55`, see docs/17 §4); the last
four, `01:814C..814F`, are unused by the original firmware (zero references) and nothing clears them before the
OS `(src: RASTRO §LLL)`.

- A39 proved `01:814C..814E → cfg 0xF4..0xF6`; A40 added `01:814F → cfg 0xF7` `(src: RASTRO §LLL-veredito, §NNN)`.
- For bulk data the later builds turn it into a **carousel**: the firmware's main-loop hook publishes
  (index, value, check byte) tuples forever; the OS reader samples config space as fast as it can
  (about 360 000 samples/s on this machine) and takes a majority vote per index
  `(src: RASTRO §MMM; construcoes/101-a42-acima-da-pilha/capturas/flash45/leitura.txt)`.
- The chip must be power-cycled at the PSU between builds: the BIOS skips the firmware upload while the old
  signature is present (docs/17 §4), and stale channel bytes from the previous build survive a warm reboot
  `(src: RASTRO §NNN)`.

A design constraint specific to this machine: the OS boots from the **chipset's** SATA controller, and
keyboard, mouse and flash drive hang off the chipset xHCI. Any probe that reads chipset hardware registers had
to finish before the OS, and a hung chipset would have meant FlashBack + power cut `(src: RASTRO §MMM)`.

## 4. Builds and flashes

All five are official 8902 + the A36 menu patch (`f87ba18d…`) with changes **only inside `_PT_`** (plus its
sum32). Each reading was taken after a PSU power cut.

| build | SHA-256 | flash | what it does | result |
|---|---|---|---|---|
| A39/VIDDID-8550 | `f59385ccef86295c7422e5924c4adb66397b2bf97434e730a07cd591d4431392` | 42 | 99 bytes. Guarded write `43b9→43d1` at `01:8552` (only if `01:8550` reads `22 10 b9 43`), from the reset and init hooks; echo + status published at `cfg F4..F6` | `43b9`, roots max 8.0; `F4..F7 = 11 12 42 00` ⇒ both hooks ran, guard failed twice, **nothing written**; `01:8552..53` = `1242` ⇒ **M33** |
| A40/CAROUSEL | `dc589ed5eb43d8ff5e5769ae495e82ddeeae343cad3b8a3a268aeec61498d9c8` | 43 | 600 bytes. Read-only sweep of page 01 for the ID byte pair, state kept in XDATA `00:59xx`, result replayed over the channel | `F0..F7 = aa 55 aa 55 00 ee ee ee`, constant over 1 574 000 samples: the routine ran, its state was gone, the sweep never started. No verdict |
| A41/MEMINT | `863b318668f7723f24605aa67399c055b00d2493b2b463453d6eb8f59c8b910b` | 44 | 547 bytes. Same sweep with state in internal RAM `A0..FF` | first page read correctly (hits at `01:0041/0043/0053/005F/008F`), then the state was destroyed three times — by the interrupt stack. No verdict |
| A42/ABOVE-STACK | `0e205813f253b7846efe02e677d661a5421ee42bf67de5721caecbdb5db01815` | 45 | stack-free routine, state in `D8..FD`, sentinels in `C0..D7`, 64 addresses per loop pass | **sweep complete** (7/7 controls, 1 452 000 samples): `b9 43` at `01:005E..5F` (known) and `43 b9` at `01:58A2..58A3` (new) |
| A43/WRITE-58A3 (full) | `943b3638d1e2fee796d6536873c923f0b04f45b439b9a07bc33ec3585583083f` | 46 | guarded, echoed, once-per-power-cycle write of `d1` to `01:58A3` and `01:005E`; also swaps two firmware literals (`0xb291`, `0xb45c`) | guard never satisfied: `01:58A2..A3` never read `43 b9` in 174 polls (last `01:58A0..A3` = `a7 02 63 b9`); **no hardware write happened**; bus ID still `43b9` |
| A43 minimal | `d30e026d17ba1dcd3f0054b61908a34c54f89ec5010661c91d7bbebbfcbf605d` | — | the two cell writes only, firmware literals untouched | staged as an optional control, not flashed |

`(src: RASTRO §LLL–§PPP; SHA-256 recomputed from construcoes/98…102 outputs; flash readings under each
build's capturas/)`

## 5. M33 — `01:8550` exists and is not what the bus shows (A39, flash 42)

Reading at 18:24: xHCI `1022:43b9` (subsystem `1b21:1142`), roots max 8.0 GT/s, signature present, and
`cfg F4..F7 = 11 12 42 00`. Decoded: `F4 = 11` — the reset-hook and init-hook nibbles both say "guard failed",
so **zero writes** to `01:8552`; `F5 F6 = 12 42` — the device-ID half of `01:8550` reads **`1242`**, the ID of
the ASMedia ASM1142 core (`1b21:1242`) `(src: RASTRO §LLL-veredito)`.

**M33:** the ASMedia-map `PCI_CONFIG_VID_DID` register is real on the Promontory and still holds the ASMedia
core's ID; the `43b9` on the bus comes from somewhere else. Limits: read at reset/init, not at the instant the
PSP reads the ID; the vendor-ID half was not published; no write to `01:8552` was attempted (the guard
refused) — none of which changes the decision, since the register already differs from the bus
`(src: RASTRO §LLL-veredito)`.

The same flash retroactively strengthens M32: A37 used the same two hooks and code area, and those are now
proven to execute, so A37's write to `01:005C` very probably did run `(src: RASTRO §LLL-veredito)`. It was
never echoed, though (see §8).

## 6. Three flashes to learn where an 8051 probe may keep its state (A40–A42)

The sweep needed memory that survives from "found something" to "the OS reads it". Each wrong guess cost one
flash and one power cut:

1. **A40 (flash 43): XDATA `00:59xx`.** Chosen because no firmware literal points there. The loop hook read
   `00` where the reset hook had stored its phase and mark. "Nobody references it" is not "it holds data": the
   area belongs to the compiler's data stack and `00:5902` is rewritten at run time
   `(src: RASTRO §NNN, §OOO)`.
2. **A41 (flash 44): internal RAM `A0..FF`.** Chosen from a static census of stack-pointer writes that
   concluded "shallow stack". Wrong for `A0..C4`: the two interrupt handlers push 48 bytes. The sweep read its
   first page correctly and was then killed three times `(src: RASTRO §OOO)`.
3. **A42 (flash 45): above the measured stack, no stack use at all** (no `PUSH`/`LCALL` in the hook, since
   interrupts are live), sentinel bytes below the state to measure how far the stack really climbs. It climbed
   to `C1`; the sweep completed in one pass `(src: RASTRO §OOO, §PPP; capturas/flash45/LEITURA.md)`.

Process notes the log records for itself: every probe that depends on a memory area must carry an **echo of
that memory** in its own result; and the verification suite for these builds (an 8051 instruction-level
simulation plus mutants) only counts a mutant as caught after a control run shows the unmutated code passes
the same reduced suite — the first A40 round had three mutants "caught" by a broken test
`(src: RASTRO §MMM, §NNN)`.

## 7. The "second copy" that was not one (A42 → A43, flashes 45–46)

Flash 45 found the pair at two places: `b9 43` at `01:005E..5F` (the known register, little-endian) and `43 b9`
at `01:58A2..58A3`. We read that as "a second copy of the ID" and built A43 to overwrite both, guarded on the
cells still reading the ID.

Flash 46: the guard polled `01:58A2..A3` 174 times and never saw `43 b9`; the last reading of `01:58A0..A3`
was `a7 02 63 b9`. So `01:58A2` is not constant (`43` on one boot, `63` on the next) and a copy of the ID
would read the same every time. Because the write to `01:005E` was chained behind that guard, **no hardware
write happened at all**. Useful by-product: the full variant had two ID literals of the firmware image
(`0xb291`, `0xb45c`) replaced, and the bus still showed `1022:43b9` ⇒ those literals are not the source
`(src: construcoes/102-a43-escrita-58a3/capturas/flash46/LEITURA.md; RASTRO §PPP)`.

Erratum recorded: one 2-byte hit in a 64 KiB sweep was treated as a "copy" without re-reading the address;
A42 should have re-read its own finding `(src: capturas/flash46/LEITURA.md)`.

## 8. Cross-board comparison of the chipset firmware (T103, partial)

With the owner's own copies of two other official ASUS images (Crosshair VII Hero X470 6102, Strix B550-F
3646), the `_PT_` blobs were extracted and compared with ours (8902 and 7306). All four are 114 700 bytes with
the same container (magic, length, sum32). Findings `(src: construcoes/103-promontory-x-v2/RESULTADO.md,
EVIDENCIAS.md; RASTRO §QQQ)`:

- Only the **X370** firmware has a pool of device IDs (`43b9/ba/bb/bc`).
- The X470 firmware does not contain `43d5` as data; the B550 firmware does not contain `43ee` anywhere in the
  file, in either byte order. (Their external IDs are nominal — no PCI capture of those boards.)
- No device-ID writer was demonstrated in any of them, but the census left 317 stores with unresolved
  address/value, and the task was closed as **partial**.

If a chipset's own firmware does not even contain its ID, the firmware is unlikely to be what puts that ID on
the bus — which points the same way as M32/M33, without proving it.

## 9. Verdict

No firmware-accessible source of the PCI-visible device ID was found on this chip:

- `01:005C` written at reset/init (A37) — ID unchanged (M32; execution of the hooks proven later, write never echoed);
- `01:8550` — holds `1242`, not the bus ID (M33);
- the rest of page 01 — one full sweep, no second stable copy;
- two ID literals in the firmware image (`0xb291`, `0xb45c`) — replaced, ID unchanged;
- sibling chipsets' firmwares — do not carry their IDs as data.

What this does **not** establish: that the ID is a fuse, a strap or a package option (never observed); whether
`01:005E` is writable by the 8051 (the one echoed write that would have answered it never ran, §7); what lies
in hardware pages other than 01 (not swept: there is no static proof that the firmware can address them); and
what the PSP sees at the instant it reads the ID.

It also turned out not to be the last word for a different reason: the PSP-side audit in
[docs/19](19-final-sweep-and-closure.md) shows that a changed ID alone would not have been enough.

## Open questions

- Where is the bus-visible device ID latched (fuse, strap, package option, a register outside page 01)? Only
  Promontory documentation or silicon-level work answers it.
- Is `01:005E..5F` writable from the 8051? The A43 minimal build (staged, never flashed) would echo that.
- What is the changing register at `01:58A0..A3`?
- What do the host→8051 mailbox commands at `0x1a040..0x1a14c` do?

## Sources

- `biosmod_8902_co/RASTRO.md` §KKK (ID-origin note, errata), §LLL + verdict (A39, M33, channel), §MMM (A40 design, firmware facts), §NNN (flash 43, A41), §OOO (flash 44, A42), §PPP (flashes 45/46, A43), §QQQ (external review, T103).
- `biosmod_8902_co/trabalhos/98…102-*.md` — task records for A39–A43.
- `biosmod_8902_co/construcoes/98-a39-viddid-8550/`, `99-a40-carrossel/`, `100-a41-memoria-interna/`, `101-a42-acima-da-pilha/`, `102-a43-escrita-58a3/` — designs, verification, and `capturas/flash4{2..6}/` readings.
- `biosmod_8902_co/construcoes/103-promontory-x-v2/RESULTADO.md`, `EVIDENCIAS.md` — cross-board `_PT_` comparison (partial).
- Public knowledge: `cyrozap/asmedia-xhc-re` register maps for ASM1142/ASM2142.
- Cross-links: [17](17-chipset-8051-firmware.md), [19](19-final-sweep-and-closure.md), [10](10-negative-results.md), [11](11-build-catalog.md).
