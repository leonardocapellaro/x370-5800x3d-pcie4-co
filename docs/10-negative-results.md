# 10 — Negative results: the registry of closed doors

## Summary

This campaign's crown jewel is what it **proved does not work**, with the
measurement that closed each door. Two disciplines made the registry possible:
every flash carried a **pre-registered prediction matrix** (named branches with
the decision each branch would force), and no door was called dead without
"closed with measurement" — live controls decoded twice in the same boot,
echoes recorded, raw bytes preserved with sha256. The master log is
`biosmod_8902_co/RASTRO.md` (§B "registro mestre de caminhos mortos", one-line
verdicts M1–M30); part (a) below translates that registry, part (b) gives the
bigger closed routes in hypothesis→test→measurement→status form, and the last
table lists, per door, **what would reopen it** when the sources state a
trigger. Nothing here is speculation: each entry points at the file that owns
the evidence.

## Part (a) — the M-registry (M1–M30)

Format: `M## — what is dead — what closed it — (src)`. "src: RASTRO §B" =
`biosmod_8902_co/RASTRO.md` §B unless otherwise noted. Supersessions are marked.

- **M1** — the host→SMU "mesa" (task table) protocol for installing/using CO: commands `0x88/0x8d` die at the host-table limit `0x84`, the PSP-kernel task mesa is dead code for traffic, and the drivers-module ring is internal with no host-feedable bridge — T29 + T31 + T32 (`construcoes/31-verificacao-coordenador/`).
- **M2** — direct x86 writes into SMU data RAM: the DMA/MMU engine windows exist only inside the SMU's Xtensa body; the SMN map exposes no aperture — T33 four-link proof (`construcoes/33-smn-smu-ram/`).
- **M3** *(then M3-REVISTO, then closed again)* — the x86→box-12 (QCB) write route: originally buried on FF reads **of write-only registers — the write itself was never measured**; the errata re-opened it as A20/GATE12 with a faithful protocol replica + CO echo, and flash 22 re-closed it **triple-measured** (no write echoed; decisive `SET(0)=0xFF` in DXE; owner's OS refused CO −22 8/8) — (src: RASTRO §B M3-REVISTO, §L, §M; `trabalhos/76-fila12-gate-a20.md`).
- **M4** — PCIe config mirrors `0x118xxxxx` as the unclamp target: writes landed without echo across the V2-era SONDAS/REVET decade; the real policy proxy is `0x03810054` in the `0x0381xxxx` block — T3–T5, T39 "revirada" (`construcoes/03..05-sonda*`).
- **M5** — entry-point parity/alignment as the PEI dispatch filter: refuted on the board — flash 13 shipped a 16-aligned entry point `0x390` and still NO_STATE — (src: RASTRO §A 40).
- **M6** — dispatch filters by module metadata (size — a 144-byte native dispatches; raw section `0x10` — the raw S5 dispatches; FFS/DEPEX/meta/characteristics/checksum/insertion order — all byte-identical S5×W1): FLASH 12 forensics + T41 `revisao-coordenador.txt`.
- **M7** — "an official BIOS without the strap, or downgrade the policy module": 12 versions 7403…8801, none strap-free; the function always travels in the signed module `0x16590` (digest matches) — T17 (`construcoes/21-corpus-intermediarias/`), T20.
- **M8** — a pre-Zen3 RV1 container accepted by the 8902-era BL (slot `0x28`): post-mortem C2 — don't accept without a new hypothesis on that exact link — T20 (`construcoes/20-post-mortem-swap/`).
- **M9** — SWAP-7306 (`94859606…`): **never reflash** — proven gate defect + a history of F9 recovery — T19 (`construcoes/19-swap-7306/`).
- **M10** — "request 30 rewrites the policy block between DXE and OS": the clamp block read 64/64 identical DXE→OS in the same boot (witness locked) — T38 VIVA-L1 boot #5.
- **M11** — not a dead end but a **fence** (a wall, not a door): fuse/OTP/authorization state in NO scenario; AMD content/signature untouched; flash/reboot/live writes only by the owner; publishing binaries forbidden. *Supersession:* **M11-revisto** (owner, 21/11): AMD content editable **only in explicitly authorized experimental CAPs** (signature intact, risk assumed in writing); drivers-PSP and SMU-blob edits then became "proven classes" intra-era (flashes 35/36 booted), while A34/A21 measured that the PSP verifies every blob it loads (`HANDOFF-FINAL-20261122.md` §7; RASTRO §P).
- **M12** — "decompress VZL1": the format never compressed anything (it is a strip-header container) — T41 decoder 166/166.
- **M13** — QEMU/OVMF as a test of dispatch/vetting: deferred with justification (the bench never exercises the BL; its memory map lacks the AMI's Reserved/SMRAM types, which later hung OBSPEI-A2 on the real board) — (src: RASTRO §B M13; §A 55 flash 18).
- **M14** — naming the loader/dispatch-state owner statically in any PEI-FV module: the 166 decoded bodies do not contain the other side of the inputs (the 16-byte protocol is only in the core; zero literal pointers to the core; zero replicas of the setter) — the mediator is a RAM block `[IDTR.base−4]` + vtable — T45 (`construcoes/45-dono-loader/`).
- **M15** — finding the speed decision or the clamp write in x86 code: zero proxy `0x03810054`, zero witness `0x001A43B9`, zero real svc `0x103a` in all 166 x86 PEs, reconfirmed over 7 034 024 B of zlib-expanded CAP material; the declared LZMA caveat was later executed and closed by T49/M19 — T43 (`construcoes/43-mapa-gen4/`) + `construcoes/49-lzma-agesa/`.
- **M16** — submitting request 30 (or any PSP svc/cmd) over SMN/mailbox from x86 in a CAP: zero code references to the submit registers (`0x03b10570/574/0524/0a40/0a30`) and QCB (`0x03b10700/704/718`) in the 166 modules — only readers exist; submission is exclusively PSP-side (kernel side T31/T32, aperture side T35/T36, x86 side T43-L2) — (`construcoes/43-mapa-gen4/out/l2_emissores.json`).
- **M17** — finding the clamp writer for `0x03810054` inside the SMU Xtensa body `f4cb81d9…`: zero `0x0381xxxx` literals; command `0x1e`(30) writes a **context field in RAM** (`0xb350`), not NBIO — T43-L1 (`construcoes/43-mapa-gen4/out/l1_clamp_writer.json`).
- **M18** — …in the PSP stack that **runs** on 8902 (active-dir BL/TOS/DRIVERS/PSP-OS): census of 292 blobs zero-exact (coordinator's independent scan agreed), BL byte-identical RC1×clean (sha `5b129195…`), homologous NBIF-store mechanism exists only in **inert** Zen1/Zen2 BLs — T48 (`construcoes/48-a3-bl/`).
- **M19** — …anywhere (literal **or** computed) in the **whole expanded flash** of both bases: ~48.7 MB unique / ~5.28 M instructions censused (38 LZMA payloads + nested inners), movw/movt synthesis + `[reg+disp∈{0x54,58,5c}]` + SMN cycle: **zero**, both bases; 38/38 payloads byte-identical RC1×clean; the only differing cluster is our own V2 probe container (181 official modules identical) ⇒ the clamp writer never existed as code in this flash — T49 (`construcoes/49-lzma-agesa/`). *Supersession note:* **M19-interpretation** — §WW's reading "NBIO microcode is therefore the only remaining route" was hollowed by §XX: that census had searched the wrong literal (`0904901c` instead of `67ac`); the TE window-writer **is** in the flash (a RE target, not a patch target). The zero-writer-of-`0x03810054` result itself stands — (src: RASTRO §XX, line ~1303; `HANDOFF-FINAL-20261122.md` §6).
- **M20** — finding the clamp's policy mechanism (gate devid FCH→`ctx+3`→COMMIT `svc 0x7c`→family `0x0904_90xx`) as content of our flash, or the lever in the official 7306×7403 pair: the mechanism exists only in **inert dir6** (Zen2 0.14.0.43, e14 `0x469f00`, table 24×12 @`0x480a70`); the active dir1 (Zen3 0.11.0.87) has no signature of it ⇒ flash-content search closed — T50 (`construcoes/50-diff-7306-7403/`).
- **M21** — finding the clamp applier via the native PSP COMMIT (family `0x0904`): the COMMIT's **emitter does not exist** in the active PSP-OS (e14 Zen3 has no table/pool/consumer; the 3 `0904f1xx` dwords were THUMB halves), and the COMMIT target is PSP-peripheral MMIO anyway — never `0x03810054` — T51 (`construcoes/51-emul-commit-0904/`).
- **M22** — reaching the SMN pages `0x0101_xxxx`/`0x0301_xxxx`/`0x0904_xxxx` (SMU/QCB/PSP-peripheral) through the **direct CF8/CFC gateway**: triple independent measurement across two bases (flash 10, flash 15 probe 2 592/2 592, flash 16 with live witness) — the gateway routes NBIO `0x038xxxxx` and not the SMU/PSP pages — (src: RASTRO §B M22; `capturas` under `construcoes/47`, `construcoes/52`).
- **M23** — finding on the x86 side any primitive/constant that writes the CO ports `0x01010998`/`0x01010500`: a ~74.7 MB LE census with a positive control found the constants **only inside the SMU body** ⇒ the CO-port emitter is the SMU itself; front A's host leg buried — coordinator census + `construcoes/44-frente-a-skip/out/probe44.txt`.
- **M24** — hunting the dispatch predicate for our PEIMs in the x86 PeiCore or in our image bytes: documented negative **with named class** — the core obeys a boot block installed by the caller per boot; PAD order died with measurement (the dispatching S5 of 16/11 had the identical layout); the 5 gates `cmp dword [X+0xc],0x11` never open. *Supersession chain:* T56 revised the class (the "untouchable BL/ROM" is in fact the **reset image** the BL delivers — in hand), T58 then **named the caller**: the SEC (only type-0x03 of the inner FV) with **mode constant zero** (written by the core itself; zero `0x11` writes in the image) — the offline gate hunt ended; the 3 deaths' cause migrated to the dynamic inputs (byte-state / external-loader return) — T53/T56/T58 (`construcoes/53-predicado-dinamico/`, `56-psp-bl-chamador/`, `58-chamador-inner-fv/`).
- **M25** — a bc250-class message-queue weakness (unmasked ring append → hijacked DMA pointer → arbitrary SMU-RAM write) in our SMU `f4cb81d9…`: **refuted statically** — the dispatcher validates the limit (`0x7b20+fila*2`) **before** indexing (sync doorbell protocol, no host-side append counter); of 32 scaled-store functions found, 29 were already in the closed set and the 3 extras have literal call-sites; the pointer-table setter `0x14514` has 19 all-constant call-sites; the DMA motor guards `ch>7` before store. Lateral info-leak/minor findings L1/L2/L3 recorded as reopening material, not weaknesses — T54 (`construcoes/54-smu-fila/`).
- **M26** — hunting the PeiCore's caller in FFS content: the last four un-swept RAW blobs decoded (default-store NVAR `cef5b9a3…` + three Windows-subsystem DLLs `77840a38/2fab50b8/4ed407ce` — the ASUS Windows OC bridge) with zero core markers ⇒ the flash is 100% swept for the caller — T57 (`construcoes/57-chamador-raw-pe/`).
- **M27** — staging observer CAPs with **multi-variable / multi-KB** `SetVariable` at DXE entry on this AMI board: broke the platform two different ways (A2 hang at POST 61; A3 booted with a dead variable store, owner reflashed RC1) sharing one denominator — 4×8 176 B chunks + Cnt at entry. Proven-safe class (9 flashes then 10 healthy boots): **1 volatile variable ≤ 10 528 B + 16 B NV counter**; *refinement* **M27-estrito**: one volatile var 1 308 B + Cnt at entry boots clean (A4.MIN, flash 21) — (src: RASTRO §B M27; STATUS flashes 18/19/20/21).
- **M28** — any CAP that writes LTSSM/PHY-affecting registers (`LC_SPEED_CNTL`, `LnkCap`, `LnkCtl`, Retrain) before native training: the A19 class (boot stuck, code 36 — the PHY is mask-Gen3 by policy straps); a static blocklist is now embedded in the verify step — RASTRO §F/§L.
- **M29** — "efivarfs mtime proves a per-boot firmware write": **false** — firmware writes don't update mtime as assumed; the flash 26/27 "fresh" log was byte-identical to an older capture (stale). *Supersession:* **M29²** — mtime **does** track per-boot writes after all: the RTC runs 3 h behind the kernel (local read as UTC−3), so the flash-27 mtime was fresh and the observer had run with `proxy:=1 echo=1` — the stale-log conclusion of §BB was right on the verdict for the wrong reason; **M29³** — housekeeping: the workstation froze mid-session (21/11 ~21:13): operate light, no 16 MB diffs in loops — (src: RASTRO §Z/§AB/§BB/§CC).
- **M30** — owner's house rule (decree, 21/11): daily-use machine ⇒ **clean solutions only, no per-boot corruption**; the A27/WIPER (APOB wipe) was built but **never staged or flashed** — archived; `w27.c` kept as a study — RASTRO §JJ (`construcoes/84-wiper-a27-safe/`).

## Part (b) — the closed-door catalog

### F2 — the PSP-kernel message machine is a dead island (T31)
Hypothesis: the strap decision's `id/sel/r3` arrive as a RAM message pumped by a
kernel message machine the x86/host could feed (T24→T30). Test: read-only
disassembly of the whole PSP kernel body e02 (`0x411200..0x420BD0`, directory
`$PSP` @ `0x3f8800`). Measurement: the router has **zero external entries**, the
copy-DMA validator has no host-side entry, there are **zero jumps from e02 to
the drivers module's VA window**, and the host mailbox has no RX in the kernel
⇒ no host-reachable door (`F2-FILA-SEM-PORTA`). Status: closed by RE, phase-1
report. Reopen triggers in the table below (`biosmod_8902_co/RELATORIO-FINAL-8902.md` §2.4; `trabalhos/24`,`30`,`31` + `construcoes/31-verificacao-coordenador/verificacao-c.txt`).

### G1 — the drivers-module ring is internal (T32)
Hypothesis: the "OS" ring of the drivers module (the one remaining door after
F2) accepts host-supplied descriptors (`blx r2` of `[desc+4]` @ `0x46B2A4`).
Measurement: the executed descriptors are **stack-built by the module itself**
(single chain `0x47B816/0x47B8A2 → 0x46B264 → 0x46B8DE → 0x46B33C`); the handler
fields are pc-relative literals (`0x695`@`0x46B288`, `0xFFFFFFE5`@`0x46B900`);
the wanted handler values `0xE019D5`/`0xE01A05` **never occur as a dword
anywhere in the CAP**; the pump `0x46B820` is dead (zero pools, zero callers);
the master pool `0x00E05A11` (`0x46B960`) has no reader and `0x00E05A10` never
occurs in the CAP (the master was never installed) ⇒ zero host-feedable
indirections (`G1-RING-INTERNA`). Status: closed; it was the documented-negative
close of the combo question in phase 1 (`biosmod_8902_co/RELATORIO-FINAL-8902.md` §2.5; `trabalhos/32` + `construcoes/31-verificacao-coordenador/verificacao-32.txt`).

### x86 → SMU data RAM (T33 / M2)
Hypothesis: the SMN aperture reaches the SMU's data RAM, so the CO gate byte
(`ctx+0x14` bit 8) could be poked from x86. Measurement (four links): the
engine windows `0x0326fe00 / 0x03270a00 / 0x0322fe00` (descriptors
`0x1a600/0x1a560`, flags `0x9020`) occur **only inside the SMU's Xtensa body**
(zero in the raw CAP, e02, and the drivers); queue limits read `0x0084` (two
independent readings); the SMU's QCB VA `0x7000` is the very box x86 already
uses (slot 1 `0x03010a40/570/524`); the 17 h SMN map exposes only
mailbox+mirrors. Honest residue: BKDG/PPR unavailable at the time. Status:
**M2-INALCANÇÁVEL**; reopen only with an official AMD document naming an
aperture for `0x032xxxxx` (`biosmod_8902_co/trabalhos/33-smn-ate-ram-do-smu.md` §6; `construcoes/33-smn-smu-ram/`).

### Host mesa command limit `0x84` (T29)
Hypothesis: CO can be installed/used through the SMU task mesa by host-submitted
commands `0x88/0x8d` (T25/T27 had "planted" them). Measurement: both die at the
host-table command limit — limit u16s at `0x7b22/0x7b24` read **`0x0084`** —
and out-of-range submissions get `0xfe` at `0x1153`; the mesa handlers belong to
the PSP-only queue 12; `Ack88=0` was a log ghost, not a response. Status:
front-A host route closed with byte-level verification. Reopen trigger: a
host-addressable queue carrying the mesa handlers, or a pre-UEFI writer of the
PSP box (`biosmod_8902_co/RELATORIO-FINAL-8902.md` §2.3 + §"gatilhos"; `construcoes/29-reperficia-mesa-host/relatorio.md` §5).

### 7306 policy-module swap (T19/T20)
Hypothesis: port the policy module from official 7306 (this board's last BIOS
that took Gen4 unaided — owner fact) into the 8902 base. Test: build + validate
offline (never flashed in this campaign — T19 withdrew it pre-flash, M9).
Measurement: the 8902-era BL demands the **self-anchor**
`sha256(corpo) = 2564305e…` recorded at `$PS1+0xc0` **inside the signed
header**; the 7306 body hashes `4b748e88…` and its anchor field is all-zero ⇒
unmatchable without rewriting a digest in a signed blob (cryptographically out
of reach; policy-fenced anyway). Post-mortem (T20): the era-BL also rejects the
pre-Zen3 RV1 container at slot `0x28` (not a VMR/RV1 tag comparison — zero tag
comparisons in the whole CAP). The F9 + recovery outcome of a same-class swap is
historical (V2 era) and cited as the measured worst case (`biosmod_8902_co/RELATORIO-FINAL-8902.md` §2.2; `construcoes/19-swap-7306/`, `construcoes/20-post-mortem-swap/`; RASTRO §A 19/20, §O).

### QCB replica filtering — the write question closed (A20 / M3, flash 22)
See doc 08 §2 and M3 above: the faithful protocol replica wrote flag/msg/cmd at
both `0x03b10718`/`0x03b1071c` — **nothing echoed**; the decisive CO handshake
echoed `SET(0)=0xFF` (gate closed) while `GET(0)=ACK1` proved the SMU alive, and
the owner's OS run refused CO −22 on 8/8 cores the same boot ⇒ **triple-
measured**: writes are filtered out of the QCB; the PSP native driver uses its
own VA mapping (svc `0x7d`), not SMN. Status: x86→box-12 route does not exist;
the CO gate opens **only** through the signed vetting transaction itself — the
same transaction that writes the strap (`biosmod_8902_co/RASTRO.md` §M; `trabalhos/76-fila12-gate-a20.md`).

### Box-12 / SMU pages / page 0904 (M22 family — flashes 10, 15, 16)
Hypothesis: the message boxes and PSP-peripheral banks are visible (and
writable) through the direct CF8/CFC gateway. Tests + measurements (all with
live controls in the same boot, double decoding): box-12 ternas
`0x03b10700/704/718` all-FF while NBIO decoded (flash 10, M2_FORA); SMU pages
`0x0101/0x0301` + per-core stride TODO-FF, probe perfect at 2 592/2 592 with
`writes=0` (flash 15, A_MORTA); page `0x0904` banks A–F FF/0 with witness
`0x001A43B9` locked (flash 16, PÁGINA_FORA — closing breach B7). Status:
**M22** — the gateway routes NBIO and nothing SMU/PSP; no further CF8-direct
census of these pages (`biosmod_8902_co/RASTRO.md` §B M22; `capturas/20261120-flash1{5,6}/LEITURA.md` under `construcoes/47`, `construcoes/52`).

### Whole-flash clamp-writer census (T49 / M19)
Hypothesis: the writer of `0x03810054` exists somewhere in the flash as code
(literal or computed). Test: full LZMA expansion of both bases — AGESA
16.1 MiB / 3.29 M instructions, inner FV 164 VZL1 / 955 094 instructions,
nested inner2/inner4 — ~48.7 MB unique / ~5.28 M instructions, censused for
dword literals + `movw/movt` synthesis + `[reg+disp ∈ {0x54,58,5c}]` + SMN
cycles. Measurement: **zero hits in both bases**; 38/38 payloads byte-identical
RC1×clean; coordinator's independent re-decode matched sha 38/38 and his own
literal scan of 67 325 391 B also hit zero; APCB identical, NBIFS nonexistent.
Status: the clamp writer never existed as software in this flash (interpretation
caveat: M19-interpretation above — the *window* writer TE is in the flash,
but as a never-loaded/neutralized-gate writer; flashes 35/36 confirmed neither
visible applier is the actor) (`biosmod_8902_co/RASTRO.md` §A 49, §B M19; `construcoes/49-lzma-agesa/`).

### e03 commit unreachable by mailbox (§WW)
Hypothesis: a native e03 (SMU PSP-OS backend) mailbox command commits clean
values (the "e03 has the applier" hope from §SS/§TT). Test: dump the e03
dispatch tables — found to be **image data** (14 queues, 289 handlers,
`*(0xb9c)=0x7070` baked in RAM-init) — and scan for the commit chain.
Measurement: `FUN_000396ec` is **not a handler of any queue** and has no real
caller (its "callers" were literal-pool false-positives) ⇒ the commit chain
(`396ec→3e010→3dd0c→dcc0→ce3c→daac`) is unreachable by mailbox dispatch; a
"native command that commits clean values" does not exist in our current
knowledge. Status: closed as of 22/11 with named residual (exported vector or
dead code); the surviving model is e07 save/restore autocatalysis (`biosmod_8902_co/RASTRO.md` §WW; `analises/13-e03-backend-applier/out/e03_dispatch_tables.txt`).

### SMU queue-overflow weakness, bc250-style (T54 / M25)
Hypothesis: the public `bc250-vcn-research` precedent (ring append overflow →
hijacked DMA-table pointer → arbitrary SMU-RAM write) replicates on **our**
SMU. Test: static audit of the append/dispatch path with three pre-registered
branches (no CAP). Measurement: synchronous doorbell protocol, limit validated
before indexing, no host-side append counter, all setter call-sites constant,
DMA channel guard before store — **FRAQUEZA REFUTADA**; the value-hijack
dimension (TR_TABLE via the legitimate `32444` writer) also died with
measurement (`param_5` is a compile-time zero). Status: B9 dead-with-evidence;
L1/L2/L3 laterals kept as named reopening material (`biosmod_8902_co/trabalhos/54-fraqueza-de-fila-do-smu.md`; `construcoes/54-smu-fila/`).

### PEI dispatch triple death (flashes 12/13/14)
Hypothesis: our PEIMs (W1 → W1-A1 → PEIPROBE) differ from the dispatching native
S5 in some byte-observable predicate (alignment, metadata, GUID, content).
Measurement: three distinct modules, first in APRIORI each, unconditional entry
— all **never dispatched** (NO_STATE, empty PEI log, no HOB), while alignment
(M5), metadata (M6), and even the module-GUID route are eliminated; T53 then
proved the FFS twins: the dispatching S5 of 16/11 has the same layout, and the
gates (`mode==0x11`) never open because the SEC writes mode=0 (T58) ⇒ the
predicate is dynamic (byte-state / external-loader return), not our bytes.
Status: dead-end closed **with named class**; the residual dynamic cause was
never board-measured (observer line closed at A4, doc 08 §5). Full story in
doc 04 §3 (`biosmod_8902_co/RASTRO.md` §A 39–42, 46, 53, §B M5/M6/M24/M26).

### NBIO proxy write = the poison (A26v2, §BB/§CC)
Hypothesis (T39 lineage): writing `0x03810054 := 1` post-30 with echo lifts the
clamp. Measurement (flash 27, the only echo-proven x86 SMN write of the
campaign): `proxy:=1` **echoed 1**, the speed target was masked (`echo 3,3`,
`Cap2=0xe` at hook time), and both roots ran clamped max 8.0 — while on RC1
(skip armed) the same write was ignored and roots ran 16.0. Unified model: the
consumer reacts to **any** Gen4 request (`Setup[0x239]=4` or proxy `:=1`) ⇒
"the request IS the poison"; the W1/A16/A26 class closed, A26v2 never reflash
(`biosmod_8902_co/RASTRO.md` §AB/§BB/§CC; doc 05 §4).

### Policy-closed (not measured — decided)
- **Wiper / APOB corruption (A27)**: built, validated, **never staged or
  flashed**; archived by the owner's clean-solution decree (M30) for a
  daily-use machine; the "poisoned NVRAM/APOB" arc it was meant for was itself
  reinterpreted as "probably a ghost" once the driver-reapplied-clamp model
  landed (§DDD) `(src: RASTRO §JJ, §DDD; HANDOFF-FINAL-20261122.md` §7`).
- **Skip_PSP / boot-done suppression**: forbidden as levers after Gen4 was
  reached — as levers they were already refuted by measurement reuse (T10:
  armed chain + echoed skip did **not** open the CO gate), and the endgame rules
  list them as prohibited on the A28/A32 final line `(src: HANDOFF-FINAL-20261122.md` §7; `biosmod_8902_co/trabalhos/10-frente-a-sv6-boot-done.md`; RASTRO §A 10).
- **Fuse / OTP / authorization state**: never, in any scenario (M11 absolute;
  Flashback does not undo fuses) — the fence survives every reopening
  `(src: RASTRO §B M11; CLAUDE.md limits)`.

## What would reopen each (as stated by the sources)

| door | reopening trigger |
|---|---|
| F2 kernel message machine | a named writer of the router/copy-DMA; a pointer-registration svc `0xE0F7xx`; a host buffer inside the copy-DMA window (RELATORIO-FINAL §gatilhos) |
| T29 mesa / host route | a host-addressable queue carrying the mesa handlers, or a pre-UEFI writer of the PSP box (T29 §5.4) |
| x86→SMU-RAM (M2) | an official AMD document (BKDG/PPR) naming an aperture for `0x032xxxxx` |
| box-12 write (M3) | only a new **class** of emitter reaching the QCB (RASTRO §D A2) |
| clamp writer / microcode (M17–M21) | extracted on-chip NBIO microcode; an AMD service/policy document for Zen3; a dump of another board/vendor showing the active mechanism; APML/hardware access (RASTRO §N/§FFF; HANDOFF-FINAL §3) |
| CO ports / front A host leg (M23, B8) | a named non-CF8 primitive (NBIF77-indirect/APML/new window) — currently zero evidence any exists |
| SMU queue weakness (M25) | a host handler building a DMA descriptor with host-controlled byte `+0x10`; a host write into table `0x14514`; an AMD document naming a message queue in SMU RAM |
| PEI dispatch (dynamic inputs) | board H1/H2-class measurement outside the failed observer class (doc 04 Open questions) |
| signed-module rebuild | AMD private key (RSA-2048/4096 factorization or leak) — none public; "accepting the risk" does not buy it (RASTRO §O) |
| QCB replica / CO gate | the gate opens only via the signed vetting transaction — no offline trigger (RASTRO §N) |

## Open questions

- None of the reopening triggers above was in hand at campaign close (22/11);
  the accepted endgame and remaining low-chance leads are in
  [05-gen4-the-clamp.md](05-gen4-the-clamp.md) §7 and [13-open-questions.md](13-open-questions.md).

## Sources

- `biosmod_8902_co/RASTRO.md` — §A (task index, one-line verdicts), §B (M1–M27 master registry), §D (front A survivors), §F–§O (A16–A21 era, M28, A20/flash 22, rebuild viability), §P–§ZZ (A-series era, erratas), §JJ–§OO (M30, poison arc), §RR–§FFF (PSP chain, e03/e07/TE, M19-interpretation, flashes 34–38) — the registry spine.
- `biosmod_8902_co/RELATORIO-FINAL-8902.md` — phase-1 close: F2/G1 detailed measurements, the four-link swap analysis (`2564305e…`/`4b748e88…`), documented reopening triggers.
- `biosmod_8902_co/trabalhos/29-reperficia-do-caminho-host-da-mesa.md`, `31-e1-mesa-tarefas-e-registro.md`, `32-ring-do-drivers-e-quem-empurra.md`, `33-smn-ate-ram-do-smu.md`, `54-fraqueza-de-fila-do-smu.md`, `76-fila12-gate-a20.md` — owning task specs/verdicts for the catalog entries.
- `biosmod_8902_co/construcoes/31-verificacao-coordenador/`, `33-smn-smu-ram/`, `29-reperficia-mesa-host/`, `19-swap-7306/`, `20-post-mortem-swap/`, `21-corpus-intermediarias/`, `43-mapa-gen4/`, `45-dono-loader/`, `48-a3-bl/`, `49-lzma-agesa/`, `50-diff-7306-7403/`, `51-emul-commit-0904/`, `53-predicado-dinamico/`, `54-smu-fila/`, `56-psp-bl-chamador/`, `57-chamador-raw-pe/`, `58-chamador-inner-fv/`, `84-wiper-a27-safe/` — evidence trees.
- `biosmod_8902_co/HANDOFF-FINAL-20261122.md` — endgame state, §4 closed-by-RE list, §6 M19-errata lesson, §7 surviving rules.
- `biosmod_8902_co/STATUS.md`, `capturas/` — board outcomes (flashes 9–38) underpinning the measured closures.
- Cross-links: [04-boot-timeline.md](04-boot-timeline.md) (PEI dispatch arc), [05-gen4-the-clamp.md](05-gen4-the-clamp.md) (clamp mechanism, aperture map, endgame flashes), [08-smn-probes.md](08-smn-probes.md) (probe designs), [11-build-catalog.md](11-build-catalog.md) (CAP SHAs), [12-timeline.md](12-timeline.md) (chronology).
