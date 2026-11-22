# 09 — Reverse-engineering the PSP side

## Summary

This document records **how** we reverse-engineered the AMD-signed PSP side of
the 8902 image: the toolchain and per-blob workflow, the directory-attribution
erratum that mislabeled two PSP firmware sets for two weeks (and what it
cost), how mailbox requests reach a driver handler on the PSP-OS side and a
queue handler on the SMU side, what lives inside the **active** PSP driver
(0.14.0.43) — the `ctx[3]` whitelist gate and the clamp function `0x3230` — the
`0x0904_xxxx` commit mechanism found by diffing the official 7306×7403 pair,
the two writer-hunt censuses (T48, T49) that exhausted the flash as a source of
the `0x03810054` proxy writer, and the bc250-class queue-overflow audit of our
SMU (T54) that refuted that weakness class on our firmware. The firmware
*anatomy* (offsets, containers, `$PS1` layout) is doc
[03](03-firmware-anatomy.md); the boot trace that brackets the clamp in
request 30 is doc [04](04-boot-timeline.md); the clamp verdict chain is doc
[05](05-gen4-the-clamp.md); the closed doors are doc
[10](10-negative-results.md). Everything here is static RE: signed blobs were
read, never edited; no live writes.

## 1. Toolchain and method

**Ghidra 12.1.4 headless** was the decompiler of record
(`~/tools/biosrev/ghidra/ghidra_12.1.4_PUBLIC/support/analyzeHeadless`), with a
fixed architecture map: `ARM:LE:32:v8T` for PSP-OS/BL/drivers (Thumb code),
`Xtensa:LE:32:default` for the SMU blobs (imported with `BinaryLoader`, base 0
— *file == VA*), `x86:LE:32:default` for the x86 modules
`(src: biosmod_8902_co/HANDOFF-FINAL-20261122.md §6)`. Modelled Java export
scripts (`DumpFns.java`, `DisasmFn.java`, `DumpContaining.java`,
`DumpDriver.java`/`DumpDriver2.java`, `DumpBlock.java`, `Probe54.java`) ran
against per-analysis Ghidra projects
`(src: biosmod_8902_co/analises/11-cadeia-psp-executor/scripts/; analises/12-smu-e07-restore/scripts/; construcoes/54-smu-fila/scripts/)`.
Xtensa encodings had to be validated by hand first: `L32R =
align4(pc+3)+(imm−0x10000)*4`, `callN (op0=0101, n bits[5:4],
target=(pc&~3)+sext18(off)*4+4)`, and the `l8ui→movi` 3-byte patch form
(byte1=0xA0, byte2=0x00) — the byte order was validated inside Ghidra itself
`(src: biosmod_8902_co/HANDOFF-FINAL-20261122.md §6)`.

**capstone** (host-side Python) was the surgical tool for targeted questions:
the analises/11 scripts are the canonical pattern — `chain_re.py`
(challenge-chain functions), `executor_re.py` (executor literals + a raw
halfword scan that decodes Thumb 32-bit `BL` immediates to find *who calls* a
function), `dispatch_map.py` (whole-body `tbb`/`tbh` scan + a census of every
`svc` site), `funcmap.py` (function map via prologue scan: `push {…,lr}` as
`0xB5xx`/`0xE92D`+lr) and `nvs_decode.py` (decompress/list varstore slices from
SPI dumps to compare persistent state across flashes)
`(src: biosmod_8902_co/analises/11-cadeia-psp-executor/scripts/{chain_re,executor_re,dispatch_map,funcmap,nvs_decode}.py)`.
Disassembly always resolved PC-relative `ldr` literals and `bl`/`b` targets
inline, so offset claims come with their constants
`(src: biosmod_8902_co/analises/16-diretorio-psp-ativo/scripts/gen4dis_driver_ativo.py)`.

**Our own extractors**: the VZL1 decoder (166/166 PE validation, doc 03), the
LZMA-alone envelope reader, and for the PSP blobs the direct-CAP body reads —
driver bodies at CAP `0x895094`/`0x713094`, SMU `e03`/`e07` as **zlib at
packed+0x100** giving exactly `0x40000` decompressed
`(src: biosmod_8902_co/HANDOFF-FINAL-20261122.md §6; analises/12-smu-e07-restore/README.md)`.
PSPTool (public tool, installed offline in a venv at `~/tools/psptool`) gave
the certified per-directory blob tree for the censuses (T48)
`(src: biosmod_8902_co/trabalhos/48-a3-bl-escritor-do-clamp.md)`.

**Static-only discipline**: every task forbade board, flash, live writes and
network; signed AMD content was read/extracted only; Python always ran
`python3 -I` with absolute paths; Ghidra projects were opened only on copies
inside the worker's own tree (never the predecessor `.rep`)
`(src: biosmod_8902_co/trabalhos/48-a3-bl-escritor-do-clamp.md; trabalhos/51-emul-commit-0904-direcao.md; trabalhos/54-fraqueza-de-fila-do-smu.md)`.
Disassembly listings went to files, summaries to the conversation
(`analises/12-smu-e07-restore/out/` holds the e07 text dumps; per-module
disassembly-as-text follows the same house pattern, e.g.
`analises/17-menu-pbo-co/out/pei_aod_c8f6d366.dis.txt`)
`(src: biosmod_8902_co/trabalhos/12-probe-estaatico-smu.md; analises/12-smu-e07-restore/README.md)`.

**Cross-verification rule**: the coordinator re-checked byte-level claims with
his own instruments before they entered the master log — independently
re-hashing the BL blobs in T48 (`5b129195f852…`)
`(src: biosmod_8902_co/RASTRO.md M18)`, re-decoding 38/38 LZMA payloads by sha
in the T49 check, re-running a 67 325 391 B literal scan with zero hits
`(src: biosmod_8902_co/RASTRO.md M19)`, an independent 1465-function
scaled-store scan in T54 (§7), and an LE-scan of the `0x0904` doorbell keys
after correcting his own endian mistake in T51 (§5)
`(src: biosmod_8902_co/RASTRO.md M25, §A line 51)`.

## 2. The PSP OS directory on this board — the attribution erratum

The `$PSP` directory table, per-entry layout and the `$PS1` container map are
in doc [03](03-firmware-anatomy.md) §PSP-directory; the self-anchor detail that
matters for RE is that each signed container records `sha256(body)` at
`PS1+0xc0`, itself covered by the AMD chain rooted on-chip (`6C9E` PSP ROM → BL
→ TOS/ABL0/HIC/SMU) — editing one body byte breaks the anchor, fixing the
anchor breaks the signature, and a module with a zeroed anchor measured **F9 +
recovery** in an early test `(src: biosmod_8902_co/RASTRO.md §P; docs/03-firmware-anatomy.md §PSP directory)`.
The campaign later proved the check is real on the *loaded* driver: a 2-byte
data edit into it measured non-POST (flash 37, doc 05 §5)
`(src: biosmod_8902_co/RASTRO.md §FFF)`.

**The erratum.** For most of the campaign we analysed two PSP directory sets
under reversed labels: "dir1 ATIVO Zen3" (driver 0.11.0.87, SMU bodies e03/e07
at CAP `0x82be00`/`0x86d500`) and "dir6 INERTE Zen2" (driver 0.14.0.43 at CAP
`0x469f00`). On 22/11 we matched the **load path**, not content similarity: the
kernel line `ryzen_smu: SMU v56.76.0` appears in all 11 logged boots; reading
each SMU header at `+0x60` against the CAP gives directory `0xBC0B0500`
sub1 @`0x421400` = **56.76.0** (the loaded one), while `0xBC0C0140`
("dir1"/e03) = 64.74.0 (**Cezanne**), `0xBC0C0000` = 55.95.0 (Renoir) and
`0xBC0B0500` sub0 = 46.73.0 (Matisse)
`(src: biosmod_8902_co/RASTRO.md §DDD; analises/16-diretorio-psp-ativo/scripts/gen4dis_driver_ativo.py)`.
So the Cezanne/Renoir content — e03/e07 and every 0.11.0.87 driver edit (the
A21/A23/A29 PSP patches) — **never loads on this machine**; "boot sane, zero
effect" was the expected outcome, and the "inert" 0.14.0.43 is the active
driver `(src: biosmod_8902_co/RASTRO.md §DDD)`. T48/T50/T51 were written with
the wrong labels; §DDD and doc [10](10-negative-results.md) track which of
their claims survive the correction (the byte-evidence survives; directory
attribution in their prose does not) `(src: biosmod_8902_co/RASTRO.md §DDD;
docs/05-gen4-the-clamp.md §3.3)`.

## 3. How a request reaches a handler

Three dispatch surfaces had to be mapped to join the x86 trace to the code:

| surface | what it is | key facts |
|---|---|---|
| x86 → SMU mailbox | native protocol, hardware-captured as **38 requests** | the clamp fires inside request 30 (`0x308`); request 29 returns state 8 = **VETTING** — full table in doc [04](04-boot-timeline.md) §request-timeline `(src: biosmod_v2/diagnostics/8902-boot-trace-v2.6-full-smu-20261116/hardware-capture-20261116/REPORT.md)` |
| SMU-side dispatcher (Xtensa, blob `f4cb81d9…`) | doorbell/port protocol | `FUN_00001134` reads the port id, checks `if (*(ushort*)(0x7b20+fila*2) <= id) → 0xfe` **before indexing**, then calls `tabela[fila] + id*8` directly (meta bit7) or via wrapper `FUN_000026cc` — synchronous, no message queue (§7) `(src: biosmod_8902_co/construcoes/54-smu-fila/out/VEREDITO.md)`. In the e03 blob the dispatch tables are **image data**: 14 queues, 289 handlers, dumped to `analises/13-e03-backend-applier/out/e03_dispatch_tables.txt` `(src: biosmod_8902_co/HANDOFF-FINAL-20261122.md §4.3)` |
| PSP-OS driver dispatcher (Thumb) | switch over the first message word | dispatcher `0x1da8` (the driver export): mailbox command `0x1039` → challenge `0x4d28`, `0x103a` → executor `0x4c90`; `dispatch_map.py` found the surface by a whole-body `tbb`/`tbh` scan + `svc` census `(src: biosmod_8902_co/analises/11-cadeia-psp-executor/README.md)`. **Erratum kept: `0x1039/0x103a` are mailbox command IDs, not service IDs** `(src: biosmod_8902_co/HANDOFF-FINAL-20261122.md §4.1)` |

The PSP-OS kernel exposes its MMIO primitives to drivers through `svc` numbers
that our disassembly treated as the ABI: `svc #0x7c` = write
`(addr, value, size)`, `svc #0x7b` = read `(addr, buf, size)`, `svc #0x6c` also
used; the kernel maps a 1 MiB block (`addr>>20`) into a window-slot table
(`>>20` / `&0xFFFFF` / `slot<<20`) — the translation routine was confirmed in
the TOS body at `0x2f98` `(src: biosmod_8902_co/analises/16-diretorio-psp-ativo/out/resultado-a28.txt;
RASTRO.md §A line 51)`.

Where the requests of the x86 timeline live inside signed code: request 30
corresponds to SMU mailbox command `0x1e` — in the active SMU body its
dispatcher handler is `0x26f90`, which writes a **RAM context field** `0xb350`,
not NBIO (that negative is M17, doc 10) `(src: biosmod_8902_co/RASTRO.md §A line 48,
M17)`. The legacy PSP-side pair (`0x1039` challenge → doorbell token
`0xFFFE0000`, platform id `0x43b9` = X370 served by the SMU; `0x103a` executor
→ writes to `0x1118_06xx`) was fully mapped from the 0.11.0.87 driver — but
§DDD proved that driver is Cezanne content, so the per-request PSP row of the
doc-04 timeline keeps both readings with that caveat
`(src: biosmod_8902_co/analises/11-cadeia-psp-executor/README.md; RASTRO.md §RR, §DDD;
docs/04-boot-timeline.md §4 errata)`. The driver versions that matter here:
**0.14.0.43 active** (dir `0xBC0B0500`; blob `$PS1` at CAP `0x469f00`, magic
at `blob+0x10`, version `00140043`, signed size `0x1a590` B + a `0x100` B
signature region; PSPTool entry e14 `DRIVER_ENTRIES 0.28 0.14.0.43` = 108 176 B,
sha16 `3e2c983c`) vs **0.11.0.87 never loaded** (Cezanne dir)
`(src: biosmod_8902_co/analises/16-diretorio-psp-ativo/scripts/gen4dis_driver_ativo.py;
trabalhos/51-emul-commit-0904-direcao.md pins; RASTRO.md §DDD)`.

## 4. Inside the active driver 0.14.0.43: the gate and the clamp

The full disassembly commentary of the clamp function `0x3230`, its caller and
the whitelist is `analises/16-diretorio-psp-ativo/out/resultado-a28.txt`
(script `gen4dis_driver_ativo.py`, one-shot read-only, takes any CAP path)
`(src: biosmod_8902_co/analises/16-diretorio-psp-ativo/out/resultado-a28.txt)`.
In prose: function `0x3230` performs three write groups via `svc 0x7c/0x7b` —
(1) strobes 8 indices `0xFFF0001C..0xFFF00023` through command port
`0x0904_901C` with byte strobe/ack at `0x0904_9020` (and the mirror
`D01C/D020`), semantics unidentified ("possible lock"); (2) writes the strap
doorbell token `0xFFFE0084` to `0x0904_97AC`/`0x0904_D7AC`, reads the data
word at `+4` (`97B0/D7B0`) and, **if it reads 0**, writes `1`; (3) RMW-ORs bit
21 into `0x0904_9914`/`0x0904_D914`. By the published PCIe-RSMU strap interface
(illumos/Oxide `milan/pcie_rsmu.h`, `STRAP_ADDR 0x7ac`/`DATA 0x7b0`, upper word
`0xFFFE0000` — public knowledge) strap index `0x84` is **`GEN4_DIS`**
`(src: biosmod_8902_co/RASTRO.md §DDD; docs/05-gen4-the-clamp.md §3.2)`.

The gate: the single caller of `0x3230` is `0xaa62` (the tail branch of the
function starting `0xa9dc`), requiring `ctx[3] != 0` with context `0xe16ac0`;
`ctx` fields come from the **24 × 12-byte whitelist table at CAP `0x480a70`**
(14 entries selector 7, 10 entries selector 2): entry bytes copy `ctx[0]/[1]/[3]
:= entry[5]/[6]/[7]` at `0xab46..0xab54`, and lookup `0xb6f8` matches the
chipset devid plus a selector read from `[0xe86e78+0x510]`, looping exactly 24
rows `(src: biosmod_8902_co/analises/16-diretorio-psp-ativo/out/verif113-ctx3.txt;
out/resultado-a28.txt)`. Flag `b3` (= entry byte 7, bit 24) is set for devids
`43b9/43ba/43bb/43bc/43d0/43d3/43d5/43d8/43ec` and clear for
`43d1/43d2/43ed/43ee/43ef` — matching the product policy (B550 free; 300/400/
A520 without Gen4); X370 (`0x43b9`) is entries 0 and 23 (`01 01 00 01`)
`(src: biosmod_8902_co/RASTRO.md §DDD; analises/16-diretorio-psp-ativo/out/resultado-a28.txt)`.

One unconditional SMU-side handler must be named here because it closed the
front-A "open the gate by command" route on emitter grounds: handler `0x1dee4`
(SMU body, mailbox command `0x0a`) is 7 instructions and sets byte
`[0x7b4c+0x14] ← 1` **unconditionally** (T34 elo-3) — but no host-reachable
emitter exists for it (M1/M3/M16/M22/M23 chain, docs 05 §6 / 10)
`(src: biosmod_8902_co/RASTRO.md §A line 34; §C A2)`.

## 5. The commit mechanism: the 7306×7403 diff (T50) and its direction (T51)

The official pair 7306 (`f87a7fcf…`, last BIOS of this board accepting Gen4
without a hack, owner-stated) × 7403 (`3e35c6f1…`, already refuses) is the
campaign's only natural differential. The diff put the lever in **PSP-OS
content**: 7403 gains a whitelist gate (chipset devid FCH → `ctx+3`) consumed at
the end of the auth flow with a tail-call to a **COMMIT** that writes the
`0x0904_90xx/D0xx` family via `svc 0x7c`; in the 7306 CAP the pool immediates
`0x0904901c/d01c/97ac/d7ac` are zero occurrences and no consumer or tail exists;
the `svc 0x7c` count goes 53→74 with a contiguous tail cluster
`(src: biosmod_8902_co/RASTRO.md §A line 50; trabalhos/50-diff-7306-7403-alavanca-oficial.md)`.
The SMUs of the pair are **byte-identical** (sha `ed15b19b…`, 108 608 B,
7306@`0x2aa100` == 7403@`0x2b8d00`) — the lever is not the SMU; and the two
x86 "validators" that a V2-era lead suspected were exonerated (their changed
spans are a uniform −0x40 relink) `(src: biosmod_8902_co/RASTRO.md §A line 50)`.
On the 8902 the same mechanism was first seen only in the blob later revealed
as the **active** driver (see §2; at the time T50 concluded "only the inert
dir6", M20) `(src: biosmod_8902_co/RASTRO.md M20, §DDD)`. The direction
(enable-list vs clamp) was recorded as **not proven** by the worker's own
caveat `(src: biosmod_8902_co/RASTRO.md §A line 50; docs/05-gen4-the-clamp.md §1)`.

T51 resolved target + direction for the Zen2-shaped COMMIT: emulating/shim-tracing
the TAIL (`0x3230..0x3366` + literal pool at `0x3364..0x3390`) yields the full
write table — doorbell `0x0904_97AC/D7AC := 0xFFFE0084` + status byte `97B0/
D7B0`; command port `901C/D01C` ← `0xFFF0_0000` then the `0xFFF0_001C..23`
stream, strobe byte `9020/D020`; RMW OR set bit21 at `9914/D914` (the
`orr r1,r0,#0x200000` at `0xe03351`); condition: runs only when `ctx+3 ≠ 0`
(§4's whitelist) `(src: biosmod_8902_co/construcoes/51-emul-commit-0904/out/A_tabela_alvos_tail.txt)`.
The **identity of page `0x0904`** was then proven by three independent content
lines: the four doorbell keys exist as constants in the same-generation SMU
body at `0x1437c` (`97ac | fffe0000 | 97b0 | d7ac | d7b0`) and in the `e07`
blob at `0x185f8` with banks renumbered 6/7 (`67ac | fffe0000 | 67b0 | 77ac |
77b0`); the `SEC_GASKET` and `TOS_SECURITY_POLICY` blobs carry register
protection lists naming banks 6/7/F (49 and 15 hits, checked); and the kernel
translation (`>>20` block → window slot) was confirmed at TOS `0x2f98`
`(src: biosmod_8902_co/construcoes/51-emul-commit-0904/out/C_prova_smu_doorbell.txt;
RASTRO.md §A line 51)`. Conclusion: `0x0904_xxxx` is **PSP-peripheral MMIO
governed by TOS security policy — not NBIO, not the QCB, and it never touches
the `0x03810054` proxy** `(src: biosmod_8902_co/construcoes/51-emul-commit-0904/out/C_prova_smu_doorbell.txt;
RASTRO.md §A line 51)`. The board-side confirmation that x86 cannot even reach
this page came from the PG0904 read probe (flash 16, PÁGINA_FORA with live
controls in the same boot) — probe campaign detail in doc
[08](08-smn-probes.md) `(src: biosmod_8902_co/RASTRO.md §A line 52, M22)`.
Note the label caveat: T51 recorded the `e07` bank-6/7 table as "the ACTIVE
Zen3 SMU"; §DDD later showed `e07` (dir1, 64.74.0) belongs to the never-loaded
Cezanne set — the byte evidence stands, the attribution in that prose does not
(§2).

**Errata we kept as method lessons** (from this task pair): (a) the
coordinator's own first `0904xxxx` scans were done **big-endian**, producing a
false "zero doorbell keys in the SMU"; the LE scan (`ac 67 04 09`) finds them
exactly — recorded against him, M21 `(src: biosmod_8902_co/RASTRO.md §A line 51)`.
(b) In the active-form scan of the 19-blob set, three aligned dwords
`0x0904_F100/107/108` in e14 looked like a pool but are **THUMB instruction
halves read as data** (zero PC-relative references in the whole file;
neighbouring dwords disassemble as continuous code) — the reverse of the old
"magic matches in data" lesson `(src: biosmod_8902_co/construcoes/51-emul-commit-0904/out/C_prova_smu_doorbell.txt §4,
out/B_q2_forma_19blobs.txt)`. (c) Q2 of T51 ("does the running PSP-OS emit the
channel?") answered negative on the blob then believed active (0.11.0.87 e14:
no table/pool/consumer; `svc` census 7b=56/7c=130/6c=24 shows the *form* but
not the mechanism) — after §DDD this question targets a never-loaded blob, and
the mechanism's emitter question moved to the 0.14.0.43 function `0x3230`
itself, which is in-flash and gate-controlled (§4)
`(src: biosmod_8902_co/construcoes/51-emul-commit-0904/out/B_q2_forma_19blobs.txt;
RASTRO.md M21, §DDD)`.

## 6. The writer-hunt censuses (T48, T49)

Two questions: does the running PSP stack write the policy proxy
`0x03810054`, and does anything in the flash? **T48** extracted every PSP blob
from both bases with PSPTool offline and ran a dword census: **292 blobs, zero
exact hits** for `0x03810054` (the census file shows `exact=[]` on every line;
the `0x038xxxxx` family hits cluster in the BIOS blob and known readers, e.g.
`fam81n=8` in `e04_BIOS`) `(src: biosmod_8902_co/construcoes/48-a3-bl/out/census_global.txt)`.
The coordinator's independent scan: 291 files / 20.1 MB, zero hits; the BL is
**byte-identical between RC1 and clean** (raw sha `5b129195f852…`), so no PSP
blob can be the differential writer (dir1/dir3 identical RC1×clean)
`(src: biosmod_8902_co/RASTRO.md M18)`. A homologous NBIF-store mechanism was
named in **inert Zen1/Zen2 BLs only** (d6 BL `9979cde3…`: mailbox cmd `0x5a`
handler at `0x6224`, pool `0x03810058/0x030109a0/0x03010058`) — absent from the
board's generation; the one unreadable blob (HIC at `0x881200/0x670`,
encrypted) is identical across both bases `(src: biosmod_8902_co/RASTRO.md §A line 48, M18)`.
⇒ **M18** (doc 10).

**T49** extended the census to *all expanded flash content* of both bases:
after measuring the real container form (`GUID + u16(0x18) + u16(0x01) +
props@+4 + u64 + LZMA1` — after two wrong header assumptions, an error kept on
record) it decoded 38 LZMA payloads per base (18 CAP + 20 nested): AGESA
16.1 MiB / 3.29 M instructions, inner FV with 164 VZL1 modules (955 094
instructions), nested layers swept (`inner2` 253 zlib + 1 VZL1; `inner4` 39
LZMA) — **~48.7 MB unique / ~5.28 M instructions** searched for the literal
`0x03810054`, the witness `0x001A43B9`, the `0x038xxxxx` family, and computed
synthesis forms (movw/movt immediates, `[reg+disp ∈ {0x54,0x58,0x5c}]`, CF8/CFC
SMN cycles): **zero hits on both bases**; the only RC1×clean-different cluster
is our own V2 probe container (`3e3b6dc0`), i.e. the 181 official modules are
identical; APCB identical, NBIFS absent
`(src: biosmod_8902_co/RASTRO.md §A line 49, M19; biosmod_8902_co/trabalhos/49-lzma-agesa-censo-clamp.md)`.
The coordinator re-decoded 38/38 payloads (matching shas) and scanned 67 325
391 B himself → 0 hits `(src: biosmod_8902_co/RASTRO.md M19)`.

**Net conclusion of the censuses** (as recorded, M19 + M18): the writer of the
NBIO policy proxy `0x03810054` never exists as software in this flash — only
NBIO on-chip microcode / hardware logic, unreadable by every offline path we
know. Reconciliation kept explicit so this doc does not contradict doc 05: the
censuses targeted the proxy literal; §DDD later named a flash-resident clamp
**decision** in the active driver (§4) whose stores go to the `0x0904` strap
page, a different register family — the two statements address different
targets, and the final board evidence (A34 non-POST / A35 no-effect) is in doc
[05](05-gen4-the-clamp.md) §5 `(src: biosmod_8902_co/RASTRO.md §DDD, M19;
docs/05-gen4-the-clamp.md §3.3)`.

## 7. The bc250-class queue-overflow audit (T54) — weakness refuted

The owner pointed at the public research `bc250-vcn-research` /
`bc250-smu-unlock` (a demonstrated arbitrary-write in another AMD SMU via a
mailbox queue append that overruns a ring at `0x18850` into DMA pointer
tables, then fixes up state) — read as public knowledge, **nothing executed**;
its repo is of another board `(src: biosmod_8902_co/trabalhos/54-fraqueza-de-fila-do-smu.md)`.
Our CO gate lives in SMU RAM unreachable from x86 (M2), our DMA descriptors sit
at `0x1a560/0x1a600` (T33), and the host *does* submit messages — so the exact
question was asked statically of **our** SMU (Xtensa, `f4cb81d9…`, file==VA):
is there an unmasked ring-append reachable by a host message, with counters or
DMA tables adjacent? `(src: biosmod_8902_co/trabalhos/54-fraqueza-de-fila-do-smu.md;
construcoes/54-smu-fila/out/VEREDITO.md)`.

Answer: **FRAQUEZA REFUTADA**, two independent reasons with byte evidence
`(src: biosmod_8902_co/construcoes/54-smu-fila/out/VEREDITO.md)`:

- **R1 — no message queue in the host path.** The dispatcher `FUN_00001134` is
  a synchronous doorbell protocol (§3): the u16 limit at `0x7b20+fila*2` is
  checked *before* the table index (out-of-range → response `0xfe`, and those
  limits read `0x0084` as independently measured in T33); there is no slot
  counter, no write pointer, no append. The only ring in the body is the debug
  log `0x12c0` with an explicitly masked `0x20` wrap
  `(src: biosmod_8902_co/construcoes/54-smu-fila/out/VEREDITO.md; RASTRO.md M25)`.
- **R2 — every host-reachable indexed store is bounded.** A scan of all
  `base + idx*stride` stores (77 functions in the whole body) intersected with
  the host-callable closure (`out/closure_host.json`: 246 table lines, seeds
  fila0/1/2, 507 functions) leaves **19 functions**; each is bounded by loop
  constants, explicit masks (`&7`), capacity guards before the write, or
  constant call-site indices — and none writes adjacent to the DMA descriptor
  banks `(src: biosmod_8902_co/construcoes/54-smu-fila/out/VEREDITO.md table)`.

The coordinator's independent pass: his own scan of the decompiled dump (1465
functions) found 32 scaled-store functions — 29 already in the worker's census,
3 extra (`1c9d8`, `1bbf4`, `2600`) whose call-sites are all literal constants;
the function-pointer-table setter `0x14514` (`1c9c8`) has 19 call-sites, all
constant; the DMA motor `31e28` checks `ch > 7 → panic` *before* writing; and a
follow-up value-dimension trace (`325f4`'s single caller passes `param_5 = 0`)
killed the pointer-**value** hijack through the legitimate door too
`(src: biosmod_8902_co/RASTRO.md M25)`. Lateral findings kept as reopening
triggers, not as the weakness: L1 out-of-bounds **read** (`254d0/25578`,
index `ARG>>16` ≤ 0xff), L2 unmasked byte-store in `1a8c` on DMA busy flags
(but descriptors are stack-built internals, zero host closure), L3 `34a40`
writes next to the descriptors but only on the display path outside the host
closure `(src: biosmod_8902_co/construcoes/54-smu-fila/out/VEREDITO.md §laterais; RASTRO.md M25)`.
Reopening requires one of three named triggers (host-built DMA descriptor with
a host-controlled `+0x10` byte; a host path writing the `0x14514` table; an
AMD document naming a message queue for this IP)
`(src: biosmod_8902_co/construcoes/54-smu-fila/out/VEREDITO.md)`. This is
**M25** in doc [10](10-negative-results.md). Three transferable techniques were
adopted from the public work: `0xFD (PREREQ) vs 0xFE (UNKNOWN) vs 0xFF
(gated)` mailbox surface probing, the "FF is ambiguous — read twice from two
sources" rule (which had already burned us in flash 10), and the post-primitive
FIXUP discipline `(src: biosmod_8902_co/trabalhos/54-fraqueza-de-fila-do-smu.md §regras de engenho)`.

## 8. What we could NOT localize (honest ledger)

- **The TOS svc-table of 0.11.0.87 was never located** — the handler-number →
  routine map for that kernel stayed a named gap (the e02 `svc` census matched
  between our counts, 8/16/19 per-blob, but no table found)
  `(src: biosmod_8902_co/RASTRO.md §A line 51, M21; docs/05-gen4-the-clamp.md Open questions)`.
- **The NBIO on-chip microcode**: named by elimination (M19) but its source
  region is unreadable by every offline path we have (the only encrypted blob,
  HIC, is inert/identical) `(src: biosmod_8902_co/RASTRO.md M19)`.
- **Doorbell receipt on the actually-loaded 56.76.0 SMU**: the proven receipt
  tables (§5) sit in `e07`/SMU blobs of the never-loaded generation after
  §DDD; no source records a re-scan of the loaded `0x421400` SMU body for the
  `67ac/77ac`-class keys — listed as Open questions rather than claims.
- **Semantics of the `0xFFF0001C..23` strobes and bit 21 of `0x0904_9914/D914`**
  — "possible lock", never identified `(src: biosmod_8902_co/RASTRO.md §DDD, §FFF)`.
- **Whether the SMU honours the A36 boost base** patched to 4550 MHz (the menu
  work, out of the Gen4 question): the fuse-derived boost base is inferred and
  **not measured**; flash 39 and its reading were pending at campaign end
  `(src: biosmod_8902_co/RASTRO.md §GGG; docs/07-co-pbo-menus.md)`.

## Lessons (method, keep on file)

> - **Byte-combining ≠ pointer.** Two early tasks (T24/T30) built a chain of
>   inference on byte-values that could fill a pointer table; the campaign's
>   own correction records the lesson verbatim — a value that *fits* a slot is
>   not evidence anything *points* there ("byte-combinando ≠ ponteiro").
>   `(src: biosmod_8902_co/RASTRO.md §A line 24, §A line 30)`
> - **Endian scans burn you silently.** The coordinator's `0x0904xxxx` scans
>   run big-endian produced a false negative against our own firmware; the LE
>   scan found the exact keys. And a negative scan is only worth the exact
>   literal searched (house erratum: hunting `0904901c` when the live key was
>   `67ac`). `(src: biosmod_8902_co/RASTRO.md §A line 51; HANDOFF-FINAL-20261122.md §4.5, §6)`
> - **Directory attribution must be proven by load path, not content
>   similarity.** "Looks like the active generation" sustained two weeks of
>   patches into never-loaded Cezanne blobs; only the SMU-version match against
>   the kernel's reported line settled which directory the CPU actually loads.
>   `(src: biosmod_8902_co/RASTRO.md §DDD)`
> - **Constants match inside code.** Aligned dwords in Thumb blobs read as
>   addresses can be instruction halves (T51 §4); magic strings match in
>   payloads (VZL1 lesson); validate context (function prologue, PC-relative
>   reference) before believing a pool.
>   `(src: biosmod_8902_co/construcoes/51-emul-commit-0904/out/C_prova_smu_doorbell.txt; HANDOFF-FINAL-20261122.md §6)`

## Open questions

1. Re-scan the **loaded** SMU body (`0xBC0B0500` sub1 @`0x421400`, 56.76.0) for
   the doorbell/command-port constants — the receipt proof exists only for the
   never-loaded generation (§5/§8).
2. Semantics of the `0x3230` strobe groups and bit21 (inherited from doc 05).
3. The e07 save/restore model's entry count differs between sources: the
   analises/12 README says "3 + 8 entries (stride 12)", the independent review
   says groups "3 and 7", and HANDOFF §4.2 records the correction "3+7 = **10**,
   not 3+8" — the review/§4.2 pair is the corrected reading but the primary
   blob was never re-counted after §DDD.
   `(src: biosmod_8902_co/analises/12-smu-e07-restore/README.md; analises/12-smu-e07-restore/REVISAO-INDEPENDENTE-20261122.md; HANDOFF-FINAL-20261122.md §4.2, §4.5)`
4. Whether `svc` numbering is stable across TOS generations (0.14.0.43 vs the
   0.11.0.87 e02 counts matched within ±1 in T51, but no table-to-table proof).

## Sources

- `biosmod_8902_co/analises/11-cadeia-psp-executor/README.md` — PSP executor chain (0x1da8/0x1039/0x103a), files and Ghidra outputs, NV_DATA erratum.
- `biosmod_8902_co/analises/11-cadeia-psp-executor/scripts/{chain_re,executor_re,dispatch_map,funcmap,nvs_decode}.py` — capstone method: literals, BL-caller scan, tbb/tbh + svc census, prologue funcmap, NVS decode.
- `biosmod_8902_co/analises/12-smu-e07-restore/README.md` — e03/e07 zlib@+0x100 extraction, save/restore model, Ghidra Xtensa flow.
- `biosmod_8902_co/analises/12-smu-e07-restore/REVISAO-INDEPENDENTE-20261122.md` — independent reproduction (shas of e03/e07) and the classification table of what is fact vs hypothesis.
- `biosmod_8902_co/analises/16-diretorio-psp-ativo/{scripts/gen4dis_driver_ativo.py,out/resultado-a28.txt,out/verif113-ctx3.txt,out/verif114-escritor-smn.txt}` — SMU-version-by-directory table, `0x3230`/caller/whitelist disassembly commentary, whitelist→ctx link.
- `biosmod_8902_co/trabalhos/11-gate-co-e-limpador-nativo.md` — the gate-naming task spec (CO gate, public-sources discipline).
- `biosmod_8902_co/trabalhos/12-probe-estaatico-smu.md` — static SMU-body probe spec; "one function at a time, listing out of the conversation" method rule.
- `biosmod_8902_co/trabalhos/48-a3-bl-escritor-do-clamp.md` — T48 spec: PSPTool offline, census method, negative-as-valuable rule.
- `biosmod_8902_co/construcoes/48-a3-bl/out/census_global.txt` — 292-blob census, `exact=[]` per blob.
- `biosmod_8902_co/trabalhos/49-lzma-agesa-censo-clamp.md` — T49 spec: full-LZMA flash census method (verdict recorded in RASTRO §A line 49 / M19).
- `biosmod_8902_co/analises/13-e03-backend-applier/out/e03_dispatch_tables.txt` — e03 SMU dispatch tables as image data (14 queues, 289 handlers).
- `biosmod_8902_co/trabalhos/50-diff-7306-7403-alavanca-oficial.md` — T50 spec: 7306×7403 byte-diff method, input SHAs, thumb-census recipe, lições list.
- `biosmod_8902_co/trabalhos/51-emul-commit-0904-direcao.md` — T51 spec: translation confirmation, emulation-with-shim plan, pins.
- `biosmod_8902_co/construcoes/51-emul-commit-0904/out/{A_tabela_alvos_tail.txt,B_q2_forma_19blobs.txt,C_prova_smu_doorbell.txt}` — COMMIT write table, 19-blob form scan, block-identity proof + THUMB-halves erratum.
- `biosmod_8902_co/trabalhos/54-fraqueza-de-fila-do-smu.md` — bc250 precedent summary, the three branches, technique rules.
- `biosmod_8902_co/construcoes/54-smu-fila/out/VEREDITO.md` — T54 verdict: synchronous dispatcher, 19-function table, lateral findings, reopening triggers.
- `biosmod_8902_co/HANDOFF-FINAL-20261122.md` §4, §6 — RE-closed chain, Ghidra arch map + Xtensa encodings, extraction recipes, scan-literal lesson.
- `biosmod_8902_co/RASTRO.md` (§A lines 34/48/49/50/51, §C A2/B7, M17–M22, M25, §DDD, §GGG) — master log: verdicts, M-registry, directory correction, A36 boost context.
- Cross-doc: extraction/directory map `docs/03-firmware-anatomy.md`, request timeline `docs/04-boot-timeline.md`, clamp verdict `docs/05-gen4-the-clamp.md`, probe results `docs/08-smn-probes.md`, M-registry `docs/10-negative-results.md`, menu/boost context `docs/07-co-pbo-menus.md`, glossary `docs/16-glossary.md`.
