# 12 — Timeline: 14→26 November 2026, day by day

## Summary

Chronology of the campaign on the ASUS ROG Crosshair VI Hero (X370) + Ryzen 7
5800X3D, BIOS 8902: the V2 predecessor work (14–17 Nov), the 8902 campaign
(18–22 Nov) through its task chain T01→T58 and the `A16…A36` build sprint, the
~40 physical flashes, and the close by the owner ("finalizei tudo", 22 Nov).
Dates come from timestamped source blocks (`YYYYMMDD`, `20/11`, "~16:30" in
RASTRO sections and STATUS diary lines). Where a date or flash number is not
stated in the sources and only follows from diary order, it is marked
**(reconstructed)**; everything else is contemporaneous logging.

## Before this campaign: the V2 era (14–17 Nov 2026)

The predecessor campaign (`biosmod_v2`) ran the CO1→CO10b readback series, the
SV1→SV6 skip-vetting experiments and produced GEN4-REL1/RC1 — the only image
with working Gen4 (chipset validation skipped) but CO refused by the SMU
(`0x000000FF`). It closed with a handoff on 17 Nov. Full story: docs 05, 06;
builds: docs 11 §1 (src: biosmod_v2/diagnostics/8902-gen4-co-handoff-20261117/HANDOFF.md).

## 18 Nov 2026 — the campaign opens; policy revision; two fronts

- The 8902 repo opens with a stop-point question: does a demonstrable native
  CO control exist? (src: CLAUDE.md "Ponto de parada"; docs 02).
- Owner policy revision (20261118): byte-patch spoofing and private
  NBIO/SMN interfaces **allowed** as embedded experiments, with absolute
  conditions — echo-reads on every write, never fuses/OTP, no repeat of closed
  experiments (src: CLAUDE.md; docs 02/10 M11).
- **Two-front decision (owner, 20261118):** front A = Gen4 via skip (REL1 base,
  reactivate CO there); front B = clean 8902 with checking ON (keep Gen4, never
  touch the checking). Never mix bases (src: `biosmod_8902_co/frentes/README.md`; docs 05 §5).
- Board day (reconstructed ordering): V2-built SONDA3-V2 / SONDA4-V2 probes
  run — writes into the capacity dwords land **without echo**, pre-30 and
  post-30, while the clamp 4→3 of request 30 is observed live. Closure of the
  probe line: "no write window exists; the PSP handler inside request 30 is the
  only agent that changes those dwords during boot" (src: STATUS.md "Fechamento
  da linha das sondas"; docs 05 §2).
- Numbered flash diary begins: 1 COAPP, 2 SONDA5-V5 (read 16:51), 3 COAPP-R1,
  4 COAPP-B2, 5 REVET-P1, 6 REVET-P2 — the CO half of the solution lands on the
  board (REVET-P2) (src: STATUS.md).

## 19 Nov 2026 — mass closure (T17–T32), era probe, two more owner authorizations

- T17 matrix and the "F2" host-side chain: T24→T32 run one worker at a time and
  close every host-side route to the combo with byte-level proof (kernel message
  machine dead to traffic; PSP driver ring internal to itself) — documented
  negative in both fronts; phase-1 report `RELATORIO-FINAL-8902.md`: CO =
  REVET-P2, Gen4 = RC1, no demonstrable interface (src: RASTRO §A rows 24–32; docs 10).
- Era evidence from the owner: official BIOS 7306 was the last that accepted
  Gen4 without a workaround; no vendor BIOS ever offered Gen4 + Ryzen 5000 on
  X370/X470 (src: CLAUDE.md aditamento 20261119).
- **Owner revision 20261119T03:10Z:** PSP/SMU weakness research **authorized**
  (offline only: published knowledge + our own static RE/emulation/fuzzing;
  live board work still forbidden; signed content untouched; fuses never).
- SWAP7306 flashed (flash 7, reconstructed day): F9 memory storm, FlashBack
  recovery to RC1; withdrawn (src: STATUS.md; docs 15).
- MESA-C1 flashed (flash 8): CO reproduced 8/8 on clean base, Gen3 (src: RASTRO §A row 29).
- **Owner revision 20261119T21:49Z:** automated **read-only live SMN probing**
  authorized (service installed by the owner with one sudo; kill-switch file;
  never writes) → task T38 (src: CLAUDE.md; docs 08).
- Reopen ("vamos reabrir e testar tudo que der", 20261120T01:00Z addendum
  block): T33 (x86→SMU-RAM: **M2-INALCANCÁVEL**), T34 (protocol route: no wire),
  T35 SMN12-A1 (flash 9: decodes but caixa-12 triple reads FF), T36 SMN12-A2
  (flash 10: **M2_FORA** — x86→caixa-12 dead by measurement), T37 NBIO-B1
  (flash 11: **W_VIVA**, witness `0x001A43B9` live), T38 live L1 service
  installed; first boot: clamp block identical DXE→OS ⇒ "the call-30 rewrite
  between DXE and OS" hypothesis dies (src: RASTRO §A rows 33–38).
- Owner reframes: "eu queria um patch, não monitoramento" ⇒ T39/W1 dispatched
  ~20:15 — first attempt to **write** the policy proxy `0x03810054` (src: STATUS.md).

## 20 Nov 2026 — patch attempts, VZL1 mystery, observer saga

- Flashes 12 (W1) and 13 (W1-A1): PEIM **never dispatched** twice — empty PEI
  log despite byte-equivalent insertion; entry-point alignment ruled out
  (src: RASTRO; docs 10 M-registry).
- T41 decodes **VZL1** (it is a header-stripped PE container, not a compressor)
  and lifts the real AMI PeiCore; T42 fails to name the rejection predicate
  (T2-B negative) (src: RASTRO §A rows 41–42; docs 03 §VZL1).
- Owner mode directive 20261120T0600Z: investigate both fronts until every
  breach is exhausted; **RASTRO.md** created as anti-repetition master registry
  (§A tasks, §B dead ends M1–M…, §C live breaches) (src: CLAUDE.md).
- T46 PEIPROBE-A1 → flash 14: NUNCA_DESPACHOU (third PEIM death; PEI gate is
  dynamic, not our bytes). T44 (front A breach map: CO accepted via two SMN
  writes per core, alias `0x0101↔0x0301`) → T47 SMU101-A1 → flash 15:
  **A_MORTA** (SMU pages all FF via direct CF8) (src: RASTRO §A rows 44–47; docs 08).
- T48: no clamp writer in the PSP runtime stack; T49: full expanded-flash scan
  (≈48.7 MB LZMA payloads, 5.28 M instructions) finds **zero writers** of the
  clamp block in either base (M19). T50 diffs official 7306×7403 (the gate
  whitelist appears only in 7403). T51 names the Zen2 COMMIT targets on page
  `0x0904`; T52 PG0904 sonda → flash 16: **PÁGINA_FORA** — page invisible to
  SMN; M22 consolidated (CF8-direct never reaches `0x0101/0x0301/0x0904`)
  (src: RASTRO §A rows 48–52; docs 10).
- T53 (dynamic PEI gate): the dead PEIMs are structural twins of a PEIM that
  *did* dispatch on 16/11 → gate is set by a producer outside every FFS (BL/ROM
  hypothesis); negative-with-named-class, M24 (src: RASTRO §A row 53).
- T54: the publicized `bc250` SMU-queue weakness is **refuted** for our SMU
  (synchronous doorbell protocol, no message queue) — M25 (src: RASTRO §A row 54).
- T55 OBSPEI-A1: validated 19:10, staged 19:42. Owner pause order 18:47 →
  **superseded the same evening** ("REABERTURA"): find a path that serves
  PCIe4 together with PBO/CO by any means. Flashes 17 (A1: log lost), 18 (A2:
  POST-61 hang, jamais reflashar), 19 (A3: store corrupted), 20 (RC1 recovery),
  21 (A4: CTX_GONE — observer line closed) (src: RASTRO; STATUS.md; docs 08 §5).

## 21 Nov 2026 — the A-sprint: from PEI levers to the PSP chain

- 06:00Z block (reconstructed from §F–§M timestamps): W1-A14/A15 packaged with
  native VZL1 dispatch proven — **A15 board dump: proxy write echoed
  (`Proxy54R2B=1`) yet Target Link Speed stayed 3 ⇒ proxy alone refuted**
  (src: RASTRO §F).
- Unnumbered flashes ~12:49–14:41: A16 TARGET_MORTA, A17 CAP2_MORTA, A18
  LC29_CAP2_MORTA, A19 boot-stuck at POST code 36 (unsafe; jamais reflashar)
  (src: RASTRO §G–§K).
- Flash 22 (~16:30): A20/GATE12 — first x86 **write** to the caixa-12 gate:
  GATE_FECHADO measured (src: RASTRO §M).
- Flashes 23–28: A21 PSP patch restores CO −22 and trains M.2 at 16.0 (GPU root
  8.0 — §Q's "Gen4 died" record later corrected by §Z/§BB); A23 gives both
  roots max=16.0 (flash 24, candidate "final BIOS"); A24+GEN4 set clamps to 8.0
  (flash 25 — the "poison" line); A26v2 TARGET_MORTA (flashes 26–27, second one
  a stale-log episode); A23 reflash still 8.0 (flash 28) ⇒ NVRAM/state poison,
  not image (src: RASTRO §U–§BB; docs 05/10).
- Late 21/11 (numbers 29–33 reconstructed as a block; 31–33 partially
  unresolved — see docs 11 discrepancies): A28/G4PBO built and flashed (flash
  32) — PBO visible via 11 front bytes validated on board; XMP retrain boot
  (flash 33, boot at 23:14) still lands Gen3; A27 wiper archived by owner
  decree (M30) (src: RASTRO §AA–§BB).
- A29 (flash 34): glitches, REPROVADA — changing PSP return semantics breaks
  subsystems. This triggers the deep PSP-chain RE of the night (§RR–§YY):
  dispatcher `0x1da8`, challenge `0x4d28`, executor `0x4c90`, e07 save/restore
  slot 0x98, e03 NVM primitive, TE PEIM geometry — all closed by RE (src:
  RASTRO §RR–§YY; HANDOFF-FINAL §4; docs 09).

## 22 Nov 2026 — controlled endgame flashes, erratum, menu unlock, close

- ~04:30 owner **risk decree**: three final experimental CAPs allowed.
  A31/E07-RESTORE, A32/TE-UNDO, A33/COMBO built+verified+staged (src: RASTRO §AAA).
- Flashes 35/36: **both visible appliers neutralized on board, clamp persists
  (8.0/8.0 both roots, CO ok, healthy boots)** ⇒ the Gen3 applier is outside
  the editable flash (NBIO microcode / hardware). A31 becomes the proven
  safety-net CAP (src: HANDOFF-FINAL §2–3; docs 05 §7).
- §DDD erratum: the **active** PSP directory is `0xBC0B0500` — earlier PSP/SMU
  patches (A21/A23/A28/A29/A31) had been hitting unloaded blobs (src: RASTRO §DDD).
- Flashes 37/38 (image order inferred): A34 = NÃO-POST (PSP refuses an edited
  signed driver — the live signature check, measured); A35 healthy, Gen3
  persists (src: RASTRO §EEE–§FFF; docs 09/10).
- Owner asks for the menu work (outside the Gen4 question): **A36/PBO-CO**
  built+verified+staged 22/11 — 37 bytes in FVMAIN unlock native PBO/CO menus;
  flash 39 pending; profile `final_settings_A36.CMO` delivered (src: RASTRO §GGG; docs 07).
- **Owner closes the campaign ("finalizei tudo"), 22/11 ~12:00 handoff:** daily
  BIOS = A28/A23 behavior (Gen3 roots, CO −22 via service, PBO exposed,
  signature alive), recovery = A31; reopening triggers documented (NBIO
  microcode dump, AMD policy doc, another board) (src: HANDOFF-FINAL).
- This case-study repo is the post-campaign publication (22/11).

## Flash log (compact)

| # | Date | Image | Result (one line) |
|---|---|---|---|
| 1 | 18/11 | COAPP | observer alive on clean base |
| 2 | 18/11 | SONDA5-V5 | post-30 writes land **without echo** (16:51 read) |
| 3 | 18/11 | COAPP-R1 | CO refusal logged on REL1 |
| 4 | 18/11 | COAPP-B2 | iteration logged |
| 5 | 18/11 | REVET-P1 | flip attempt 1 (reads only) |
| 6 | 18/11 | REVET-P2 | **CO half works** (documented) |
| 7 | 19/11 (reconstr.) | SWAP7306 | F9 storm → FlashBack recovery; withdrawn |
| 8 | 19/11 | MESA-C1 | CO 8/8 reproduced; Gen3 |
| 9 | 19/11 (reconstr.) | SMN12-A1 | decodes; caixa-12 triple reads FF |
| 10 | 19/11 | SMN12-A2 | **M2_FORA** — x86→caixa-12 dead (final) |
| 11 | 19/11 | NBIO-B1 | **W_VIVA** — policy block live |
| 12 | 20/11 | W1 | NO_STATE — PEIM never dispatched |
| 13 | 20/11 | W1-A1 | NO_STATE again — alignment ruled out |
| 14 | 20/11 | PEIPROBE-A1 | NUNCA_DESPACHOU (3rd PEIM death) |
| 15 | 20/11 | SMU101-A1 | A_MORTA — SMU pages invisible (M22) |
| 16 | 20/11 | PG0904 | PÁGINA_FORA — page invisible (M22) |
| 17 | 20/11 | OBSPEI-A1 | dispatched; volatile log lost |
| 18 | 20/11 | OBSPEI-A2 | POST-61 hang — jamais reflashar |
| 19 | 20/11 | OBSPEI-A3 | store corrupted |
| 20 | 20/11 | RC1 (recovery) | recovery boot |
| 21 | 20/11–21/11 | OBSPEI-A4 | CTX_GONE — observer line closed |
| — | 21/11 am | W1-A15 | proxy echo, target still 3 — proxy alone refuted (unnumbered in RASTRO) |
| — | 21/11 ~13:24 | A16 | TARGET_MORTA (unnumbered) |
| — | 21/11 ~13:47 | A17 | CAP2_MORTA (unnumbered) |
| — | 21/11 ~14:41 | A18 / A19 | LC29_CAP2_MORTA / stuck POST 36 (unnumbered) |
| 22 | 21/11 ~16:30 | A20/GATE12 | GATE_FECHADO (first x86 write to gate) |
| 23 | 21/11 | A21 | CO −22 back; M.2 16.0; GPU root 8.0 |
| 24 | 21/11 | A23 | both roots max=16.0 — "final BIOS" candidate |
| 25 | 21/11 | A24 + GEN4 set | roots clamp 8.0 — poison line |
| 26 | 21/11 | A26v2 | TARGET_MORTA |
| 27 | 21/11 | A26v2 (again) | stale-log episode |
| 28 | 21/11 | A23 (again) | 8.0 persists ⇒ NVRAM/state poison |
| 29–31 | late 21/11 (reconstr.) | *(not resolvable from sources; flash 31 has a recorded menu/16.0 matrix; 30 reads as an SPI-dump event)* | — |
| 32 | late 21/11 (reconstr.) | A28/G4PBO | usable interim; PBO front bytes validated |
| 33 | late 21/11 23:14 | (boot event on A28) | XMP retrain; policy stayed Gen3 |
| 34 | 21/11–22/11 | A29 | glitches — REPROVADA |
| 35 | 22/11 | A31 | healthy; e07 restore NOT the applier; safety net |
| 36 | 22/11 11:54 | A32 | healthy; TE gate NOT the applier |
| 37 | 22/11 | A34 | NÃO-POST — PSP signature check measured |
| 38 | 22/11 | A35 | healthy; Gen3 persists |
| 39 | 22/11 | A36 | pending at log close (menu unlock) |
| 40 | 25/11 | A37 | `43b9`, roots max 8.0 — first boot invalid (upload skipped), post-PSU-cut boot same ⇒ M32 |
| — | 25/11 | A38 | built+staged; readout impossible from the OS (window PEI-only); chipset-firmware line closed (reopened the same evening, below) |
| 42 | 25/11 18:24 | A39 | `43b9`; 8051→OS channel works; `01:8550` holds `1242` ⇒ M33 |
| 43 | 25/11 ~19:35 | A40 | routine ran, probe state lost, no sweep — no verdict |
| 44 | 25/11 ~21:00 | A41 | first page swept, then state destroyed by the interrupt stack — no verdict |
| 45 | 25/11 21:08 | A42 | page-01 sweep complete: known ID register + one hit at `01:58A2..A3` |
| 46 | 25/11 21:46 | A43 (full) | the `58A2` hit is a changing register, not a copy; no write happened; ID `43b9` |
| 47 | 26/11 | A44 | NBIF ID strap, guarded write: `0c:00.0` still `148a` ⇒ M36 |
| 48 | 26/11 | A45 | NBIF ID strap, blind write: still `148a`, SMN control alive ⇒ M37; **campaign closed** |

After the 22 Nov close the owner reopened the campaign twice: on 25 Nov for the chipset-firmware idea
(docs [17](17-chipset-8051-firmware.md), [18](18-chipset-8051-id-hunt.md)) and on 26 Nov for one last general
sweep (static audit ⇒ M35, then the B10 strap test; [docs/19](19-final-sweep-and-closure.md)). Flash 41 is not
recorded as a number in the log `(src: RASTRO §HHH–§WWW)`.

## Open questions (date-related)

- Exact day/number of flashes 29/31 and the exact split of the unnumbered
  21/11-morning W1-A15/A16–A19 runs are not recorded as diary numbers (docs 11
  "Source discrepancies").
- Whether A14 was itself flashed ("A14-proven" vs README "Board-tested: no").

## Sources

- `biosmod_8902_co/RASTRO.md` — master log: §A task index (spine T01–T58), §B M-registry, dated sections §F–§M, §AA–§BB, §RR–§YYY, §DDD–§GGG.
- `biosmod_8902_co/STATUS.md` — contemporaneous diary: probe verdicts, flash order 1–8, policy addenda text.
- `biosmod_8902_co/CLAUDE.md` — owner addenda with timestamps (20261118 policy, 20261119T03:10Z, 20261119T21:49Z, 20261120T01:00Z, 20261120T0600Z, pause/reopen).
- `biosmod_8902_co/HANDOFF-FINAL-20261122.md` — endgame: flashes 35/36 table, accepted state, close.
- `biosmod_8902_co/RELATORIO-FINAL-8902.md` — phase-1 close narrative.
- `biosmod_v2/diagnostics/8902-gen4-co-handoff-20261117/HANDOFF.md` — V2-era chronology and limits.
- `biosmod_8902_co/construcoes/*/README.md` + `capturas/20261120-flash1{4,5,6}/LEITURA.md` — dated build/flash/read records.
- This repo: docs 02 (doctrine), 05 (clamp/fronts), 08 (probes), 09 (PSP chain), 10 (M-registry), 11 (build catalog), 15 (F9 memory).
