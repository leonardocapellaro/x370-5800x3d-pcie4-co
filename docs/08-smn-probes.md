# 08 — SMN probes: the instrumentation campaign

## Summary

Every self-built observer and writer that touched the System Management Network
(SMN, reached from x86 through the `0xCF8/0xCFC` PCI config-address/data pair)
or the NBIO windows, what each was built to answer, its pre-registered
prediction branches, and what the board actually said. The campaign ran read-only
DXE probes in flashes 9–11 and 15–16, an OS-runtime service, one echo-proven
proxy write, and an observer family (flashes 14, 17–21) whose crashes produced a
platform rule (M27). The practical artifact for future researchers is the
reachability map in the last section. Board mechanics of the clamp itself are in
[05-gen4-the-clamp.md](05-gen4-the-clamp.md); PEI dispatch (why our PEIMs never
ran) is in [04-boot-timeline.md](04-boot-timeline.md) §3.

## 1. SMN transport and the safety rules we adopted

The x86→SMN gateway used everywhere in this campaign: write the SMN address to
the config-address port with bit 31 set (`CF8 = 0x80000000 | address`), read the
result from `CFC`. In NBIO terms the gateway is register `00:00.0+0x60` (index
latch, `CF8 = 0x80000060`) with data at `+0x64` (`CF8 = 0x80000064`), dword
aligned; one read costs 5 `IN` + 6 `OUT` port operations (the cycle re-reads and
restores the previous latch value) `(src: biosmod_8902_co/trabalhos/37-sonda-nbio-frente-b.md; trabalhos/35-sonda-read-only-caixa-12.md §7)`.

House rules, enforced in source and asserted by host-side mock suites that flag
*any* `OUT` to `0xCFC` while `CF8` points at the data window:

- **Never write the data window.** `OUT` to `0xCFC` occurs only inside the
  index-latch cycle (`CF8 = 0x80000060`); the data window (`0x80000064`) is
  `IN`-only, audited line by line. (An early spec wording "never `OUT` to
  `0xCFC` at all" was self-contradictory — the latch cycle itself `OUT`s — and
  the accepted reading is "never a *data* write in the `0x64` window.")
  `(src: biosmod_8902_co/trabalhos/38-sonda-viva-l1-automatica.md §"io.h" + "Desvios ACEITOS")`
- **Save/restore the index register** (`CF8` and the `+0x60` latch) on every
  path including errors and signal handlers `(src: biosmod_8902_co/trabalhos/38-sonda-viva-l1-automatica.md)`.
- **`writes_attempted == 0` sentinel** in every read-only probe: the module
  exits reporting its own write count, and the harness checks it; all probes
  honored `writes=0` on the board.
- **No mailbox, MMIO, ECAM, strap, fuse/NVRAM state writes** from probes —
  reads of the SMN windows only, plus the probe's own logging variables.
  `(src: biosmod_8902_co/trabalhos/35-sonda-read-only-caixa-12.md §"ZERO ESCRITA DE DADO")`
- Every negative required **live controls in the same boot** (a known-alive
  NBIO witness + double decoding): "reads FF" alone is not proof of absence —
  the "unclaimed = FF" premise false-fired in flash 10 (negative control
  `0x03b10ff0` read 0, not FF) `(src: biosmod_8902_co/RASTRO.md §A flash 9; §B M22)`.

## 2. Box-12 family probes (flashes 9–10)

**SMN12-A1** (task 35, flash 9, base RC1 `8b19a729…`) — read-only DXE via CF8/CFC
of the PSP "box-12" message window `0x03b10700..073c` plus mirror `0x03010700`
and negative control `0x03b10ff0`; volatile variable `BiosmodSMN12`; anti-write
flag; predictions P1 (region decodes) / P2 (FF) / P3 (probe dead). Question: can
x86 see/replicate the message box whose handler `0x1dee4` (cmd `0x0a`) opens the
CO gate unconditionally? Board: **P1-decoded-but-FF** — the region decoded, but
the terna `700/704/718` read all FF while NBIO decoded elsewhere, and the
negative control read 0. So terna ≠ QCB state, and the earlier assumption
"unclaimed reads FF" died. CAP sha `c330209b…`
`(src: biosmod_8902_co/trabalhos/35-sonda-read-only-caixa-12.md; RASTRO.md §A line 35, §L)`.

**SMN12-A2** (task 36, flash 10, base RC1) — a full read-only map in three
blocks: page `0x03b10000..0ffc` (1024 dwords) + NBIO inventory
`0x03810000..00fc` + family `0380/0382/0383/0384/0385`; 1 168 readings; slot
`BiosmodSMN12_A2` (BS|RT) + NV counter 16 B; branches M1 (terna ≈ live row ⇒
write phase authorized) / M2 (terna in FF zone ⇒ route dead) / M3 (dead probe ⇒
diagnostic). Board: **M2_FORA** — terna all-FF with NBIO alive
(`0x03810054 = 1` on RC1; the `0x0381` block decoded 62/64), reads double-checked
(embedded == coordinator's decode), `writes=0` honored ⇒ **the x86→box-12 route
does not exist** (negation-final for the software leg of front A; M22 later
extended it to all SMU/PSP pages). CAP sha `4c89b093…`
`(src: biosmod_8902_co/trabalhos/36-sonda-a2-mapa-do-aperture.md; RASTRO.md §B M22)`.

The write question stayed open until **A20/GATE12** (flash 22): a faithful
replica of the box protocol (flag:=0, msg:=0, cmd:=`0x0a` at both `0x03b10718`
and `0x03b1071c`, poll) — **no write echoed** (flag/msg/cmd read back FF;
`71c` read back 0 = idle value, not an echo), decisive echo `SET(0)=0xFF` with
`GET(0)=ACK1` the same boot, and the owner's OS test refused CO −22 on 8/8 cores
⇒ **M3 triple-measured** (no DXE echo + SET(0)=FF in DXE + CO refused in OS):
the QCB is filtered from x86; the PSP native driver reaches the box through its
own VA mapping (svc `0x7d`), not through SMN
`(src: biosmod_8902_co/RASTRO.md §M flash 22; trabalhos/76-fila12-gate-a20.md)`.

## 3. NBIO block probes (flashes 10–11) and the runtime service

**NBIO-B1** (task 37, flash 11, base clean `962de598…` — a test that does not
cost CO) — a 148-address read-only map of `0x03810000..00fc` + family
`0380/0382/0383/0384/0385` + mailbox controls; branches W_VIVA / W_MORTA /
W_PARCIAL / PRIM. Board: **W_VIVA** — clamp witness `0x001A43B9` alive under
chipset-check ON (`+0x04=0x4000cc60`, `+0x54=0x001A43B9`, `+0x58=0x12210000`,
`+0x5c=0x43001400`); mailbox controls `0/1/0/8` identical RC1↔clean;
`writes=0` honored; 62/64 of the `0x0381` block decoded (CAP sha `0b688ea4…`)
`(src: biosmod_8902_co/trabalhos/37-sonda-nbio-frente-b.md; RASTRO.md §A line 37)`.

**VIVA-L1** (task 38) — the same 148+4 addresses at **OS runtime**, a systemd
`oneshot` service installed by the owner (single sudo step) reading SMN with the
same CF8 primitive; kill-switch = presence of
`/etc/biosmod/VIVA-L1-AUTORIZACAO.txt` with an embedded sha256 (delete it and
the service refuses to run); logs under `/var/log/biosmod`; final binary sha
`f26ddace…` (a prior `7bce127a…` embedded an authorization text the coordinator
had to correct — ASRock→ASUS CH6, Ryzen 5→7 — and fully revalidated)
`(src: biosmod_8902_co/trabalhos/38-sonda-viva-l1-automatica.md)`.
First boot read (boot #5): **clamp block 64/64 identical DXE→OS in the same
boot** (witness `0x001A43B9` locked), mailbox counters moved `0/1/0/8 → 5/fd/0/2`
(normal traffic), family `0380` counters free-running ⇒ the hypothesis "request
30 rewrites the block between DXE and OS" died (M10)
`(src: STATUS.md boot #5 block; RASTRO.md §B M10)`.

## 4. The write attempts

- **W1 / W1-A1 PEIM (tasks 39/40, flashes 12/13)** — post-check write
  `0x03810054 := 1` once, post-request-30 / pre-training, with echo, plus
  `LnkSta` capture of GPU/M.2; branches `DIAG / W_ESCRITA_MORTA /
  W_ESCRITA_VIVA_G3 / W_ESCRITA_VIVA_G4`. The PEIM **was never dispatched** —
  flash 12 (CAP `9b5a7d7b…`): `PeiValid=3 (NO_STATE)`, empty PEI log,
  `port_ops (0,0)`, `writes_attempted=0` honored; flash 13 (W1-A1, CAP
  `6f5a34e5…`, entry point moved to 16-aligned `0x390`): identical NO_STATE ⇒
  the odd-entry-point hypothesis died with measurement. **No proxy-write verdict
  comes from W1** (dispatch forensics: doc 04 §3) `(src: biosmod_8902_co/RASTRO.md §A 39/40; STATUS.md FLASH 12/13)`.
- **A35 strap re-write (flash 38)** — x86 re-writing strap `0x84 := 0` after
  request 30 via a hook at the native `call memset` (VA `0x9d69976`) into a code
  cave calling the native wrapper `0x9d685d8`. Booted sane; roots stayed max
  8.0 GT/s ⇒ refuted as a lever, and honestly *which* sub-hypothesis it refuted
  was not discriminated (write discarded after vetting / other lock groups
  `0xFFF0001C..23` + bit 21 / one-time sampling / wrong core numbering / no
  proof the cave executed — no exported log). Detail in doc 05 §4
  `(src: biosmod_8902_co/trabalhos/92-a35-strap-regrava.md; RASTRO.md §FFF)`.
- **A26v2 echo-proven proxy write (task 83, flash 27; first boot flash 26)** —
  module wrote `proxy 0x03810054 := 1` and set Setup target to 4. Live log
  (fresh, after the M29² mtime correction): *"proxy:=1 echo=1 SUCESSO, target:=4
  mascarado echo 3,3, Cap2=0xe no hook-time"* — the proxy write **echoed 1**,
  the speed target was masked to 3 on both roots, and the OS showed both CPU
  roots clamped to max 8.0 GT/s. On RC1 (skip armed) the same `proxy:=1` was
  ignored and roots ran 16.0. Unified model: the clamp consumer reacts to
  **any** Gen4 request — `Setup[0x239]=4` **or** proxy `:=1` — so writing the
  proxy was self-defeating: **"the request IS the poison"**; the
  W1/A16/A26 class closed. (First-boot log read from flash 26 was stale — the
  M29 errata chain, see doc 10; efivar mtime discipline.)
  `(src: biosmod_8902_co/RASTRO.md §Z/§AB/§BB/§CC; CAP sha 79d49998…; brutos in capturas/20261121-flash26-A26v2/)`

## 5. The observer family (flashes 14, 17–21)

**PEIPROBE** (task 46, flash 14, base clean) — a PEIM reading the runtime
mediator block `[IDTR.base−4]` + vtable (the dispatch-state owner found by T45),
first in APRIORI, plus DXE `peip_obs` with one SetVariable. Board: the DXE
observer wrote its record (1 312 B, NV, triple decoding agreeing) but the PEIM
never created its HOB ⇒ **NUNCA_DESPACHOU** — the third PEIM dead with content,
GUID and alignment eliminated as the dispatch predicate `(src: biosmod_8902_co/construcoes/46-peiprobe/capturas/20261120-flash14/LEITURA.md; RASTRO.md §A 46)`.

**OBSPEI A1–A4** (task 55 family; observer line closed after A4) —

| build | flash | design | board result |
|---|---|---|---|
| A1 (CAP `21da0f78…`, module `1b8bb67c…`) | 17 | read-only DXE: H1 full HOB#0 dump, H2 RAM sweep for the core ctx (signatures generated, ≤192 MB), H4 NVRAM vs defaults bank; volatile 32 512 B log + NV counter | **dispatched** (NV `CNT5` v1, BootCnt=6) but the **32 512 B volatile log died**; hypotheses (a) AMI volatile-store out-of-range, (b) ReadyToBoot never fired — indistinguishable with v1 flags |
| A2 (CAP `02567016…`) | 18 | robust transport: 4 entry-time chunks `BiosmodOBSPEI{0..3}` of 8 176 B (`OBS2` header, per-chunk sha256) + RTB update | **hung at POST 61** — the entry sweep walked type-0 Reserved / type-13 (TSEG/SMM) memory and threw on the real AMI map (the OVMF bench has no such maps — M13); never reflash |
| A3 (CAP `244876ef…`, module `6cbf6282…`) | 19 | sweep fixed (type-guard `kObsAllow[1..7]`, scans deferred to RTB); same 4×8 176 B chunk transport | **booted but corrupted the variable store** (settings did not save, no boot device) ⇒ owner reflashed RC1 (flash 20) ⇒ **rule M27: never multi-variable multi-KB SetVariable at DXE entry** (A2/A3 never reflash); also found D-A3-12 (H4 walk zeroed the `GetNextVariableName` cursor) |
| A4.MIN (`555ddc68…`) | 21 | M27-strict transport: **one** volatile variable 1 308 B + Cnt 16 B, each written once at entry; zero RTB, zero variable walk, zero wide scans | **booted clean** (store alive, SetVariable rc=0×2, Fedora up) ⇒ safe class proven (≤1 volatile var ≤ 10 528 B + Cnt 16 B at entry — 10 healthy boots); measurements: `PEIM_HOB_ABSENT` (4th entry death) + `CTX_GONE` (core ctx does not survive into the DXE-visible TemporaryRam window) ⇒ **observer-DXE line closed** + `SEC_LIST_READ`: the final PPI list @`0x09fff74c` is assembled at runtime as an exact 32/32-dword copy of the static block @`0x09fff774` |

`(src: biosmod_8902_co/RASTRO.md §A line 55 (flashes 17–21, errata chain), §B M27; STATUS.md; construcoes/55-obspei/, 59-obspei-a4-min/)`

Follow-on OBSPEI variants were prototyped under `construcoes/60..64` but the
observer line was closed by A4's criterion; the dispatch residue moved to
zero-flash static forensics.

## 6. V2-era probes (predecessor campaign, 17 Nov) — one line each

| probe | what it tested | outcome |
|---|---|---|
| CO1 `b61630ef…` | when does the SMU stop accepting a CO offset | `0xFF` reply to "set offset" until request 30 + 1 |
| CO2 `7605d8b9…` | fix candidate: send the install message post-30 | message 10 sent after 30; offset still `0xFF` at every stage |
| CO3 `a3b86fa8…` | BIOS use of the PSP→SMU mailbox via PCI pair `60/64` | diagnostic; window not the native one |
| CO4 | feasibility review | native access uses pair `B8/BC`; box unmeasured on that path |
| CO5 | Ghidra review, no image | menu CO uses the same blocked handlers — no second door |
| CO6 | keep vetting, clear `GEN4_DIS` before continuation | built, **never flashed** |
| CO7 | strap selector + byte write | selector `0x84` selected on both pairs (PCI `60/64`); data read `FF`/`FFFFFFFF`; CO worked (−22), GPU/M.2 stayed Gen3 |
| CO8 | SMN via native service `EA335` (pair `B8/BC`) | controls valid, strap data `FFFFFFFF` on both pairs |
| CO9 | mailbox revisit via native access | no new strap write; `FF` again |
| CO10 / CO10b | observe native strap selection; export recovery | CO10 variable lost (PEI→DXE HOB-copy relocation); CO10b ran: Gen3, −22 on 8 cores, strap index/data observed |

`(src: biosmod_v2/diagnostics/8902-gen4-co{1-probe,2-unlock,3-mailbox,4-feasibility,5-ghidra,6-strap-revert,7-strap-byte,8-native-smn,9-native-mailbox,10-native-observer,10b-export}-20261117/README.md and co{6,7,8,9,10,10b}-result-*/README.md; full CAP catalog: [11-build-catalog.md](11-build-catalog.md), chronology: [12-timeline.md](12-timeline.md))`

The V2 SONDA1–5 writes into the PCIe mirrors `0x118xxxxx` (no echo) and the
REVET read-only proxy probe (first reader of `0x03810054`) predate this
campaign's CF8 discipline; M4/M5 in doc 10 carry their verdicts.

## 7. SMN reachability map (the practical artifact)

| window | reachable/readable via CF8/CFC | writable from x86 | evidence |
|---|---|---|---|
| NBIO `0x038xxxxx` (proxy `0x03810054`, witness `0x001A43B9`, family `0380–0385`) | **YES, alive** on both bases | **YES** — echo-proven x86 SMN writes exist (`proxy:=1` echoed 1: the unnumbered W1-A15/A16 runs, then flash 26/27) — and they are self-defeating (the request itself is the clamp trigger) | flashes 10/11, boot #5 (RASTRO §A 36/37; §BB) |
| box-12 QCB `0x03b10700/704/718/71c` + mirror `0x03010700` | **NO** — all FF (`710/71c` read 0 = idle) | **NO** — replica writes did not echo (flag/msg/cmd → FF; `71c` read back idle 0) | flashes 9/10 + flash 22 write test (M3 triple, M22) |
| SMU data pages `0x0101_xxxx` / `0x0301_xxxx` | **NO** — all-FF (probe 2 592/2 592, echo 100%) | untestable; the CO-port emitter is the SMU itself (constants occur only inside the SMU body) | flash 15 (M22/M23) |
| PSP-peripheral page `0x0904_xxxx` | **NO** — FF/0 with live controls in the same boot | not tested (nothing visible to write) | flash 16 (M22; breach B7 closed) |
| SMU-RAM DMA/MMU windows `0x0326fe00 / 0x03270a00 / 0x0322fe00` | **NO** — these addresses exist only inside the SMU's Xtensa body (zero occurrences in raw CAP, e02, drivers) | no route (M2, four-link proof) | task 33 (`construcoes/33-smn-smu-ram/`) |
| strap selector/data window (V2 era) | selector selectable; **data read `FF`** via both PCI `60/64` and native `B8/BC` | writes attempted without effect | V2 CO7–CO9 (`biosmod_v2/diagnostics/8902-gen4-co7..9-*`) |
| PCIe config mirrors `0x118xxxxx` (V2-era SONDAS 1–5) | (mirror, not SMN) | writes landed **without echo** ⇒ never a lever | M4 (trabalhos/03–05) |

Honesty rule attached to the map: a row may only be called dead when the same
boot shows live controls decoded twice (the flash-10 false-fire of
"unclaimed = FF" is the cautionary case).

## Open questions

- Whether `0x03b109c4..9d8`-style payload windows vs the submit/ring registers
  (`0x03b10570/574/0524/0a40`) split differently for x86 — two register lists
  circulate in our sources (doc 04 §Open questions); reconcile before reuse.
- The residual PEI-dispatch cause (dynamic byte-state vs external loader return)
  was left unmeasured when the observer line closed; see doc 04 and doc 13.

## Sources

- `biosmod_8902_co/RASTRO.md` — §A task index (lines 35–40, 46–47, 52, 55–58, 62), §B M4/M10/M22/M23/M27, §L/§M (A20), §Z/§AB/§BB/§CC (A26v2 + M29 chain), §FFF (A35) — master verdicts for every probe here.
- `biosmod_8902_co/trabalhos/35-sonda-read-only-caixa-12.md`, `36-sonda-a2-mapa-do-aperture.md` — SMN12 A1/A2 specs, predictions, validation logs.
- `biosmod_8902_co/trabalhos/37-sonda-nbio-frente-b.md` — NBIO-B1 148-address map spec + W_* branches.
- `biosmod_8902_co/trabalhos/38-sonda-viva-l1-automatica.md` — VIVA-L1 runtime service: io rules, kill-switch, install, accepted deviations.
- `biosmod_8902_co/trabalhos/46-sonda-pei-so-leitura.md`, `47-sonda-portas-smu-frente-a.md`, `52-sonda-pagina-0904.md` — PEIPROBE, SMU101-A1, PG0904 specs.
- `biosmod_8902_co/construcoes/46-peiprobe/capturas/20261120-flash14/LEITURA.md`, `construcoes/47-smu101-sonda/capturas/20261120-flash15/LEITURA.md`, `construcoes/52-pagina-0904/capturas/20261120-flash16/LEITURA.md` — board readings for flashes 14/15/16.
- `biosmod_8902_co/trabalhos/39-patch-w1-proxy-unclamp.md`, `trabalhos/40-w1-a1-entry-alinhada.md`, `trabalhos/83-target4-a26v2.md`, `trabalhos/76-fila12-gate-a20.md` — W1/W1-A1, A26v2, A20 write experiments.
- `biosmod_8902_co/trabalhos/92-a35-strap-regrava.md` — A35 strap re-write (request table, outcome).
- `biosmod_8902_co/STATUS.md` — flash 9–13/17–21 blocks, VIVA-L1 boot #5, OBSPEI recovery sequence.
- `biosmod_v2/diagnostics/8902-gen4-co1-probe-20261117/` … `8902-gen4-co10b-export-20261117/` — V2 CO probe READMEs (outcomes quoted above).
- Cross-links: [04-boot-timeline.md](04-boot-timeline.md) §3/§4 (dispatch + probe/phase matrix), [05-gen4-the-clamp.md](05-gen4-the-clamp.md) §4/§6 (proxy semantics, aperture map), [10-negative-results.md](10-negative-results.md) (M-registry).
