# 16 — Glossary

## Summary

Terms that actually occur in this repo's docs, grouped by theme, defined in one sentence
each with a pointer to the doc that uses it most.

## Firmware containers

| term | meaning |
|---|---|
| **CAP** | ASUS's signed BIOS-update container format — the file type every image in this campaign was built, flashed and hashed as (docs/03, docs/11). |
| **FV (Firmware Volume)** | EDK2's top-level storage region inside the image; five were measured in the 8902 CAP (docs/03). |
| **FFS (Firmware File System)** | EDK2's file layout inside an FV: file and section headers with their own checksum rules (docs/03). |
| **GUID-defined section** | EDK2 section type that wraps a compressed payload — the envelope holding FVMAIN (docs/03). |
| **LZMA-alone** | The compression envelope FVMAIN is stored in; our stdlib codec round-trips it byte-exact (docs/03, `tools/firmware/`). |
| **VZL1** | The AMI container that looks like a compressor but is not — a header-stripped raw PE blob, decoded in T41 (docs/03). |
| **TE (Terse Executable)** | Compact UEFI executable format; "TE `21be6180`" is the x86 vetting PEIM dissected in docs/09 §4. |
| **$PSP / $PS1** | Markers of AMD firmware directories inside the image; the `$PS1` header carries the per-slot anti-tamper digests (docs/03). |
| **AGESA** | AMD's Generic Encapsulated Software Architecture — the bulk of the compressed payloads swept by the writer censuses (docs/09, docs/10). |
| **APCB / NBIFS** | AMD's platform-configuration block (identical across both bases) and NBIO-firmware storage (absent from this image) — two more reasons the clamp writer is not in the flash (docs/09 §6, docs/10). |

## PSP, SMU and NBIO

| term | meaning |
|---|---|
| **PSP (Platform Security Processor)** | On-chip ARM service processor (Thumb code) running its own OS: boot loader **BL**, trusted OS **TOS**, and PSP-OS driver modules (0.11.0.87 legacy, 0.14.0.43 active) (docs/04 §0, docs/09). |
| **SMU (System Management Unit)** | Separate signed microcontroller (Xtensa firmware) that answers the mailbox and enforces platform policy (docs/04 §0, docs/09). |
| **mailbox** | The x86↔SMU request/response interface, captured live as a 38-request boot trace in which the Gen4 clamp sits inside request 30 (docs/04 §3). |
| **MP1 message** | Class of SMU messages used by the native Curve-Optimizer chain (`0x35`/`0x36`) and the PBO scalar (`0x2f`) (docs/07). |
| **strap** | AMD configuration value written by the signed chain; index `0x84` = `GEN4_DIS`, the anti-Gen4 strap (docs/05 §1–§2). |
| **clamp** | This campaign's shorthand for the Gen3-forcing mechanism — named as function `0x3230` of the active PSP driver, with three write groups over the `0x0904_xxxx` page (docs/05 §2–§3). |
| **QCB** | Queue Control Block — the PSP mailbox's message boxes at SMN `0x03b10700/704/718` ("box 12"), whose x86 reachability measured dead (docs/05 §6, docs/08 §2). |
| **doorbell** | The command-ring write used by the PSP-side commit mechanism (e.g. `0x0904_67ac := 0xFFFE0084`), with receipt keys found inside SMU bodies (docs/09 §5). |
| **devid** | The platform's device identity (e.g. `0x43b9` = X370) served by the SMU and matched against PSP whitelists — the chipset-validation input the CO gate depends on (docs/09 §3–4). |
| **SMN (System Management Network)** | AMD's internal register fabric, reached from x86 via the CF8/CFC gateway; it routes NBIO windows but not SMU/PSP pages (docs/08 §1/§7). |
| **CF8/CFC** | The PCI config-address/data port pair serving as the SMN gateway (`0xCF8 = 0x80000000|address`, data from `0xCFC`) used by every probe here (docs/08 §1). |
| **NBIO / NBIF** | The chipset complex hosting the CPU's PCIe root ports (and its function blocks, the `0x0380`/`0x0382`–`0x0385` SMN families); its policy block `0x0381xxxx` is where the Gen3 decision lands (docs/05 §4, docs/08 §3). |
| **proxy (`0x03810054`)** | The NBIO policy-register candidate whose value differs between armed and clamped states (witness `0x001A43B9`); its echo-proven write refuted "proxy alone" (docs/05 §4). |
| **HIC** | The only encrypted (hence unreadable) blob in the image — inert and identical across bases, so it cannot be the differential clamp writer (docs/09 §6). |
| **RSMU** | Root SMU register block; the named remaining research target (`+0x01c/+0x020/+0x914`) before any future x86 write CAP (docs/05 §7). |

## UEFI setup and overclocking

| term | meaning |
|---|---|
| **AOD / AOD_SETUP** | AMD's overclocking setup driver and its NVRAM data block; capability byte `0xdf` (written then deliberately zeroed) is what hides the PBO and Curve-Optimizer pages on the 5800X3D (docs/07 §1). |
| **PBO (Precision Boost Overdrive)** | AMD's power/current-limit override, hidden on this board until the A36 flag NOPs exposed it natively (build-side; the A36 board confirmation was pending, docs/07 §1/§6). |
| **Curve Optimizer (CO)** | Per-core voltage-offset control; its application chain (table builder → SMU DXE driver → MP1 `0x35/0x36`) was already alive here — only the menu door was missing (docs/07 §1–§3). |
| **IFR** | The setup pages' binary form representation (forms, questions, conditions) that our dumps parsed to find what renders and what hides (docs/07 §1). |
| **SUPPRESS_IF** | The IFR visibility condition; exactly two of them, on qid `0x4f0`, are the only readers of the hidden capability byte (docs/07 §1). |
| **qid** | Numeric identifier of a setup control within the IFR forms, e.g. the hidden gate qid `0x4f0` (docs/07 §1/§6). |
| **token** | Numeric setup-variable identity (the boost formula reads `token 0xed`) — and, in PSP disassembly, the payload value of a doorbell write; context distinguishes the senses (docs/07 §4, docs/09 §4). |
| **varstore** | A named NVRAM region holding one front-end page's setup variables (docs/07 §6). |
| **OCMR** | The ASUS overclocking varstore (`VARSTORE_OCMR_SETTINGS`, 7611 B) backing the ASUS OC page and its hidden-numeric quirks (docs/07 §6). |
| **`.CMO`** | ASUS BIOS user-profile format: an EFI 1.1 compressed stream (8-byte header, PBIT=4) that our codec reproduces byte for byte (docs/07 §8). |
| **efivar / efivars** | The Linux kernel's sysfs exposure of UEFI variables (`/sys/firmware/efi/efivars`) — the campaign's sudo-free, read-only log channel off the board (docs/08, docs/14). |
| **FlashBack / EZFlash** | The two ways onto this board's flash: USB recovery FlashBack accepts modified images (the owner's route back from every failed boot — flashes 7/18/37), the in-setup EZFlash rejects them (docs/03, docs/12, docs/02 §1). |
| **POST code (F9)** | AMI BIOS boot diagnostic code; F9 (memory-init/training failure) is the intermittent symptom analyzed in docs/15. |

## Boot and PCIe

| term | meaning |
|---|---|
| **SEC / PEI / DXE** | The UEFI boot phases after reset; the PSP/SMU chain runs before them, and our instruments ran in PEI and DXE (docs/04). |
| **ReadyToBoot** | The UEFI event just before OS handoff, used as the observation point for final link state (docs/04 §4). |
| **LTSSM** | PCIe Link Training and Status State Machine — the trainer whose end signal brackets the clamp window; writing its registers before native training hangs boot (M28) (docs/10). |
| **AER** | PCIe Advanced Error Reporting counters; `0x30c1` (correctable errors) is the Gen4-era quality figure that was measured once and never re-instrumented (docs/06). |
| **FCLK** | Infinity Fabric clock — 1900 MHz in the owner's memory profile (docs/15). |
| **XMP** | The memory overclock-profile standard the owner's kits use; the flash-33 XMP retrain left link policy at Gen3 (docs/12, docs/15). |

## Campaign naming and method

| term | meaning |
|---|---|
| **`C6H.<FAMILY>.<variant>`** | The CAP naming convention: board prefix (Crosshair VI Hero), family code (`CO*`, `SV*`, `SONDA`, `REVET`, `MESA`, `SMN12`, `NBIO-B`, `W1`, `PEIPROBE`, `SMU101`, `PG0904`, `OBSPEI`), variant letter (docs/11). |
| **REVET** | The Curve-Optimizer "flip" patch family; **REVET-P2** is the accepted CO-half image of phase 1 (docs/11 §2, docs/05 §5). |
| **W1** | The first proxy-write ("unclamp") module family — two of the three witnesses to the PEI-dispatch triple death, with PEIPROBE (flashes 12/13/14) (docs/08 §4, docs/10). |
| **OBSPEI** | The read-only DXE observer family (flashes 17–21) that mapped HOBs/ctx/NVRAM and, through its own crashes, derived the platform's safe-variable-size rule M27 (docs/08 §5). |
| **RC1 / REL1 / anchor (âncora)** | GEN4-REL1 — kept as the reference "RC1" (`sha 8b19a729…`), the Gen4-skip image held on the USB stick as the campaign's safe recovery anchor (docs/11 §0, docs/06 §5). |
| **Front A / Front B** | The two permanent tracks — A: Gen4 via skip base; B: clean 8902 with the chipset check ON — whose bases and results were never mixed (docs/05 §5, `biosmod_8902_co/frentes/`). |
| **flash N** | Numbering of the physical board flashes (1–39 — flash 39 was pending, never executed — plus a few unnumbered runs), used as the evidence identifier throughout the docs (docs/12). |
| **RASTRO / M-registry** | The master anti-repetition log (`RASTRO.md`), whose §B records dead paths M1–M27 (M28–M30 added later in the log) with the measurement that closed each (docs/10 part (a), docs/02 §5). |
| **prediction matrix** | The pre-registered table of named outcome branches and the decision each forces, written before building or flashing (docs/02 §2, docs/10). |
| **echo doctrine** | Every write is bracketed by a read-before and a read-back-after, inside built CAPs only — no blind writes ever (docs/02 §3). |
| **régua** | Portuguese for "gauge": the coordinator's independent acceptance re-check of a build — re-run the release, re-derive the target table from the spec, run a per-task gate script (docs/02 §4, docs/11 §7). |
| **owner-observed** | Label on claims resting on the owner's direct board experience (menu behavior, POST codes) rather than a captured artifact (docs/15, docs/07). |
| **Vermeer / Matisse / Cezanne / Renoir** | AMD client codenames used to attribute PSP/SMU firmware generations to CPU families — the attribution erratum (never-loaded Cezanne blobs) is told in docs/09 §2. |
| **X3D** | The 5800X3D's 3D V-Cache SKU, whose low fuse field mis-scales the stock boost override — the reason A36 exists (docs/07 §4). |

## Sources

- Docs 03–15 of this repo — every term above was verified to occur in them by text search
  (candidates that do not occur, such as `HII` or `TSE`, were deliberately omitted).
- `biosmod_8902_co/RASTRO.md`, `HANDOFF-FINAL-20261122.md`, `trabalhos/*.md` — original
  usage of the campaign terms (M-numbers, flash numbering, family names).
