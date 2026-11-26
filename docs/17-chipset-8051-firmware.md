# 17 — The chipset's own firmware: can the 8051 lie to the PSP? (25 Nov, M32)

## Summary

A reader's idea reopened a door we had closed: the Promontory chipset runs an **8051 firmware that lives in
our own BIOS flash and is not signed**. The PSP decides the Gen4 clamp from the chipset's xHCI device ID
(`43b9` on X370); a whitelist row for another ID (`43d1`) carries the same policy **without** the anti-Gen4
strap. So "make the chipset announce a different ID" is, on paper, the right lever and it needs no edit of any
signed AMD content. We built it (A37), flashed it (flash 40) and measured it: after a full PSU power cut the
xHCI still reads `1022:43b9`, the root ports still advertise **8.0 GT/s max**, and the chipset works
normally. Verdict **M32**: the 8051 cannot change the device ID the host sees by writing register `01:005C`
(at reset and at init). The test does **not** separate "that register is read-only to the 8051" from "that
register is not where the PCI-visible ID comes from" — the firmware never writes it and has no lock bit on it,
which points at the silicon as the source. A follow-up diagnostic image (A38) could not be read back from the
OS, so the line is closed. The doc also records a trap that invalidated our first reading: **the BIOS skips
the chipset-firmware upload when the chip already holds a firmware**, so a freshly flashed BIOS can test
nothing unless the PSU is cut first.

> **Update (25–26 Nov).** "The line is closed" was premature. M32 was re-scoped to "writing `01:005C`"
> and the work continued the same evening with a config-space side channel that *can* be read from the OS:
> see [docs/18](18-chipset-8051-id-hunt.md) (A39–A43, M33). [docs/19](19-final-sweep-and-closure.md) then
> shows why a changed ID alone would not have been enough, and closes the campaign.

## 1. Why this idea was on the table

- The PSP vetting transaction reads the chipset xHCI device ID and looks it up in a signed 24-row whitelist;
  for the X370 row one flag applies the `GEN4_DIS` strap (driver 0.14.0.43 table at CAP `0x480a70`; see
  [docs/09](09-psp-driver-re.md) and [docs/05](05-gen4-the-clamp.md)) `(src: RASTRO §HHH; trabalhos/95-a37-ptdid-43d1.md)`.
- Row `43d1` is `01 01 00 00` (same policy as X370, no strap); `43ee` (B550) also lacks the strap. `43d1` has no
  public `pci.ids` name. It is **not** X470/B450 — those are `43d5`, and their row *does* apply the cut
  `(src: construcoes/95-a37-ptdid-43d1/README.md)`.
- Editing the whitelist itself is closed: A34 (an edited signed driver) was a no-POST, the PSP verifies the
  signature of what it loads ([docs/10](10-negative-results.md), [docs/11](11-build-catalog.md) §6).
- The forum idea (public, owner-relayed): the Promontory has an 8051 that runs code and R/Ws SRAM, part of its
  init locks read-only the areas that identify the device, and one could rewrite the ID **before** the lock so
  the chipset "lies to the PSP/SMU". The claim that the 8051 is patchable turned out true; the rest did not
  hold on this board `(src: RASTRO §HHH)`.

## 2. The chipset firmware, as found in the flash

| fact | value | source |
|---|---|---|
| blob | magic `_PT_` at CAP `0x9c0800` (flash `0x9c0000`), `0x1c00c` bytes, in padding outside any FFS file; identical in 8902 and A36 | RASTRO §HHH |
| integrity | **only** a 32-bit byte sum over `[0xC..size)`, stored at blob `+8` (CAP `0x9c0808`; value `0x00a2e650` in the base), checked by the x86 PEIM `53070378-119A-4836-77BD-893C824ACEB2` before upload; no signature | RASTRO §HHH |
| CPU model | 8051 code address = blob offset − `0xC`; common area `0x0000–0xBFFF`, banked `0xC000–0xFFFF` (bank SFR `0x96`); 210 `LCALL 0156` bank trampolines; `DPX` = SFR `0x93` (`00` = XDATA RAM, `01` = hardware MMIO) | RASTRO §HHH, §JJJ |
| reset path | `0x0000 → 0x125 → 0x134` (`LJMP 0094`); init hook site `0x0fda` (`MOV DPTR,#005c`) | RASTRO §HHH |
| free code space | `0x0016–0x007F`, `0xb609–0xc000` (zeros) | RASTRO §HHH, §JJJ |
| device ID | upper word of `01:005C`; **32 reads, zero writes** anywhere in the firmware; compared only against `43B9/BA/BB/BC` (`43BA`, X399, takes the same branch as `43B9` in all 5 dispatches); `01:0050` = SVID\|SSID | RASTRO §HHH |
| "lock" | none found. `01:0060` bit 7 — the suspected unlock — is **port-activity gating** (entry `0x6bf4` increments `00:5071` and clears the bit; exit `0x62f5` decrements and sets it at zero), not a write lock | RASTRO §III |
| other ID data | the `22 10 b9 43` bytes at `0xb28f` are the xHCI **USB Debug Capability** device descriptor (`idVendor 1022`, `idProduct 43b9`), not the PCI ID; no other `43b9/43b5/43b0`/SSID occurrence | RASTRO §III |
| SSID | the BIOS programs the chipset SSIDs from a table in PEI module `27B1960A-…` ⇒ SSID is unusable as an observable marker | RASTRO §HHH |

The upload itself is a raw load: the x86 PEIM writes XDATA through a window at `BAR0+0x3000` of the chipset
xHCI (`+0`/`+1` address lo/hi, `+4` write data, `+8` read data, bit 7 of `+9` = busy), with `00:5040:=2`,
`00:5042:=1`, `00:500e:=1`, `cfg 0xEF:=0x80`, destination in `cfg 0xE2`, data at `BAR0+0x3010`, end
`00:5040:=3` with re-read. **The chip performs no validation of its own** — only the x86 sum check protects
it, which is why a patched, re-summed `_PT_` is accepted `(src: RASTRO §III)`.

Erratum recorded with it: the `cfg 0xE0/0xE4` index `0xA4` pair that the same PEIM uses belongs to the **CPU
root port** (link-speed control), not to the 8051 — an earlier note pointing at it as a host-side lever was
wrong `(src: RASTRO §III)`.

## 3. The experiment: A37 / PTDID-43D1

Base A36 (`f87ba18d…`, chipset check ON, no skip). 84 bytes changed, **all inside `_PT_`**; PSP, SMU, PEI, DXE,
NVRAM and capsule header byte-identical to A36. SHA-256
`09350a09b415474edad3cffa4a14594ad1e3c647f485be24f3db5bb8b0d61e87` `(src: construcoes/95-a37-ptdid-43d1/README.md)`.

| change | where (8051 / CAP) | what |
|---|---|---|
| guarded routine | `0x0020..0x0072` / `0x9c082c` | read `01:005C`; **only if it reads exactly `43B9`**, rewrite the four bytes with `43D1` (same write pattern the firmware uses on other registers); restore state and return |
| hook 1 | `0x0134` / `0x9c0940` | reset path calls the routine first (earliest possible moment) |
| hook 2 | `0x0fda` / `0x9c17e6` | same routine again just before the firmware's own first ID read |
| SKU constant | `0xb45a` / `0x9cbc66` | `43BA → 43D1` so the firmware treats `43D1` like X370 (`43B9` stays accepted if the write does not land) |
| checksum | `+8` / `0x9c0808` | `0x00a2e650 → 0x00a3162d` |

Prediction matrix, pre-registered: `43d1` + 16.0 GT/s + CO = success; `43d1` + 8.0 = ordering/other author;
`43d1` + CO `0xFF` = challenge failed; `43b9` = write did not take (does not separate read-only from undone);
chipset dead/no POST = FlashBack to A36 `(src: RASTRO §HHH)`. Validation was by build-time asserts, rebuild +
`cmp`, and re-disassembly only; no independent `verify.py` was run for this build (waived by the owner)
`(src: RASTRO §HHH)`.

## 4. Flash 40, the trap, and the real reading

**First boot (owner flashed A37, setting "Auto" for PCIe generation; read 25/11 13:47):** xHCI `1022:43b9`
(sub `1b21:1142`), SATA `43b5`, bridge `43b0`, roots `00:01.1` and `00:03.1` max **8.0 GT/s**, NVMe trained 8.0
(max 16.0), chipset USB/SATA normal — identical to the A36 reading before it `(src: construcoes/95-a37-ptdid-43d1/capturas/20261125-flash40/LEITURA.md)`.

By the matrix that would read "the write did not take" — but it relied on a premise of ours that fell apart
right after the reading: *"if the chipset works, the edited firmware ran."* Reading the upload PEIM again:

- **Upload skip.** At PEIM `0x1610`, if `cfg[0xF0]` of the chipset xHCI equals `0x55AA55AA`, the PEIM marks
  `[ctx+0x25]=1` and **skips the whole upload**.
- The signature is written by the **running firmware itself**: at init (`0x1634`) if bit 4 of `01:5087` is 0 it
  writes pool `0xb50a` (`aa55aa55`) to `01:8148`; two other paths (`0x5473`, `0x55a1`) set that bit and write 0
  to `01:8148` — an unidentified "request reload" event.
- So if the chip stayed powered from the PSU standby rail between flash and boot, the new BIOS saw the marker,
  skipped the upload, and the chipset kept running the **old** firmware from its own RAM. The first reading
  tested nothing. Our A37 had no host-visible fingerprint to tell the two cases apart (our design flaw: the
  SSID marker was unavailable, see §2, and we added no other) `(src: capturas/20261125-flash40/LEITURA.md; RASTRO §III)`.

**Discriminating step (owner-only, no flash):** power the PC off, cut the PSU (switch/plug), hold the power
button ~10 s to drain, wait ~1 min, power on. With no power the chip loses RAM and the signature, so the PEIM
**must** upload A37's `_PT_` and the reset/init hooks must run `(src: capturas/20261125-flash40/LEITURA.md)`.

**Second boot after the cut (owner-reported cut; read 25/11 14:08):** `1022:43b9` again, roots max **8.0**, chipset
normal `(src: capturas/20261125-boot2-pos-corte/LEITURA.md)`. The PSU cut itself is the owner's report — the
agent cannot measure it.

## 5. Verdict — M32

**M32 — the chipset 8051 cannot change the device ID seen by the host by writing `01:005C` at reset and at init
(A37, flash 40 + post-cut boot).** What it does and does not say:

- It says: the patched firmware was accepted (the chip took a modified `_PT_` with only the sum fixed and
  ran normally), and the host-visible ID, the roots' maximum speed and everything else stayed exactly as on A36.
- It does **not** separate "the 8051 cannot write that register" from "that register is not the source of the
  PCI-visible ID". Offline evidence leans to the second: the firmware has no write to it and no lock bit on it
  (§2), so the source looks like silicon/strap. It also assumes the stub ran — shown only indirectly (the chip
  accepted the image and was healthy; the code itself was checked by disassembly, never emulated)
  `(src: RASTRO §III)`.
- The "Auto" PCIe-generation setting is irrelevant to this result: with the ID unchanged the PSP applies the
  X370 row and the roots' ceiling stays 8.0 GT/s ([docs/05](05-gen4-the-clamp.md), RASTRO §S–§W). The official
  8902 menu offers GEN 1/2/3 only; forcing Gen4 in a menu with the capability capped is an experiment closed
  long ago.

**Lesson for any edit of RAM-loaded firmware:** give the build a host-visible fingerprint and verify the reload
condition *before* the flash; include a PSU cut in the procedure.

## 6. The follow-up that could not be read (A38 / T96)

To look for a *different* writable source of the ID, A38 was built from A36 (133 bytes, all in `_PT_`; sha
`bad4773ecc128866e01078d7e38a31a4fca8646232ca6fa53ca7e0d700693ba2`): a **read-only** sweep from the 8051 of
hardware pages `01:0000/0100/5000/8000/8100` (256 bytes each, DPX=1 reads) copied into free chip RAM
`0x5900..0x5DFF` with a header `S38!` + status at `0x5E00`; hardware was only read, RAM was the only write
target. The host-side reader (`read38.py`) used the BIOS's XDATA window. Result:

- v1 died at `mmap` (`EINVAL`): Fedora has `CONFIG_IO_STRICT_DEVMEM=y` and `xhci_hcd` owns the BAR; v2 needed
  `iomem=relaxed` and read via `+0x3008` (the read-data port; `+0x3004` is the *write* data port).
- v2 with `iomem=relaxed`: `ERROR: window busy (timeout)` — bit 7 of `BAR0+0x3009` stays set while `xhci_hcd`
  runs, i.e. **the XDATA window is a PEI-time interface and is unusable from the OS**. At most one byte was
  written (the low address register), chipset USB stayed normal. Whether the A38 firmware was even the running
  image at that moment is not recorded (the pendrive root held A36)
  `(src: construcoes/96-a38-varredura-id/capturas/20261125-boot-iomem/LEITURA.md; RASTRO §JJJ)`.

A redesign would have to publish the dump through PCI config space (map page 01 ↔ config and write a hardware
register) — not proposed: low prior, risk to the chipset. **Do not retry the `+0x3000` window with the xHCI
running.**

## Open questions

- Is `01:005C` writable by the 8051 at all, and which block latches the PCI-visible device ID? Only a
  config-space-visible diagnostic (or Promontory documentation) answers it.
- What event makes the running firmware set bit 4 of `01:5087` and clear `01:8148` (the "request reload" paths
  `0x5473`/`0x55a1`)? Not identified by reading.
- Is `01:8148` really the xHCI `cfg 0xF0` the PEIM compares? One constant × one comparison — strong, but an
  inference.
- What does the BIOS's SSID table writer look like (`27B1960A` block of `0x296` bytes copied at `0x432`)?
- Do the `7A54B36F-…`/`52A9B223-…` modules hold any other ID path on the x86 side? (left unchecked)

## Sources

- `biosmod_8902_co/RASTRO.md` §HHH, §III, §JJJ — firmware facts, upload-skip, flash 40 verdict and M32, A38/T96 closure.
- `biosmod_8902_co/trabalhos/95-a37-ptdid-43d1.md`, `trabalhos/96-a38-varredura-id.md` — task records.
- `biosmod_8902_co/construcoes/95-a37-ptdid-43d1/README.md` — A37 design, hook table, matrix, SHA.
- `biosmod_8902_co/construcoes/95-a37-ptdid-43d1/capturas/20261125-flash40/LEITURA.md` — flash 40 first-boot reading and the upload-skip finding.
- `biosmod_8902_co/construcoes/95-a37-ptdid-43d1/capturas/20261125-boot2-pos-corte/LEITURA.md` — post-PSU-cut boot (negative).
- `biosmod_8902_co/construcoes/96-a38-varredura-id/README.md`, `capturas/20261125-boot-iomem/LEITURA.md` — A38 design and why it could not be read.
- Cross-links: [05](05-gen4-the-clamp.md), [09](09-psp-driver-re.md), [10](10-negative-results.md), [11](11-build-catalog.md), [12](12-timeline.md), [13](13-open-questions.md).
