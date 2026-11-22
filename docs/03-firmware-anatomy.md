# 03 — Firmware anatomy of the ASUS 8902 image

## Summary

This document records the structure of the ASUS ROG Crosshair VI Hero BIOS 8902
`.CAP` image as we measured it offline: the raw FV map, the LZMA-alone envelope
that stores the FVMAIN region compressed, the FFS/section layout and its
checksum rules, the AMI **VZL1** container (which turned out *not* to be
compression but a header-stripped raw PE), the PSP directory inside the image,
and the extraction chain for the x86 policy PEIM ("TE"). All numbers were
measured by our own parsers; the house rule is that every build pins the base
SHA-256 and every claim carries the file that measured it.

Base of reference unless noted: official ASUS 8902, SHA-256 `04ddae2d0650353ec7bafa50a281528791a74694960f2104ac9d53657b0b6bba` (sha pinned in `build.py`) `(src: biosmod_8902_co/construcoes/93-a36-pbo-co-nativo-safe/build.py)`. The board image we dissected is a 16 MiB body `(src: biosmod_8902_co/bancada-uefi/replay/README.md "corpo de 16 MiB")`.

## Raw FV map of the CAP

Our parser measured 5 firmware volumes (FV signature GUID starting `8c8ce578-…`, the EDK2 FV GUID — public knowledge) in the uncompressed CAP, plus 9 `_FVH` signatures (5 valid) and 13 `$PSP` markers `(src: biosmod_8902_co/construcoes/41-vzl1-re/notas-coordenador.txt)`:

| FV at CAP offset | Size | Role we measured |
|---|---|---|
| `0x40800` | `0x20000` | contains the default NVAR store (decoded later, T57) |
| `0x610800` | `0x40000` | uncompressed module FV |
| `0x9e0800` | `0x4a0000` | contains 3 type-1 Windows DLLs (T57) |
| `0x9e10e0` | `0x1000` | small FV |
| `0xe80800` | `0x180000` | **outer PEI FV** — 12 files; one of them is the zlib container of the inner PEI FV |

Also pinned by measurement: the PSP directory `$PSP` at CAP `0x3f8800`
(parse below); the BL reset-image blob `$BL2` at CAP `0xe82800` (LZMA, size
`0xdb060`, destination RAM `0x9c7ffe0`, tags "reset image, copy image")
`(src: biosmod_8902_co/RASTRO.md §56/T56)`; the FVMAIN PKCS#7 signature at CAP
`0xe02250` `(src: biosmod_8902_co/construcoes/85-a28-g4pbo-safe/build.py)`;
the APOB region at SPI `0x101000–0x10e087` (~53 KB, measured from a flash dump)
`(src: biosmod_8902_co/RASTRO.md §II)`; PSP `NV_DATA` at SPI `0xa0000`
(container copy at CAP `0xa0800`) and PSP NVRAM at SPI `0xc0000` (256 KB) — the
latter read all-FF (dead) in three dumps `(src: biosmod_8902_co/analises/11-cadeia-psp-executor/README.md)`.
The only unreadable blob in the whole package is the PSP HIC at `0x881200/0x670`
(encrypted, and identical across both of our base images) `(src: biosmod_8902_co/RASTRO.md M18)`.

## FV and FFS layout (EDK2 with AMI specifics)

FV header: volume length u64 at `fv+32`, `_FVH` signature at `fv+40`, header
length u16 at `fv+48`, extended-header offset u16 at `fv+52`; if extended, its
size is u32 at `extoff+16` and files begin at `(extoff + size) & ~7`, else at
`headerLength & ~7` `(src: biosmod_8902_co/construcoes/93-a36-pbo-co-nativo-safe/build.py files())`.
Each FFS file is a 24-byte header: GUID (mixed-endian, bytes 0:16), file type
at byte 18, `state` at byte 23, size u24 at bytes 20:23; files are 8-aligned
`(src: biosmod_8902_co/construcoes/41-vzl1-re/notas-coordenador.txt)`.
Our modules' file header carried state/attr `aa` and a trailing `f8` like the
dispatching native ones `(src: biosmod_8902_co/trabalhos/53-predicado-dinamico-despacho-peicore.md)`.
Sections inside a file: size u24 + type u8, 4-aligned. Types we used: `0x10`
(PE32), `0x11`/GUIDed-LZMA, `0x12` (VZL1, AMI), `0x19` (raw/GUID-defined
metadata), `0x1B` (DXE/PEI dependency expression; our files carried `06 08`).

Checksums (the rules our writers implement and verify):
- header checksum byte `f[16]` = −sum of all u16s of the 24-byte header,
  **computed with `f[16]=0` first**;
- if attribute bit 0x40 (`f[19] & 0x40`) is set, data checksum byte `f[17]` =
  −sum of the file data bytes `(src: biosmod_8902_co/HANDOFF-FINAL-20261122.md §6)`
  (the same file's `prepare.py` reference parser lives at
  `~/Documentos/Projects/biosmod_v2/diagnostics/8902-boot-trace-20261115/prepare.py`;
  A28's build recomputed "header 0x16 + data 0x17 se attr 0x40" and preserved
  the state byte `(src: biosmod_8902_co/construcoes/85-a28-g4pbo-safe/build.py)`).

## The LZMA-alone envelope holding FVMAIN

The DXE-side FVMAIN volume is stored in the CAP as a custom LZMA
GUID-defined envelope: the 16 stored bytes
`98 58 4E EE 14 39 59 42 9D 6E DC 7B D7 94 03 CF` (the EDK2 LZMA custom-section
GUID in little-endian byte order — public knowledge), followed by a raw
**LZMA ALONE** stream at `envelope+20`: 5 property bytes at `+20`, uncompressed
size u64 at `+25`, data from `+33` `(src: biosmod_8902_co/construcoes/93-a36-pbo-co-nativo-safe/build.py)`.
In the 8902 official image this envelope sits at CAP `0xa9ff24` and is found by
searching the GUID and keeping the *unique* occurrence whose u64 at `+25`
equals the decompressed size **16 162 832** `(src: biosmod_8902_co/construcoes/85-a28-g4pbo-safe/build.py "LZMA ALONE @0xa9ff24"; build.py get_fvmain)`.

Measured envelope properties: `5d 00 00 00 01` → lc=3 lp=0 pb=2, dict 16 MiB;
our recompressor uses `nice_len=273` (the "A22/A24 ruler")
`(src: biosmod_8902_co/construcoes/85-a28-g4pbo-safe/build.py)`.

Recompression pipeline (the house pipeline, used unchanged from A22 to A36):

1. decompress FVMAIN with FORMAT_ALONE; patch the raw PE32 sections
   inside (same-size byte swaps only — `len(old)==len(new)` asserted);
2. re-compress with the **original props** (`lc/lp/pb` decoded from props byte
   0, dict from the next 4 bytes) plus `nice_len=273`;
3. assert the new stream is **≤ the original stream length** (measured by
   binary search: smallest prefix of the original that decodes complete);
4. write `props + u64(size) + raw` back in place, padded with `0xFF` to the
   original stream span — the UEFI decoder stops at the declared size, so
   trailing `FF` is invisible;
5. assert everything before `G+20` and after `G+20+old_stream_len` is
   byte-identical, and that a re-run of the extractor on the output reproduces
   the patched FV `(src: biosmod_8902_co/construcoes/93-a36-pbo-co-nativo-safe/build.py main())`.

The same recipe is applied recursively inside the volume: a module whose body
is itself a GUIDed-LZMA section (e.g. the setup front `fe612b72-…`, decompressed
195 904 B) is recompressed with its own original props and rebuilt **at the
same section size** with `0xFF` padding `(src: biosmod_8902_co/construcoes/85-a28-g4pbo-safe/build.py)`.

The PKCS#7 signature over FVMAIN at CAP `0xe02250` is left **intact** (live in
official/A23/A28; a previous third-party hack had zeroed ~70 KB of certificates
there, and our "clean" A28 deliberately restored a valid state
`(src: biosmod_8902_co/trabalhos/85-a28-g4pbo.md; construcoes/85-a28-g4pbo-safe/build.py)`).
Note the asymmetry we measured on the board: the in-BIOS flasher (EZFlash)
rejects **any** modified CAP as invalid (owner-observed, reported 21/11), so
every built CAP in this campaign went in through the USB FlashBack recovery,
which accepted them (owner-observed, ~40 flashes)
`(src: biosmod_8902_co/RASTRO.md §II; HANDOFF-FINAL-20261122.md §7)`. *Why*
FlashBack does not enforce that signature is not explained by any of our
sources — see Open questions.

## VZL1 — not a compressor, a header-stripped PE container

All 164 native section-`0x12` payloads of the inner PEI FV (plus the only two
VZL1 modules in the clear in the raw CAP, FFS `@0xff07e8` GUID `bb3bf734-d640-4cf5-afea-ca8cfa6020d1` size 370 and `@0xfff7e8` GUID `4cc14f19-c626-4ab6-9dea-ca6c01fd10cd` size 498, magic at body `+0x1c`) were decoded with one stdlib parser: **166/166 validated as PE** (165 i386 + 1 x64) `(src: biosmod_8902_co/construcoes/41-vzl1-re/README.md)`.
VZL1 is **not compression** — zlib/LZMA/xz/deflate-raw all failed because there
is nothing to decompress (our exhaustive brute-forcing is recorded in
`notas-coordenador.txt`). The format (40-byte header, little-endian):

| field | meaning |
|---|---|
| `[00:04]` | `'VZ'` + machine LE: `56 5A 4C 01` = VZ+i386 (0x14C); x64 = `56 5A 64 86` (0x8664). Code tests only the word `'VZ'` (`cmp word,0x5a56`), which is why a 4-byte magic search never found a comparator |
| `[04]`,`[06]` | variant bytes (0x02..05 / 0xa8..0xc8); `[05]=0x0B`, `[07]=01` — no measured effect on layout |
| `[08:12]` | original **AddressOfEntryPoint (RVA)** — equals `[12:16]` in 163/166 samples |
| `[12:16]` | original **SizeOfHeaders** (0x200..0x2a0); *not* a payload offset |
| `[16:20]` | **ImageBase** (clear immediates in the blob equal `ImageBase+RVA`) |
| `[20:24]` | zero |
| `[24:28]` / `[28:32]` | **VA / virtual size of `.reloc`** (or end of image) — NOT an entry point |
| `[32:40]` | zero |
| `[40:40+40N]` | standard COFF section table (name, VS, VA, raw size, PtrRaw==VA, relocs/lines, characteristics) |
| after table | **the original PE file bytes starting at SizeOfHeaders** — contiguous sections, file-offset == VA |

Reconstruction = synthesize a `SizeOfHeaders`-sized PE header + blob → valid
PE `(src: biosmod_8902_co/construcoes/41-vzl1-re/README.md; revisao-coordenador.txt)`.
Erratum we recorded: the "native EP 0x5b40/0x2f80" quoted by an earlier flash
forensics pass were `.reloc` VAs, not entry points (the real PeiCore EP is
`0x240`) `(src: biosmod_8902_co/construcoes/41-vzl1-re/revisao-coordenador.txt)`.

The decoded AMI PeiCore (`out/peicore_dec.bin`, IA32, EP `0x240`, ImageBase
`0x09C82ED4`) immediately explained the module-format handling: the image
getter `0x2dc5` **tries section `0x12` first and falls back to `0x10`** — which
is why our plain PE32 (`0x10`) modules are accepted at all; loader-side test
`0x41c4` is `word[ecx]=='VZ'`; machine gates at `0x2e35/0x43a9` reject anything
but 0x14c/0x8664 `(src: biosmod_8902_co/construcoes/41-vzl1-re/README.md)`.
The PeiCore's own FFS in the inner FV is at inner offset `+0x3040`
(its EDK2 GUID `52c05b14-0b98-496c-bc3b-04b50211d680` appears only there and
inside the core body) `(src: biosmod_8902_co/RASTRO.md §56)`.

## PSP directory inside the image

The directory `$PSP` at CAP `0x3f8800` holds 31 × 16-byte entries; a directory
entry points to a container `src`; house rule for the 8902 layout: `$PS1`
header at `src+0x810`, body at `src+0x900` `(src: biosmod_8902_co/trabalhos/31-e1-mesa-tarefas-e-registro.md §disposição; trabalhos/20-post-mortem-swap-carregabilidade-rv1.md)`.
Measured body ranges from that parse: e02 kernel (type 2, src `0x410900`, size
`0x102d0` → body `0x411200..0x420BD0`), type `0x108` = `0x420C00..0x441400`,
type `0xC` = `0x442200..0x462300`, container type `0x28` src `0x469700`.
(The e02 kernel turned out to be a dead island for host traffic — see docs 09/10.)

Two per-slot observations of the `$PS1` magic: 7306-era slot `@0x6da500` has
`$PS1@+0x10` (and `RV1@+0x64`); 8902 `@0x469e00` has `$PS1@+0x110`
`(src: biosmod_8902_co/trabalhos/20-post-mortem-swap-carregability-rv1.md)` [sic — file: `20-post-mortem-swap-carregabilidade-rv1.md`].
Inside a signed container, the `$PS1` header carries the **anti-tamper
self-anchor: `sha256(body)` recorded at `PS1+0xc0`**, itself covered by the AMD
signature chain rooted on-chip (root `6C9E` in PSP ROM — not in the flash; map
`6C9E → BL → 259C→ABL0 / 24C6→TOS / 118D→HIC(encrypted) / 96A0→SMU`). Editing
one body bit breaks the anchor; fixing the anchor breaks the signature
`(src: biosmod_8902_co/RASTRO.md §P).` A cross-era official module with a
zeroed anchor field was already measured to be rejected with POST code **F9 +
recovery** (T19) `(src: biosmod_8902_co/RASTRO.md §P)`.

**Directory attribution, final answer.** Early in the campaign we labelled one
directory "dir1 Zen3 ACTIVE" (its e03 SMU at CAP `0x82be00`, packed `0x210d0` →
`0x40000`; e07 SMU at `0x86d500`, packed `0x11c00` → `0x40000`; PSP driver
0.11.0.87 bodies at `0x895094` (59 716 B) and the second copy at `0x713094`,
container `@0x889200`) and another "dir6 Zen2 INERT" (driver 0.14.0.43 at
`0x469f00`). On 22/11 we measured the kernel's reported `ryzen_smu: SMU
v56.76.0` against the SMU version fields of every directory header and
**corrected the labels**: the directory this 5800X3D actually loads is
`0xBC0B0500` (sub1: SMU `@0x421400` = **56.76.0**); `0xBC0C0140` ("dir1") is
**Cezanne** (e03 = 64.74.0) and `0xBC0C0000` is Renoir (55.95.0); sub0
`@0x518400` is Matisse (46.73.0). So e03/e07 and driver 0.11.0.87 are Cezanne
APU content that **never loads on this machine**, while the "inert Zen2" driver
0.14.0.43 is the **active** PSP driver `(src: biosmod_8902_co/RASTRO.md §DDD; analises/16-diretorio-psp-ativo/out/resultado-a28.txt)`.
(Contradiction noted: `analises/11-cadeia-psp-executor/README.md` calls the
e03/e07 streams "LZMA"; the extraction that actually produced `e03_full.bin`/
`e07_full.bin` used **zlib at packed+0x100** and HANDOFF §6 repeats zlib — we
go with zlib.)

The active driver container header (read by our script): magic `$PS1` at
`blob+0x10`, version `00140043`, signed size `0x1a590` bytes + `0x100` bytes of
signature `(src: biosmod_8902_co/analises/16-diretorio-psp-ativo/scripts/gen4dis_driver_ativo.py)`.
Its chipset policy table (whitelist, 24 × 12 bytes) is at CAP `0x480a70`; the
X370 devid `0x43b9` appears as entries 0 and 23 with flags `01 01 00 01`
`(src: biosmod_8902_co/analises/16-diretorio-psp-ativo/out/resultado-a28.txt; RASTRO.md §DDD)`.

## The TE extraction chain (x86 policy PEIM)

The PEIM we call **TE** (GUID `21be6180-733a-443b-df46-41c008047687`, file type
0x06) is the only x86 module that speaks the PSP-policy window protocol; its
chain of extraction from the CAP:

```
CAP outer PEI FV @0xe80800 (0x180000)
  → container GUID 3e3b6dc0… (zlib; payload decompressed from offset 32 in)
    → inner PEI FV, decompressed 3 670 016 B (= 0x380000)
      → FFS at inner 0xe3d40  (TE, PEIM 0x06)
        → section 0x12 VZL1 → blob = PE flat, RVA == file-offset
          → PE32 i386, ImageBase 0x9d63c40, EP RVA 0x240
```
`(src: biosmod_8902_co/HANDOFF-FINAL-20261122.md §6; analises/14-writer-census/README.md inner_21be6180_e3d40@e3ddc.pe.bin; analises/15-te-writer/README.md)`

The inner FV decompressed is where the PeiCore, the SEC, the APRIORI file and
all 172 native PEIMs live (184 files total: 172 type-06 PEIMs, 1 type-04 core,
type-02 apriori, type-F0 pads). Our decoded copies: `inner_limpa.bin`
(sha `015e03b4…`) vs `inner_rc1` (sha `89e70e33…` — RC1 carries V2-era modules,
so the two differ) `(src: biosmod_8902_co/RASTRO.md §56; construcoes/41-vzl1-re/notas-coordenador.txt)`.
The SEC is the single type-03 file at inner `+0x37bac8` (ImageBase nominal
`0x09ffb958`, EP `0x2f00`) and is the caller of the PeiCore (see doc 04)
`(src: biosmod_8902_co/RASTRO.md §58)`.

## Safe rebuild rules (the house pipeline)

- Never edit in place: build in a new tree, pin base SHA-256 by re-computing
  (`sha256sum`), assert the base matches before touching bytes.
- **Same-size patches only** (`len(old)==len(new)` asserted per patch, with the
  old byte pattern asserted at the exact module offset; unique-module lookup by
  GUID inside the decompressed volume) `(src: biosmod_8902_co/construcoes/93-a36-pbo-co-nativo-safe/build.py)`.
- Recompressed streams (envelope or inner GUIDed section) must be ≤ the
  original, padded `0xFF`; FFS checksums recomputed per the rules above;
  everything outside the patched region byte-identical to base ("confined
  diff") `(src: biosmod_8902_co/construcoes/85-a28-g4pbo-safe/build.py; HANDOFF-FINAL-20261122.md §6)`.
- Signed AMD containers (PSP BL/TOS/drivers, SMU) are left untouched by all
  clean builds; where experimental patches were authorized, they were byte-
  count-verified (e.g. A21: exactly 6 bytes) and staged with the recovery path
  documented (clear-CMOS → FlashBack) `(src: biosmod_8902_co/RASTRO.md §P; HANDOFF §7)`.
  The verification is real, not folklore: A34 (a 2-byte data edit in the
  whitelist of the *actually loaded* driver) measured **non-POST** on the board
  (flash 37) — the first genuine test of the active driver's signature check,
  which an earlier edit into never-loaded Cezanne drivers had falsely suggested
  was inert `(src: biosmod_8902_co/RASTRO.md §FFF, §DDD)`.
- Determinism: the build script is run twice and outputs compared
  (byte-identical), an independent `verify.py` re-walks FFS sections and
  asserts the whole patch set, and the candidate module is exercised in a
  QEMU/OVMF VM before staging (exit code 33 = our harness "probe ran")
  `(src: biosmod_8902_co/bancada-uefi/README.md; RASTRO.md §55)`.
  The offline bench (QEMU + archived DXE-entry capture, 1 168 SMN readings)
  is the way we sanity-check probe logic without a board `(src: biosmod_8902_co/bancada-uefi/replay/README.md)`.

## Open questions

- No source explains *why* FlashBack does not enforce the FVMAIN PKCS#7
  signature (only the owner-observed EZFlash rejection vs FlashBack acceptance).
- VZL1 variant bytes `[04]/[06]` (0x02..05 × 0xa8..0xc8) have no measured
  correlation to layout (unresolved in T41).
- The full physical form of the PSP directory entry table (field meanings
  beyond src/type) was only partially parsed (T31).

## Sources

- `biosmod_8902_co/HANDOFF-FINAL-20261122.md` §4, §6 — authoritative extraction recipes, checksum rules, container chain.
- `biosmod_8902_co/construcoes/93-a36-pbo-co-nativo-safe/build.py` — LZMA-alone envelope pipeline, props, FF padding, same-size patch asserts.
- `biosmod_8902_co/construcoes/85-a28-g4pbo-safe/build.py` — envelope @0xa9ff24, props ruler, PKCS#7 @0xe02250, inner-section recompression recipe.
- `biosmod_8902_co/trabalhos/85-a28-g4pbo.md` — PKCS#7 history (gambiarra vs clean A28).
- `biosmod_8902_co/construcoes/41-vzl1-re/{README.md,notas-coordenador.txt,revisao-coordenador.txt}` — VZL1 format, validation, raw FV map, shims, errata.
- `biosmod_8902_co/trabalhos/41-pesquisa-vzl1-despacho-ami.md` — VZL1 pre-decode facts (payload 0x240, failed decompression attempts).
- `biosmod_8902_co/trabalhos/31-e1-mesa-tarefas-e-registro.md` — `$PSP@0x3f8800` parse, e02 ranges.
- `biosmod_8902_co/trabalhos/20-post-mortem-swap-carregabilidade-rv1.md` — `$PS1` per-slot offsets.
- `biosmod_8902_co/analises/16-diretorio-psp-ativo/{out/resultado-a28.txt,scripts/gen4dis_driver_ativo.py}` — directory→SMU-version table, active driver header fields, whitelist.
- `biosmod_8902_co/analises/11-cadeia-psp-executor/README.md` — driver body offsets (0x895094/0x713094), NV_DATA/NVRAM regions.
- `biosmod_8902_co/analises/12-smu-e07-restore/README.md` — e03/e07 packed sizes, zlib@+0x100, 0x40000.
- `biosmod_8902_co/analises/14-writer-census/README.md` / `analises/15-te-writer/README.md` — TE blob identity (0xe3d40@e3ddc, ImageBase 0x9d63c40, EP 0x240).
- `biosmod_8902_co/RASTRO.md` (M18, M26, §II, §P, §56, §58, §DDD) — HIC, APOB, signature chain, $BL2, SEC, directory-label correction.
- `biosmod_8902_co/bancada-uefi/README.md`, `bancada-uefi/replay/README.md` — offline QEMU bench, 16 MiB CAP body, A2 capture sample.
- `biosmod_8902_co/trabalhos/53-predicado-dinamico-despacho-peicore.md` — FFS header state/attr `aa` of our modules vs dispatched ones.
