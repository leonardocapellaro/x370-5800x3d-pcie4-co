# 04 — Boot timeline on the 8902 platform, with the evidence

## Summary

We instrumented real boots of the Crosshair VI Hero + 5800X3D (BIOS 8902 and
our modified images) with our own observers placed in pre-memory PEI, PEI, DXE,
OS runtime and USB boot services. The two load-bearing records are: (1) the
hardware-captured DXE "38 requests" trace of the native SMU mailbox interface
(v2.6 ALL3, 16/11), which brackets the Gen4→Gen3 clamp exactly inside request
30; and (2) the static/dynamic forensics of the AMI dispatcher that explain why
*our own* PEIMs were silently never dispatched on 20/11 while structurally
identical ones dispatched on 16/11. This doc gives the ordered story; the clamp
mechanism itself is in doc 05, the PSP-side RE in doc 09, closed doors in
doc 10, builds in doc 11.

## 0. Before x86: PSP and SMU come up first

The AMD Platform Security Processor is an on-chip ARM service processor
(public knowledge; consistent with every PSP binary we decoded being
Thumb code, Ghidra `ARM:LE:32:v8T`) running its own OS; the SMU is a separate
signed microcontroller whose firmware we decoded as Xtensa
(`Xtensa:LE:32:default`, file==VA) `(src: biosmod_8902_co/HANDOFF-FINAL-20261122.md §6; analises/12-smu-e07-restore/README.md)`.
The certificate chain we mapped is on-chip-rooted (`6C9E` PSP ROM → BL →
TOS/ABL0/HIC/SMU nodes), so the flash contains signed payloads whose execution
order we could only observe from the x86 side `(src: biosmod_8902_co/RASTRO.md §P, §56)`.
The SMU version that actually runs on this CPU is **56.76.0**, matched byte-wise
by header against the kernel line `ryzen_smu: SMU v56.76.0` in all 11 journal
boots; this is what let us name the *active* PSP directory (see doc 03 §PSP
directory) `(src: biosmod_8902_co/RASTRO.md §DDD)`.
An early "SMU restores a policy bank autonomously at boot" story (e07
dump/restore of A/B strap flags per CCD) was built on blobs we later proved
belong to a never-loaded Cezanne directory; with the clamp writer now named in
the active PSP driver (below), a persistent bank is not even needed and was
demoted to "probable ghost" `(src: biosmod_8902_co/analises/12-smu-e07-restore/README.md; RASTRO.md §DDD)`.

## 1. BL hands over a ready PEI image

The PSP BL loads and verifies, then — measured — the `$BL2` blob at CAP
`0xe82800` (LZMA, size `0xdb060`) delivers the **reset image** to RAM
`0x9c7ffe0`: that image *is* the decompressed inner PEI firmware volume
(3 670 016 B) containing the SEC, the AMI PeiCore and the native PEIMs
`(src: biosmod_8902_co/RASTRO.md §56; constructions cross-check RASTRO §58)`.

## 2. SEC → PeiCore

The SEC is the single type-03 file of the inner FV at `+0x37bac8` (VZL1,
ImageBase nominal `0x09ffb958`, EP `0x2f00`). We disassembled the whole
handoff chain byte by byte: 16-bit `STARTUP_` (`lgdt`, `cr0|=1`,
`ljmp 0x10:0x09ffe890`) → flat 32-bit entry → `cmp [esp+0xc],'SSSS'` path
select (path 1 = cold boot: POST code `0x11`, CR4, MTRRs) → main
`call 0x9ffbc00` copies a 34×8 IDT from `0x9fff768` → builds the core context
`{DataSize 0x24, base 0x9c80000 (hardcoded ×3), FVlen 0x380000}` → validates
the FV at runtime → `call [ebp+8] @0x9ffbcf7` = **call to PeiCore with
(ctx, PpiList)** `(src: biosmod_8902_co/RASTRO.md §58)`.
The PeiCore's FFS is at inner `+0x3040`; entry `0x240`; dispatch fetch tries
AMI section `0x12` (VZL1) first, plain `0x10` fallback `0x2dc5` (doc 03).

## 3. PEI: dispatch model, and the mystery of our own PEIMs

Model (from the decoded core): an APRIORI file (EDK2 GUID
`d685eed1-9f4e-4e0e-b380-2147af8eed3e`, type 0x02) lists 10 GUIDs; the inner
FV also carries an internal APRIORI table at `+0x78` with the same 10; then a
dependency-expression fallback pass dispatches the remaining native PEIMs
(162 on the base) `(src: biosmod_8902_co/trabalhos/42-despacho-no-core-decodificado.md; RASTRO.md §58)`.

The mystery, measured on the board (owner flashed; our observers read):

| flash | image | outcome |
|---|---|---|
| v2.6 (16/11, V2 era) | early observer + late PEIM (structurally the same recipe) | **dispatched**; early block shows 6 points and the `memory_at_entry=false → memory_seen=true` transition. Correction we recorded: `pei_found:True` is a field of the `TraceGuid` module, not the early probe `(src: biosmod_8902_co/trabalhos/53-predicado-dinamico-despacho-peicore.md preamble)` |
| 12 | `w1_unclamp` PEIM (first in APRIORI) | never dispatched: PEI log zero; its entry creates HOBs unconditionally, so absence of HOBs = never called; `writes=0` honoured |
| 13 | W1-A1 (entry aligned to `0x390`) | **same result** — the "odd entry point" hypothesis died with measurement |
| 14 | PEI-probe PEIM (different content, new GUID) | **NUNCA_DESPACHOU** — triple death rules out content/GUID/alignment as predicate `(src: biosmod_8902_co/CLAUDE.md campaign log; STATUS.md FLASH 12/13; construcoes/46-peiprobe/capturas/20261120-flash14/LEITURA.md)` |

Offline forensics (docs 03/10 for the full chain): T41 decoded VZL1 and proved
our format path is accepted (fetch 0x12→0x10); T42 enumerated the dispatch
paths (apri `f035c9`/flag 2, fallback `f036e5`/flag 0, tail gate `f0384c`) and
showed **no static predicate in the core discriminates** S5 (dispatched) from
W1 (dead) — depex `06 08`→TRUE both, machine gate both, no size gate (smallest
native blob 144 B dispatches) — pointing instead at four runtime inputs,
including a byte-state with a setter that has zero internal callers and a
"mode" test `[[ctx+0x64]+0xc] != 0x11` (the core's real magic is the
4-byte `PeiC` = `50 65 69 43`) `(src: biosmod_8902_co/trabalhos/42-despacho-no-core-decodificado.md)`.
T53 re-framed the question (identical FFS twins dispatched 16/11, dead 20/11)
and the coordinator's capstone pass found **five gates `cmp dword [X+0xc],0x11`**
at `f005cf/f00782/f02c16/f035ef/f03862` plus a skip-APRIORI branch
`f035ef→f036ab`; PAD file order was killed-with-measurement (the 16/11 dispatch
had the same PAD layout, DXE type-7 first at `0x1d5690`) and the 16/11 vs 20/11
CAP bases were measured byte-identical apart from our containers
`(src: biosmod_8902_co/RASTRO.md M24; trabalhos/53-*.md)`.
Then T56/T57/T58 finished the loop: the remaining raw FV regions decoded to
NVAR default store + Windows DLLs (flash 100 % swept, M26); the caller is the
**SEC, inside the FV itself**; and the "mode" byte `[eax+0xc]` is written
**constant 0** by the core (`mov [eax+0xc],edx @f008f9`, zero stores of `0x11`
in the entire reset image) — so the five `0x11` gates **never open** in our
boots and the cause migrated to the remaining dynamic inputs (byte-state
`[ctx+0x69]` / external loader return) `(src: biosmod_8902_co/RASTRO.md §56/§57/§58, M24)`.
The final board data point (flash 21, OBSPEI-A4.MIN): a DXE observer confirmed
`PEIM_HOB_ABSENT` (4th death of the entry line) and `CTX_GONE` (core context
does not survive the TemporaryRAM window visible to DXE), closing the DXE-
observer route to that question (M27 class rule)
`(src: biosmod_8902_co/RASTRO.md §55 FLASH 21)`.
Status as of campaign end: **unresolved, with the candidate space narrowed** —
see docs 10/13.

## 4. DXE: where the SMU interface is proxied, and where our probes ran

DXE drivers live in FVMAIN (LZMA envelope, doc 03). Our observers in DXE ran at
driver entry (and at ReadyToBoot where designed), and the V2-era ALL3 build put
a proxy on the native SMU mailbox service. Protocol measured: a native request
(`09d7aa5d`-class) copies six DWORDs (subcommand in word 0) and the transport
(`09d7b602`) writes mailbox registers `03b109c4..03b109d8`, sends the message
at `03b10530` and polls `03b1057c`; the outer SMU mailbox message is 8
`(src: biosmod_v2/diagnostics/8902-boot-trace-v2.6-full-smu-20261116/hardware-capture-20261116/REPORT.md)`.
(The x86 side never submits the PSP QCB rings — those are PSP-only traffic;
x86 touches only the reader set `03b10564/57c/530` `(src: biosmod_8902_co/RASTRO.md M16)`;
the two register families and the exact split are still an open detail.)
Honest scope notes from the capture itself: policy codes inside packets differ
from actual link speeds, and an in-band request *brackets* native work, it does
not name the instruction `(src: .../hardware-capture-20261116/README.md)`.

### The 38-request timeline (hardware-captured, ALL3 v2.6, two independent BMC traces)

All 38 requests retained, native EFI statuses zero; the SMU GUID HOB is 62,472
bytes, DXE export area 131,072, log 165,192
`(src: biosmod_v2/diagnostics/8902-boot-trace-v2.6-full-smu-20261116/README.md)`.
Cross-checked across six later boots (38 calls, 23 register snapshots / 506
reads each) `(src: biosmod_v2/diagnostics/8902-gen4-reset-evidence-20261117/analysis/REPORT.md)`.

| request | measured event | who writes what |
|---|---|---|
| 9 | status poll, input `[0,0xd,0,0,0,0]`, reply `[3,1,0,…]` | x86 poll only |
| 14 / 23 | port-table query / upload (0x23 selectors 3/6) | x86 hosts port tables |
| 18 | state **MAPPED** | **TE** (x86 PEIM `21be6180`) writes `GEN4_DIS := 0` to the PCIe cores (site `0x9d662ef`, wrapper `0x9d685d8`; §DDD refines sites to `0x9d662e3/0x9d662f1`, writes `GEN3_DIS(0x7a):=0` and `GEN4_DIS(0x84):=0`, core≠2) `(src: biosmod_8902_co/trabalhos/92-a35-strap-regrava.md; RASTRO.md §DDD)` |
| 26 / 27 | topology query; host rewrites chipset packet devfn/control before re-upload | x86 |
| 29 | status returns `[3,0x102,8,0,0,0]` — **state 8 = VETTING**; native `21BE` polling loop treats it as an event and continues with subcommand `0x308` | SMU→x86 |
| **30** | **the clamp**: subcommand `0x308` brackets max-link-speed **4→3** on GPU `00:03.1` (`f7733904→f7733903`), M.2 `00:01.1` (`f7733844→f7733843`), chipset uplink `00:01.3` (`00733884→00733883`); **LinkCap2 `180001e→0000000e`** on all three; identity/width/LinkCtrl unchanged in the interval. In BMR_0008, `11480604/11880604` read 0 until sample 15 (call30/after) then 1; GPU/M2 LC `d0000207` → `f0000207`/`f0000203` | SMU↔PSP policy exchange (mailbox commands `0x1039` challenge / `0x103a` executor as decoded in driver 0.11.0.87 — which on *this* board is Cezanne code, see errata below). The clamp writer named for the active stack: driver **0.14.0.43** function **`0x3230`** — strap index `0xFFFE0084` at `0x0904_97AC`/`0x0904_D7AC`, writing **1** when the data word (`+4`) reads 0; preceded by 8 indices `0xFFF0001C..23 := 1` via `0x0904_901C/9020` and `D01C/D020`; followed by OR-bit21 at `0x0904_9914/D914`; single caller `0xaa62` gated by `ctx[3]` `(src: hardware-capture-20261116/REPORT.md; reset-evidence REPORT.md; RASTRO.md §DDD; analises/11-*.md; analises/16/out/resultado-a28.txt)` |
| 31, 33 | PERST events (data type 4) | SMU/native |
| 32, 34 | further `0x308` resumes; at **34** GPU/M.2 become DLL-active **Gen3 x16 / x4** | x86 TE resume loop `FUN_09d6983d → 0x9d6996f` |
| 35 | **DONE** | — |
| 36 | final packet query (policy4 still present in every captured packet) | — |
| 38 | chipset uplink reaches Gen3 x4 | — |

`(src: biosmod_8902_co/trabalhos/92-a35-strap-regrava.md request table — the coordinator's synthesis over the two v2 traces; biosmod_v2 hardware-capture-20261116/REPORT.md; reset-evidence REPORT.md)`

Errata we must flag: the `0x1039/0x103a` challenge/executor chain and the
`0x1118_06xx` window writes belong to driver 0.11.0.87, which §DDD proved is
**Cezanne content that never loads on this board** — the per-request PSP side
of row 30 is therefore best supported for the *active* driver by function
`0x3230`, and the table above keeps both as recorded by their own sources
`(src: biosmod_8902_co/RASTRO.md §RR vs §DDD)`.
Also negative results that shape the table: no x86 code in the whole expanded
flash writes the clamp proxy or the decision (M15/M19), and the clamp register
block reads **identical DXE→OS in the same boot** (64/64, witness `0x001A43B9`;
VIVA-L1 OS service, boot #5), killing "the clamp rewrites between DXE and OS"
`(src: biosmod_8902_co/RASTRO.md M15/M19; STATUS.md VIVA-L1 boot #5)`.

### Probe/phase matrix (which of our instruments ran where)

| phase | probe (flash) | result one-liner |
|---|---|---|
| PEI (attempted) | W1 / W1-A1 / PEIPROBE (12/13/14) | never dispatched (above) |
| DXE entry, SMN CF8/CFC | SMN12-A1 (9) | PSP window `0x03b10700` reads FF while NBIO decodes |
| DXE entry, map | SMN12-A2 (10) | terna all-FF with live NBIO ⇒ no x86 route to PSP box (M22) |
| DXE entry, NBIO block | NBIO-B1 (11) | **W_VIVA** — witness `0x001A43B9` alive on clean base |
| OS runtime (service) | VIVA-L1 (boot #5) | clamp block identical DXE→OS; mailbox counters moved `0/1/0/8 → 5/fd/0/2` |
| DXE entry | SMU101-A1 (15) | pages `0x0101/0x0301` all-FF (A_MORTA) |
| DXE entry | PG0904 (16) | page `0x0904` invisible to SMN (PÁGINA_FORA) |
| DXE entry + ReadyToBoot | OBSPEI A1/A2/A3 (17/18/19) | A1 dispatched, volatile log lost; A2 hung POST 61 (read type-0/13 memory); A3 booted but corrupted the variable store → owner reflashed RC1 (flash 20); lesson M27: never multi-variable multi-KB writes at entry |
| DXE entry, minimal | OBSPEI-A4.MIN (21) | booted clean; PEIM_HOB_ABSENT + CTX_GONE + SEC PPI list assembled at runtime as an exact copy of the static block |

`(src: biosmod_8902_co/RASTRO.md §A lines for tasks 35–38/46/47/52/55; STATUS.md flash blocks; construcoes/{46-peiprobe,47-smu101-sonda,52-pagina-0904}/capturas/20261120-flash1{4,5,6}/LEITURA.md)`

## 5. OS side

The V2-era trace recorded USB boot-services stages 1/2/3 (3 controllers / 4
input handles final) alongside the boot `(src: biosmod_v2/diagnostics/8902-gen4-reset-evidence-20261117/analysis/REPORT.md)`.
In Linux, `lspci` shows the post-clamp state (roots advertising 8.0 GT/s, end
devices capable of 16.0 — e.g. the A35 measurement table in
`trabalhos/92-a35-strap-regrava.md`). Curve Optimizer and PBO on this part run
through native DXE chains that end in **MP1 messages** (`0x35`/`0x36` for CO,
`0x2f` for scalar boost) from the Vermeer SMU DXE driver `9a29bbe9` — the same
native interface our A36 menu work exposes `(src: biosmod_8902_co/RASTRO.md §GGG)`
(detail: doc 07).

## Open questions

- The residual PEI-dispatch cause (byte-state `[ctx+0x69]` vs external loader
  return) was left to a board measurement the campaign ended without.
- Exact split between x86-writable mailbox payload window
  (`03b109c4..d8`) and PSP-exclusive submit/ring registers
  (`03b10570/574/0524/0a40`) — both statements are in our sources with
  different register sets; reconcile before reusing either list.
- Whether request 30's PSP-side exchange on the *active* stack uses the same
  `0x1039/0x103a` command numbers (decoded only on Cezanne code) or an
  equivalent not yet named.

## Sources

- `biosmod_v2/diagnostics/8902-boot-trace-v2.6-full-smu-20261116/README.md` — ALL3 capture design, bounds, "38 requests", policy≠speed caution.
- `biosmod_v2/diagnostics/8902-boot-trace-v2.6-full-smu-20261116/hardware-capture-20261116/REPORT.md` — request-30 bracket, LinkCap/LinkCap2 table, mailbox transport addresses, DLL-active at 34.
- `biosmod_v2/diagnostics/8902-gen4-reset-evidence-20261117/analysis/REPORT.md` — six-boot comparison, 506 register reads, `...80604` flip, LC traces, Setup `+0x239/+0x23b`.
- `biosmod_8902_co/trabalhos/92-a35-strap-regrava.md` — request table 18→35 (Portuguese; translated), A35 outcome table.
- `biosmod_8902_co/trabalhos/41-pesquisa-vzl1-despacho-ami.md`, `trabalhos/42-despacho-no-core-decodificado.md`, `trabalhos/53-predicado-dinamico-despacho-peicore.md` — PEI dispatch forensic chain and its correction preamble.
- `biosmod_8902_co/construcoes/41-vzl1-re/README.md` — PeiCore decode facts used in §2.
- `biosmod_8902_co/RASTRO.md` (§P, §II, M15/M16/M19, M24/M26/M27, §55–§58, §DDD, §FFF, §GGG) — master log for every claim above.
- `biosmod_8902_co/analises/11-cadeia-psp-executor/README.md` — PSP-side chain and mailbox commands (with the §DDD caveat).
- `biosmod_8902_co/analises/12-smu-e07-restore/README.md` / `13-e03-backend-applier/README.md` — autonomous restore story (Cezanne blobs) and e03 applier.
- `biosmod_8902_co/analises/16-diretorio-psp-ativo/out/resultado-a28.txt` — active driver 0x3230 disassembly context, whitelist.
- `biosmod_8902_co/STATUS.md` + `biosmod_8902_co/construcoes/{46-peiprobe,47-smu101-sonda,52-pagina-0904}/capturas/20261120-flash1{4,5,6}/LEITURA.md` — flash 12–16/21 board outcomes, VIVA-L1 boot #5.
- `biosmod_8902_co/HANDOFF-FINAL-20261122.md` — final state, toolchain identities.
- Cross-doc: clamp mechanics `docs/05-gen4-the-clamp.md`, PSP RE `docs/09-psp-driver-re.md`, closed doors `docs/10-negative-results.md`, build catalog `docs/11-build-catalog.md`, tooling `docs/14-tooling.md`, glossary `docs/16-glossary.md`.
