# 14 — Tooling: what is in `tools/`, how to use it, and the method gotchas

## Summary

This repo ships the campaign's own analysis, build and verification tools —
translated to English, with personal paths removed and every input path taken
from `argv`. The tools fall into six families: **setup/profile** (decompress
and inspect the BIOS user profile; docs/07), **firmware** (CAP → FVMAIN →
FFS module extraction chain; docs/03), **x86 RE** (disassembly grep, module
pull, call survey), **PSP/Thumb/Xtensa RE** (active-directory attribution,
function maps, NVS decode, literal cross-reference; docs/09), **scans**
(the 74 MB writer census and Xtensa literal xrefs that closed doors in
docs/10), **probes + offline replay** (the read-only SMN DXE/PEI probe
skeletons from docs/08 and the QEMU/OVMF harness that tested probe logic
against archived board readings before any flash).

One tool doubles as the campaign's strongest reproducibility test:
`tools/build/fvmain_bytepatch.py` rebuilds the final A36 BIOS **byte for
byte** from the official 8902 image (see "Reference build" below).

Nothing here contains firmware content. You must supply your own BIOS images
(see "Supply your own firmware"). Every script was smoke-tested against
synthetic inputs built for this repo; the byte-fidelity of the translated
logic was checked with AST diffs against the originals in the campaign tree.

## Tool map

All commands assume you are inside this repo and run Python 3 with `-I`
(see the gotcha about `-I` below).

### tools/setup/ — profile and setup data (docs/07)

| Tool | What / how to invoke |
|---|---|
| `efi11_decompress.py` | EFI 1.1 (Tiano LZ77+Huffman) decompressor, pure stdlib, the public EDK2 `Decompress.c` algorithm. `efi11_decompress.py <input> <output> [pbit]` |
| `cmo_parse.py` | Reader for a decompressed ASUS `.CMO` user profile: header, schema (typedef text) and `$ProfileData(NAME)` hex sections. `cmo_parse.py <bin>` |
| `dump_ocmr.py` | Lists the option values of the `VARSTORE_OCMR_SETTINGS` section (varstore 0x20) cross-referenced with a decoded IFR dump. `dump_ocmr.py <profile.bin> <setup_ifr_all.txt> [all]` |
| `fix_boost_profile.py` | Produces the corrected profile for the A36 BIOS (the boost-formula fix, docs/07). `fix_boost_profile.py <decompressed.bin> <out.bin>` |
| `efitool.c` | EDK2 BaseTools-style utility (see the build comment inside; it is not standalone-compilable). |

### tools/firmware/ — volume and module extraction (docs/03)

| Tool | What / how to invoke |
|---|---|
| `fv_decompress.py` | Extracts the main DXE volume (FVMAIN) from an 8902-family CAP. `fv_decompress.py <cap> <out_fv.bin>` |
| `fv_ls.py` | Lists the FFS files of a decompressed volume (538 files in 8902's FVMAIN). `fv_ls.py <fv.bin> <listing.txt>` |
| `ffs_unpack.py` | Extracts one FFS module by GUID prefix and splits its sections (LZMA sections decompressed). `ffs_unpack.py <fv.bin> <guid-prefix> <out-stem>` |

### tools/x86re/ — x86 module RE

| Tool | What / how to invoke |
|---|---|
| `disgrep.py` | Regex-grep a **disassembly** of every executable section of a PE32/PE32+ (capstone, `skipdata` on, so data islands never abort the pass); prints `address raw-bytes mnemonic operands`. This is how the two capability-flag stores that A36 NOPs (`mov byte ptr [rbx+0xdf],bpl`) were found. `disgrep.py <pe.bin> <python-regex>` — requires `pip install capstone`. |
| `modpe.py` | One-line "give me the driver": finds an FFS file by GUID in a decompressed FVMAIN, decompresses its LZMA (GUID-defined type 0x02) sections recursively, writes `<outdir>/<guid8>.pe.bin` (the raw PE32 section, AMI type 0x10) and prints the UI name (section 0x15, UTF-16LE) + SHA-256. `modpe.py <fv.bin> <outdir> <guid>...` |
| `callargs.py` | For every `call` in a module, surveys which argument registers (`edx/ecx/r8d/r9d/rdx/rcx`) carry small immediates in the 0x30 bytes before it — turns "who calls this with which constant" into a list. `callargs.py <pe.bin>` |
| `thumb_dis.py` | Small hand-written Thumb-16 disassembler for bodies capstone mis-flags (BL/BLX encoding quirks). `thumb_dis.py <blob.bin> <start_hex> <length_hex>` |

### tools/psp/ — PSP OS / firmware bodies (docs/09)

| Tool | What / how to invoke |
|---|---|
| `psp_active_dir.py` | The active-directory attribution pass: prints the four SMU versions carried per directory (header at +0x60 — compare with the kernel's `ryzen_smu: SMU vX.Y.Z` line), the PSP driver's magic/version/signature split, disassembly of the commit function (svc 0x7c = `write(addr,value,size)`, svc 0x7b = read) with its sole gated caller, and the 24×12 devid whitelist table. `psp_active_dir.py <CAP>` |
| `thumb_funcmap.py` | Prologue scanner + function outline for a Thumb body (with `bl` targets resolved). `thumb_funcmap.py <body.bin> [target_hex [end_hex]]` |
| `nvs_decode.py` | Decodes the NVS region (zlib stream right after the `NVS` tag at file offset 0x90000 of a SPI dump): size, SHA-256, first 256 bytes hexdump, printable strings. `nvs_decode.py [--out DIR] dump.bin...` |

### tools/scans/ — whole-image evidence scans (docs/10)

| Tool | What / how to invoke |
|---|---|
| `census_window_literals.py` | The writer census: searches a set of decoded payloads (the campaign ran it over ~74.7 MB of LZMA-decompressed CAP payloads from both bases, plus embedded inner payloads) for literal banked-window addresses (`0x090467ac/67b0/77ac/77b0`) and the `0xFFFE0000` token, LE and BE; writes a JSON report with per-file offsets. Zero literal writers found is what forced the conclusion "the clamp writer is NBIO on-chip microcode" (M18/M19, docs/10). `census_window_literals.py <report.json> <file\|dir>...` (dirs glob `*.bin`) |
| `l32r_scan.py` | Xtensa L32R cross-reference: for a raw load image and a hypothesized load base, reports every code offset whose `L32R` literal resolves to the requested slot VAs — needed because SMU tables are reached through pooled literals, so plain value greps miss them (docs/09). `l32r_scan.py <image.bin> <base_hex> <slot_hex>...` |

### tools/probes/ — read-only SMN probe skeletons (docs/08)

| File | What |
|---|---|
| `smn_dxe_probe.c` | Self-contained DXE driver skeleton: walks an address table through the CF8/CFC SMN pair on the AMD host bridge (config offsets 0x60 index latch / 0x64 data window), classifies each dword, runs the M1–M4-style result matrix, exports a **volatile** BootServices\|RuntimeServices log variable + a separate 16-byte **NV** boot counter. Ships with a 10-address representative table (mailbox controls, the QCB ternary, NBIO witnesses, a negative); the campaign's full maps (e.g. the 148-address NBIO map) are described in docs/08 — the probe does not depend on table size. |
| `pei_probe.c` | PEI-side skeleton (T46): `SIDT`/CR0/CPUID only, a sane-pointer guard, a dump of the `[IDTR.base−4]` control block + vtable + a 1 KiB window with skip masks, written unconditionally to a HOB (create-or-lookup) so the observation exists even when the module is never dispatched. |

Doctrine baked into both skeletons (every rule was a measured requirement —
docs/08): **zero data writes** (the only writes are the CF8/latch index
cycle and the log variable; `WritesAttempted` must export 0), **save/restore**
of the previous CF8 and latch contents, **echo bits** on every read (CF8
re-read + latch content), a fixed 5-IN + 6-OUT port budget per read
(anti-hang), and **live controls** in every table — all-FF *controls* mean
your probe is broken, while all-FF targets with live controls are a real
negative (docs/10, M22). Syntax-check without EDK2:
`gcc -fsyntax-only -fshort-wchar tools/probes/smn_dxe_probe.c` (the file's
`#else` branch supplies the minimal UEFI stand-ins); inside EDK2 define
`USE_EDK2_HEADERS`. Read the volatile log after boot (before reboot!):
`hexdump /sys/firmware/efi/efivars/BiosmodProbeLog-<your-guid>` — efivars
are world-readable (distro `efivar`/`efitools` packages; no firmware
tooling needed to *read*).

### tools/qemu/ — offline replay bench (the pre-flash gate)

Test the decision logic of a new probe against a **real archived boot**
(the A2 capture: 1168 SMN readings taken at DXE entry on the 5800X3D board)
with zero risk and no board. This harness was a standing gate: probe CAPs
passed here before staging (docs/02 doctrine).

| File | What |
|---|---|
| `replay_run.py` | The runner: compiles `replay_guest.c` + your probe C against the capture on a temp FAT disk, boots OVMF under QEMU/TCG, and turns the debug-console transcript into a verdict. `EDK2_INCLUDE=~/edk2/MdePkg/Include python3 -I replay_run.py --capture A2.BIN 0x03810054 …` or `--probe probe_example.c`. Env: `EDK2_INCLUDE` (required, an EDK2 checkout), `OVMF_DIR` (default `/usr/share/edk2/ovmf`). Needs `clang` (COFF), `lld-link`, `qemu-system-x86_64`. **Exit codes: 0 PASS, 1 FAIL, 2 INCONCLUSIVE (probe consulted an address outside the capture, or made no consults), 3 infrastructure.** A printed `MEASURED` only proves that address was recorded in that boot phase — one value alone never proves meaning, writability, or reachability in another phase. |
| `replay_guest.c` | The QEMU guest app: loads `A2.BIN`, validates attrs/magic/version/`ReadsOk`/`WritesAttempted==0`, runs your `probe_check()`, stops the VM with the verdict code (PASS / FAIL / INCONCLUSIVE markers on the debug console). |
| `bench_app.c` | The "bancada" USB-stick application: reads `C6HLAB/LISTA.TXT` (first line `LIVE` or `REPLAY`, then 1..64 aligned NBIO-block addresses) and answers in `C6HLAB/LOGnnn.TXT`, never overwriting an existing log. `LIVE` refuses cleanly on non-AMD (`SKIP unsupported-platform`). |
| `bench_ovmf.py` | The OVMF battery around `bench_app.c`: builds a 32 MB FAT disk (needs `mtools`), runs replay/live/invalid-list/missing-list/truncated-capture/subset cases in parallel, asserts log lines and that an old `LOG000.TXT` is untouched. `python3 -I bench_ovmf.py --efi BOOTX64.EFI --list list.txt --capture A2.BIN` |
| `capture_format.h` | The capture wire, fully documented so readers can regenerate a capture with `tools/probes/`: `u32 attributes(=6)` + 4 800-byte `SMN_LOG` struct (32-word header: magic `'SM12'`, version 2, phase, reads planned/ok, `WritesAttempted`, echo counters, zones; then `Raw[1168]` dwords at word 32) + padding. Block layout: page 1024 dwords @`0x03b10000`, NBIO 64 @`0x03810000`, family 5×16 @`0x0380/0382/0383/0384/03850000`. A dword's offset in the file is `4 + 128 + 4*i`. |
| `probe_api.h`, `nbio.h`, `uefi_shim.h`, `probe_example.c` | `read_captured()`/`probe_check()` contract; the PciIo NBIO read helper (same save/restore/echo discipline); minimal UEFI stand-ins so the C files pass `gcc -fsyntax-only` outside EDK2; an example probe (`read_captured(0x03810054) == 1`). |

### tools/build/ — the CAP pipeline, reference example

| Tool | What |
|---|---|
| `fvmain_bytepatch.py` | The A36 "PBO-CO-native" build, kept as the reference example of the patch pipeline: patch in place inside the LZMA envelope of the official 8902 CAP (NOP two capability-flag stores across three modules; rewrite the boost formula's base/ceiling constants in one module), re-compress deterministically, emit a JSON receipt. |

## Reference build — the byte-identical A36 reproduction

From the **official** ASUS 8902 image (supply your own; verify first):

```
sha256sum official8902.CAP
# 04ddae2d0650353ec7bafa50a281528791a74694960f2104ac9d53657b0b6bba

python3 -I tools/build/fvmain_bytepatch.py official8902.CAP out.CAP
```

Expect `out.CAP` at 16 779 264 bytes with

```
f87ba18d677e6ae79c8a3a5118be87fcebba97f5958690718521f89efbd87a22
```

— byte-identical to the A36 CAP the campaign built and flashed (build A36,
docs/11). The script refuses to run if the input SHA-256 does not match the
official base. This is simultaneously the pipeline example and the tooling
suite's strongest end-to-end test: if the output SHA matches, the whole
envelope/patch/re-compress chain is bit-exact. (src:
biosmod_8902_co/construcoes/93-a36-pbo-co-nativo-safe/out/patch.json,
tools/build/fvmain_bytepatch.py)

## Method gotchas and errata (learned the expensive way)

* **The LZMA envelope offset.** In this firmware family the big volume
  payloads are GUID-defined (LZMA) sections; the LZMA ALONE stream starts at
  **GUID + 20** — 5 property bytes + u64 uncompressed size + stream —
  **regardless** of the declared `DataOffset` field. `fv_decompress.py`
  decodes from there (as the campaign's `build.py` did); the envelope found
  in the official 8902 sits at `0xa9ff24` and yields a 16 162 832-byte
  FVMAIN. (src: biosmod_8902_co/construcoes/*/build.py; BUILD-NOTES)
* **The AMI 16-byte prefix.** The decompressed main FV starts with a
  16-byte AMI `ZeroVector` **before** the volume header: the `'_FVH'`
  signature lands at file offset `0x38`. Strip the 16 and use the header
  recipe: `FvLength` at base+32, `ExtHeaderOffset` at base+52, `HeaderSize`
  at base+48, FFS files 8-byte-aligned, sections 4-byte-aligned
  (`fv_ls.py`/`modpe.py` implement exactly this).
* **Raw PE32 section type is 0x10** (AMI convention), not EDK2's 0x01 —
  code written against the EDK2 spec silently finds "no PE" on these images.
  UI name is section type 0x15 (UTF-16LE). (docs/03)
* **A real upstream bug: `align(n, 4)`.** The campaign's original
  `mod_unpack` mis-aligned FFS file walking with `align(n,4)` instead of
  8-byte file alignment; fixed in `tools/firmware/ffs_unpack.py`. If your
  walk "loses" files or lands mid-header, suspect alignment first.
* **`python3 -I` removes the script's own directory from `sys.path`.** We
  standardize on `-I` (a standing hygiene rule when analyzing extracted,
  untrusted trees — a planted `json.py` in the data directory otherwise
  shadows the stdlib), but that also drops the script dir, so same-directory
  imports need `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))`
  (`dump_ocmr.py` does this). Prefer argv + stdlib only.
* **Translation/AST errata caught in review** (kept as method warnings): a
  `c += 1` dedented out of its while-loop while translating the EFI 1.1
  decompressor (an infinite-`dsize` bug — caught only by byte-exact
  re-run against the campaign's reference output); and, upstream in the
  campaign, big-endian byte scans that produced a false "zero keys in the
  SMU" verdict. Both are why every tool here was AST-diffed against its
  original and re-run on synthetic inputs before shipping.
* **Probe port discipline.** NEVER issue `OUT` to `0xcfc` while `CF8` points
  at the **data** window (`0x80000064`) — the data window is IN-only; the
  only legal `OUT 0xcfc` is to the **index latch** window. The shipped
  skeletons make the illegal path structurally impossible (no write
  function exists) and export the `WritesAttempted==0` sentinel as proof.
  (docs/08)
* **Capstone:** keep `skipdata = True` on linear passes over PE bodies —
  data islands (jump tables, embedded blobs) otherwise abort the disassembly
  early and hide the instructions after them.
* **Volatile vs NV variables:** kilobytes of per-boot log in a
  NON_VOLATILE variable punish the SPI chip; keep the log `BS|RT` volatile
  and the NV footprint to a 16-byte counter — and read volatile logs **before
  rebooting**, because they do not survive it.

## Tools NOT shipped, and why

| Tool | Why | How we invoked it |
|---|---|---|
| **Ghidra (headless)** | Third-party (public, NSA); too heavy to vendor. | `analyzeHeadless <proj> <name> -import <blob.bin> -scriptPath <dir> -postScript Dump.java`, scripts setting the memory base first (Xtensa SMU bodies load at the directory VA, e.g. the e07 SMU) and dumping function bodies/strings to text. The campaign's example scripts (`DumpSmu.java`, `DumpFns.java`, `DumpDriver.java`) live in the research tree, not here. |
| **PSPTool** | Third-party public project. | Used offline for directory/certification views (`-t` prints the PSP directory tree with the certification chain) — useful to double-check which PSP directory is active and which SMU version each carries. |
| **efivar / efitools / `efibootmgr`** | Distro packages. | Only ever *reading*: `/sys/firmware/efi/efivars/` is world-readable — that is how the campaign read probe logs back, no sudo, no writes. |
| **CHIPSEC** | Excluded by policy: it operates live on registers — the campaign's rule is *no live writes ever*; reads came from our own read-only probe CAPs instead. |
| **capstone** | Install it: `pip install capstone` (used by `disgrep.py`). |
| **clang/lld, qemu-system-x86_64, OVMF (edk2), mtools** | Distro/toolchain packages for `tools/qemu/` (see each script's docstring for the exact flags used). |
| **`chain_re.py`, `dispatch_map.py`, `executor_re.py` (analises/11)** | Campaign-specific dispatch walks; the reusable core is the function-map method, shipped as `thumb_funcmap.py`, and the attribution pass as `psp_active_dir.py`. |
| **`bancada-uefi/build.sh`, `amostras/`, `resultados/`, board captures** | Build script hardcodes one EDK2 workspace; samples/results/captures are board data (firmware-adjacent measurements) — the wire format is documented in `capture_format.h` so you can regenerate your own with `tools/probes/`. |
| **`literal_census.json`** | A research *result* file (offsets into proprietary payloads), not a tool; its method is shipped and its conclusions are in docs/10. |

## Supply your own firmware

This repo contains **no** CAP/ROM files, extracted modules, SMU blobs, or
board captures — proprietary content stays out by design, and publishing AMD
signed binaries is prohibited anyway. Every tool takes image paths from
`argv`. Fetch the BIOS for the ASUS ROG Crosshair VI Hero from the ASUS
support page; check `sha256sum` against `04ddae2d0650353ec7bafa50a281528791a74694960f2104ac9d53657b0b6bba`
for the official 8902 before feeding it to `fvmain_bytepatch.py`. The SPI
dumps used by `nvs_decode.py` and the SMN captures used by `tools/qemu/` can
only come from your own board (tools/probes + reading the EFI variable).

## Sources

- `tools/setup/*.py`, `tools/firmware/*.py`, `tools/build/fvmain_bytepatch.py`, `tools/x86re/*`, `tools/psp/*`, `tools/scans/*`, `tools/probes/*`, `tools/qemu/*` — every shipped tool, self-documented (this file maps them).
- `biosmod_8902_co/analises/17-menu-pbo-co/scripts/{disgrep.py,modpe.py,callargs.py}` — originals of the x86 RE trio.
- `biosmod_8902_co/analises/06-a23/scripts/dis6.py` — original Thumb disassembler.
- `biosmod_8902_co/analises/16-diretorio-psp-ativo/scripts/gen4dis_driver_ativo.py` — original active-directory attribution pass.
- `biosmod_8902_co/analises/11-cadeia-psp-executor/scripts/{funcmap.py,nvs_decode.py}` — originals of the function-map method and the NVS decoder.
- `biosmod_8902_co/analises/12-smu-e07-restore/scripts/{l32r_scan.py,DumpSmu.java}` — Xtensa L32R xref scanner and a Ghidra headless dump script (not shipped, recipe above).
- `biosmod_8902_co/analises/14-writer-census/census_window_literals.py` — original writer census (74 MB, zero hits; docs/10 M18/M19).
- `biosmod_8902_co/construcoes/{47-smu101-sonda,36-smnmap-a2}/src/` — board-proven CF8/CFC read primitives the DXE skeleton distills.
- `biosmod_8902_co/construcoes/46-peiprobe/src/{pei_probe.c,peip_engine.h}` — original PEI probe.
- `biosmod_8902_co/bancada-uefi/{test_vm.py,sonda.c,nbio.h}` and `bancada-uefi/replay/{rodar.py,guest.c,sonda.h,exemplo.c}` — originals of the OVMF bench and the replay runner.
- `biosmod_8902_co/construcoes/93-a36-pbo-co-nativo-safe/out/patch.json` — A36 base/result SHAs and 16 779 264-byte size.
