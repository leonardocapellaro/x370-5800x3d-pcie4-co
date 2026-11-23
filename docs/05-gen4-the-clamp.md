# 05 — Gen4: the clamp

## Summary

On the Crosshair VI Hero + Ryzen 7 5800X3D with BIOS 8902, PCIe Gen4 on the
CPU roots is removed by a **clamp that lives inside AMD-signed PSP firmware**
and fires during SMU mailbox **request 30**: the same signed transaction that
validates the chipset (the gate Curve Optimizer needs) also writes the
anti-Gen4 strap (index `0x84`, `GEN4_DIS`). The campaign named the clamp
function in the *active* PSP driver (0.14.0.43, function `0x3230`), mapped its
three write groups over the `0x0904_xxxx` register page, proved no x86 code
anywhere in the flash is the writer, proved no official BIOS in the measured
corpus lacks the strap for this CPU generation, and closed every x86 route to
the gate (box-12, SMU pages, page `0x0904`). Two controlled endgame flashes
(A31, A32) and two more (A34 no-POST, A35 Gen3-persists) finished the
editable-flash avenues. Final verdict: the Gen4+CO combo is **excluded by
construction** — the verdict quotes and the full negative ledger are here and
in [10-negative-results.md](10-negative-results.md). The timeline of the
38 boot requests lives in [04-boot-timeline.md](04-boot-timeline.md); the skip
route and BIOS-era detail live in [06-gen4-skip-and-era.md](06-gen4-skip-and-era.md);
the probe campaign in [08-smn-probes.md](08-smn-probes.md).

## 1. The official-policy layer

Two independent layers say the X370 Gen4 cap for Ryzen 5000 is vendor policy,
not accident.

**Owner-stated fact** (the machine's owner, also recorded in the campaign
rules): the last official BIOS of this board that accepted Gen4 without a
workaround is 7306, and no official BIOS of any manufacturer gives
Gen4+Ryzen 5000 on X370/X470 — only X570. Verbatim: *"a última BIOS desta
placa que aceitou Gen4 sem gambiarra é 7306; nenhuma BIOS oficial de nenhum
fabricante dá Gen4+Ryzen 5000 em X370/X470 (só X570)"*
(src: biosmod_8902_co/RELATORIO-FINAL-8902.md, "Fato oficial do dono").

**AGESA corpus check** with PSPTool (public knowledge tool), 7306→8801 on this
board's line: 7306 = ComboAM4v2PI 1.0.0.3 (Zen2 PSP; PSP module `0x16590` body
`1e44811a`, *without* the strap); 7403..8101 = 1.0.0.x, **pre-Vermeer** — they
do not boot the 5800X3D at all (7306's Gen4 freedom belonged to the Matisse
era); 8503..8801 = the X3D era, **strap ON in every version**. The report
closes: *"Nenhuma BIOS oficial desta placa boota o 5800X3D com Gen4 livre — a
janela 'sem strap' predata o Vermeer; a janela 'X3D' já nasceu travada"* —
"no official BIOS of this board boots the 5800X3D with free Gen4 — the
'no-strap' window predates Vermeer; the 'X3D' window was born locked"
(src: biosmod_8902_co/RASTRO.md §N; also RELATORIO-FINAL-8902.md, Adendo final
item 2; task-level index entry T17 "corpus 7306…8801: NEGATIVO — nenhuma
versão oficial sem strap; a função entra no PSP entre 7306/7403 no módulo
`0x16590` assinado (digest bate)" in RASTRO.md §A).

The pair 7306×7403 was also diffed directly: the lever between them is
PSP-OS content, not the SMU (the two SMUs are byte-identical, sha `ed15b19b…`,
108 608 B, 7306@`0x2aa100` == 7403@`0x2b8d00`). The 7403 *gains* a
whitelist gate keyed on the chipset devid (FCH → `ctx+3`) whose tail COMMIT
writes the `0x0904_90xx/D0xx` register family via `svc 0x7c`; in the 7306 CAP
the pools (`0x0904901c/d01c/97ac/d7ac`) are zero occurrences and no consumer
or tail exists. The direction of the mechanism (enable-list vs clamp) was
recorded as **not proven** (worker's own caveat)
(src: biosmod_8902_co/RASTRO.md §A line 50, task T50).

## 2. The clamp as measured on the board: request 30

The physical trace (v2.6 hardware capture, 16 Nov, BMC-side request/packet
log, 38 requests, 10 packet snapshots) brackets the speed cap inside
**request 30** (subcommand `0x308` on node0). Verbatim result table from the
V2-era capture — Link Capabilities before → after request 30, all three CPU
roots simultaneously lose the 16 GT/s bit of Link Capabilities 2:

| CPU root | Link Capabilities before -> after request30 | Link Capabilities 2 |
|---|---|---|
| 00:03.1 GPU | f7733904 -> f7733903 | 180001e -> 0000000e |
| 00:01.1 M2 | f7733844 -> f7733843 | 180001e -> 0000000e |
| 00:01.3 chipset uplink | 00733884 -> 00733883 | 180001e -> 0000000e |

(src: biosmod_v2/diagnostics/8902-boot-trace-v2.6-full-smu-20261116/hardware-capture-20261116/REPORT.md)

Everything else in that interval (vendor/device, capability offsets,
widths, Link Control/Status) stays identical, and the GPU's requested speed
policy stays 4 in every outgoing packet through the final query — the clamp
hits the *root ports*, not the endpoint requests. The same report ties the
boundary to the native SMU mailbox transport and warns that `0x308` is reused
and must not be relabelled a "dedicated disable-Gen4 command"
(src: same REPORT.md, "Sequence and bounded interpretation").

The request timeline around the event (38-request trace; full table in
[04-boot-timeline.md](04-boot-timeline.md)): req 18 = MAPPED (x86 TE PEIM
writes `GEN4_DIS:=0`); req 29 = state VETTING; **req 30 = the resume where
the PSP side writes `GEN4_DIS:=1` and `LinkCap` falls 4→3**; req 31/33 =
PERST events; req 32 = resume; **req 34 = the resume where GPU/M.2 train,
pinning DLL-active at Gen3**; req 35 = DONE — "⇒ o x86 tem o controle duas
vezes entre clamp e treino" ("⇒ x86 has control twice between clamp and
training") (src: biosmod_8902_co/RASTRO.md §EEE; biosmod_8902_co/trabalhos/92-a35-strap-regrava.md).

Because request 30 is one signed transaction that (a) validates the
chipset, (b) opens the CO gate, and (c) writes the anti-Gen4 strap, the two
desired capabilities are welded together. The final verdict, verbatim
(Portuguese) and translated:

> "o combo é **excluído por construção** — a mesma transação assinada que
> valida o chipset abre o gate do CO e escreve o strap anti-Gen4. Sem a chave
> da AMD não existe caminho; todos os caminhos que existem foram medidos."
>
> "the combo is **excluded by construction** — the very signed transaction
> that validates the chipset opens the CO gate and writes the anti-Gen4
> strap. Without AMD's key there is no path; every path that exists has been
> measured." (src: biosmod_8902_co/RELATORIO-FINAL-8902.md, Adendo final)

and the campaign-close formulation: *"o combo Gen4+CO nesta placa é excluído
por construção do firmware assinado da AMD — transitória única (request 30:
valida chipset + abre gate + escreve strap), todas as caixas intermediárias
filtradas do x86 (QCB), todos os caminhos x86 medidos mortos (M1..M28),
nenhuma BIOS oficial sem a exclusão (corpus inteiro + 7306)"* — "the
Gen4+CO combo on this board is excluded by construction of AMD's signed
firmware — single transit (request 30: validates chipset + opens gate +
writes strap), all intermediate boxes filtered from x86 (QCB), all measured
x86 paths dead (M1..M28), no official BIOS without the exclusion (whole
corpus + 7306)" (src: biosmod_8902_co/RASTRO.md §N).

The **skip route** (front A) breaks weld (b)/(c) by suppressing the PSP leg
of request 30 (a bifurcation bit set from Setup), which preserves Gen4 — and
thereby loses the chipset validation the CO gate needs, so the SMU refuses CO
with `000000FF`. Same transaction, two halves; full treatment in
[06-gen4-skip-and-era.md](06-gen4-skip-and-era.md)
(src: biosmod_8902_co/RASTRO.md §A lines 07/13; biosmod_8902_co/frentes/A-gen4-com-skip/README.md).

## 3. The writer: named, located, then fenced

### 3.1 The legacy PSP chain (driver 0.11.0.87) — mapped by RE

The dispatcher `0x1da8` (mailbox switch) in the 0.11.0.87 driver routes
mailbox command `0x1039` to the challenge handler `0x4d28` (doorbell token
`0xFFFE0000`, banks 6/7 at `+bank*0x1000`; the platform id `0x43b9` = X370 is
served to it by the SMU; the anti-Gen4 strap membership comes from hard-coded
lists at `0x6028`/`0x5fd8`, which include the X370 ⇒ clamp), and `0x103a` to
the executor `0x4c90`, which writes strap list A at `0x11180604+i<<20` and
list B^1 at `0x11180600+i<<20` for i=0,1, committing through `svc #0x7c`
(×3) and a tail `svc #0x96` (args 2,0x4d,1). Erratum kept from the source:
"`0x1039/0x103a`" are mailbox command IDs, not service IDs
(src: biosmod_8902_co/HANDOFF-FINAL-20261122.md §4.1; biosmod_8902_co/RASTRO.md §RR, §R).
A later region model attributed the M.2 strap writer to `svc #0x7c`
(`0x13b1_80xx`) and the PEG/GPU strap writer to `svc #0x96`
(src: biosmod_8902_co/RASTRO.md §BB).

Two CAPs edited this driver and flashed: **A21** (sha `6380ac54…`) replaced
3× `svc #0x7c` with `movs r0,#0` at the executor COMMITs `0x4cc6/0x4ce8/0x4d0a`
(flash 23 — booted fine, M.2 root max 16.0 GT/s + CO, PEG 8.0) and **A23**
(sha `707b93c3…`) NOPed 10 halfwords (`movs#2` + `svc96` + `svc7c`×3) in both
identical copies of the driver (bodies @`0x895094` and @`0x713094`) — flash 24
measured 16.0/16.0 + CO (src: biosmod_8902_co/RASTRO.md §P, §Q, §R; §BB table).

**§DDD correction (22/11, the campaign's own re-audit).** The kernel reports
`ryzen_smu: SMU v56.76.0` on all 11 logged boots; matching CAP headers show
that version in PSP directory `0xBC0B0500` (sub1 SMU @`0x421400`) — so this
CPU loads `0xBC0B0500`, while `0xBC0C0140` ("e03", 64.74.0, Cezanne),
`0xBC0C0000` (55.95.0, Renoir) and their companions — including e07
(@`0x86d500`) and the drivers 0.11.0.87 (@`0x889200`/`0x707200`) — "são dos
diretórios de APU Cezanne/Renoir e NUNCA são carregados nesta máquina" ("are
from Cezanne/Renoir APU directories and are NEVER loaded on this machine").
Consequence recorded as an erratum against A21/A23/A28/A29/A31: their
"boot sane, zero effect" was the *expected* outcome, and earlier labels were
reversed ("dir1 ATIVO Zen3" = Cezanne; "dir6 INERTE Zen2" = the active one)
(src: biosmod_8902_co/RASTRO.md §DDD). The tension with the measured
flash-23→24 root changes is listed in Open questions.

The e07 save/restore model (slot 0x98, restore `FUN_0001b780` writing straps
`0x130..0x133` via `0x0904_67ac/67b0` + `77ac/77b0`, token `0xfffe0000`) and
the TE PEIM x86 writer were explored through it — see §5 and
[09-psp-driver-re.md](09-psp-driver-re.md).

### 3.2 The active clamp: driver 0.14.0.43, function `0x3230`

The clamp is **named in the driver this machine actually loads**: PSP module
`$PS1` at CAP `0x469f00`, version `00140043`, whose function `0x3230`:

1. first strobes 8 indices `0xFFF0001C..23` to 1 through command ports
   `0x0904_901C`/`9020` (and mirror `D01C`/`D020`) — semantics not
   identified, flagged "possible lock";
2. then writes the strap doorbell index `0xFFFE0084` to `0x0904_97AC` (and
   `0x0904_D7AC`), reads data at `+4` (= `0x97B0`/`D7B0`), and if data reads
   0 writes **1**;
3. then RMWs **OR bit 21** into `0x0904_9914`/`0x0904_D914` (`orr r1,r0,#0x200000`).

By the published interface of PCIe RSMU straps (illumos/Oxide
`milan/pcie_rsmu.h`: `STRAP_ADDR 0x7ac`/`DATA 0x7b0`, upper word
`0xfffe0000`; header sha `be52be3365d153cc9db32714dbc2d900e3aa09f393dfe43df0b5676e56c09125`,
public knowledge), strap index `0x84` is **`GEN4_DIS`**
(src: biosmod_8902_co/RASTRO.md §DDD; full disassembly in
biosmod_8902_co/analises/16-diretorio-psp-ativo/out/resultado-a28.txt).

The call site is gated: the only caller of `0x3230` is `0xaa62`, requiring
`ctx[3]!=0` (context `0xe16ac0`). `ctx[3]` comes from a 24×12-byte whitelist
table at CAP `0x480a70`: byte 7 (bit 24) is 1 for devids
`43b9/43ba/43bb/43bc/43d0/43d3/43d5/43d8/43ec` and 0 for
`43d1/43d2/43ed/43ee/43ef` — matching the product policy (B550 free;
300/400/A520 without Gen4) and the 7306-absence of T50. X370 (`0x43b9`) is
entries 0 and 23 (`01 01 00 01`, selectors 7/2). The whitelist→gate link was
confirmed by separate disassembly: `ctx[0]/[1]/[3] := entry[5]/[6]/[7]` at
`0xab46..0xab54`, lookup `0xb6f8` matching devid + selector
`[0xe86e78+0x510]` (src: biosmod_8902_co/RASTRO.md §DDD + adendo recibo 113;
biosmod_8902_co/analises/16-diretorio-psp-ativo/out/resultado-a28.txt —
24-row table).

On the x86 side the native strap path is **ECAM**, not CF8/CFC: the TE PEIM's
wrapper `0x9d685d8` bottoms out at `0x9d68b4a mov [edx-0x10000000],eax`
(ECAM `0xF00000B8/BC`), 4 stores per call, zero read/guard; and TE itself
writes `GEN3_DIS(0x7a):=0` and `GEN4_DIS(0x84):=0` at `0x9d662e3`/`0x9d662f1`
(core ≠ 2) — i.e. the x86 firmware asks for *fast* straps early, and the
clamp (`0x3230` or its Zen3 equivalent) wins at request 30
(src: biosmod_8902_co/RASTRO.md §DDD, §EEE adendo recibo 114).

### 3.3 What was ruled out before naming it

The census phase (docs [10](10-negative-results.md)/[08](08-smn-probes.md))
eliminated, with measurements: any x86 decision or writer for the clamp
policy (`M15`, reconfirmed over 7,034,024 B; also `M16` — x86 never even
submits the mailbox), the writer inside the SMU Xtensa body (`M17` — command
`0x1e`(30) there writes a RAM context field `0xb350`, not NBIO), the running
PSP stack (`M18` — BL byte-identical RC1×clean, `5b129195…`; 292-blob census
zero hits), and finally **all expanded flash content** of both bases
(`M19` — ~48.7 MB / ~5.28 M instructions of LZMA-expanded payloads, zero
hits for the proxy or the witness; the only different cluster is the
campaign's own V2 probe container). `M20`/`M21` (mechanism "only in the
dormant dir6" / "no COMMIT emitter in the active PSP-OS") were written with
the directory labels reversed and are superseded in scope by §DDD — the
mechanism *is* in the active driver (§3.2), which is exactly why A34 below
mattered (src: biosmod_8902_co/RASTRO.md §B M15–M21, §A lines 43–51).

## 4. The NBIO "policy proxy" `0x03810054`

The dword at SMN `0x03810054` (witness value `0x001A43B9`) sits in the NBIO
block `0x038xxxxx` — the one family the CF8/CFC SMN gateway *does* route. It
was first read (never written) by V2's REVET probe (`REVET_PROXY_ADDR`,
explicitly read-only — `s_smn(REVET_PROXY_ADDR,0,FALSE)`,
`unclamp_engine.h:139`) and was seen changing by itself mid-boot
(src: biosmod_8902_co/trabalhos/39-patch-w1-proxy-unclamp.md, motivation
block). It distinguishes the two fronts: on the clean base it reads
`0x001A43B9` in DXE, on RC1 (skip armed) `0x00000001`; the V2 CO flip
measured `00000001→001A43B9` afterwards.

- **Read map (T37/NBIO-B1, flash 11):** W_VIVA — `+0x04=0x4000cc60`,
  `+0x54=0x001A43B9`, `+0x58=0x12210000`, `+0x5c=0x43001400`; the 148-address
  read-only map decoded 62/64 in the `0x0381` block; mailbox controls
  `0/1/0/8` identical RC1↔clean; writes=0 honored
  (src: biosmod_8902_co/trabalhos/37-sonda-nbio-frente-b.md).
- **Runtime map (T38/VIVA-L1, boot #5):** the clamp block read **64/64
  identical DXE→OS in the same boot** (witness locked; mailbox moved
  `0/1/0/8 → 5/fd/0/2`; family `0380` counters free-running) — killing the
  hypothesis "request 30 rewrites the block between DXE and OS" (M10)
  (src: biosmod_8902_co/trabalhos/38-sonda-viva-l1-automatica.md).
- **Write attempt W1 (T39):** the CAP that would write `0x03810054:=1` once,
  post-30/pre-training, with echo, never ran: the PEIM was never dispatched
  on two consecutive flashes (flash 12 sha `9b5a7d7b…`: `PeiValid=3
  (NO_STATE)`, empty PEI log, port_ops `(0,0)`, `writes_attempted=0`; flash 13
  W1-A1 sha `6f5a34e5…` with a 16-aligned entry point `0x390`: same NO_STATE,
  so the odd-entry hypothesis died with measurement). **The W1 write never
  executed — no proxy-write verdict comes from W1**
  (src: biosmod_8902_co/STATUS.md, FLASH 12/FLASH 13 blocks).
- **The echo-proven proxy writes are from the A-series lineage** (first on the
  unnumbered W1-A15/A16 runs, then on A26v2). On the official
  base with a module that wrote `proxy:=1` and set Setup target to 4
  (A26v2, flash 27): *"proxy:=1 echo=1 SUCESSO, target:=4 mascarado echo 3,3,
  Cap2=0xe no hook-time"* — the write echoed 1, the speed target was masked
  to 3, and live OS readings showed both CPU roots clamped (max 8.0 GT/s).
  On RC1 with the skip armed, `proxy:=1` was ignored and roots ran 16.0
  (src: biosmod_8902_co/RASTRO.md §CC erratum + §BB table). The resulting
  **unified model**: a consumer reads *any* Gen4 request — `Setup[0x239]=4`
  **or** proxy `0x03810054:=1` — and clamps the CPU roots to Gen3;
  "o pedido É o veneno" — "the request IS the poison". Writing the proxy was
  therefore self-defeating, and the W1/A16/A26 class was closed
  (src: biosmod_8902_co/RASTRO.md §BB).
- **Post-clamp strap rewrite (A35, flash 38):** x86 re-writing strap
  `0x84:=0` after request 30 (hook at `call memset` @VA `0x9d69976` into a
  code cave calling the native wrapper `0x9d685d8`) booted sane but the
  roots stayed max 8.0 GT/s ⇒ refuted as a lever; and honestly, which
  sub-hypothesis it refuted was **not discriminated** — among the
  alternatives listed: the write discarded/locked after vetting, the other
  two groups of `0x3230` (`0xFFF0001C..23`, bit 21) being the real lock,
  the strap sampled only once earlier, wrong core numbering, and **no board
  proof the cave executed** (the CAP exports no log)
  (src: biosmod_8902_co/trabalhos/92-a35-strap-regrava.md; RASTRO.md §FFF).

## 5. Two fronts, and the controlled endgame flashes

The campaign ran two permanent fronts on separate bases, never mixing images
(src: biosmod_8902_co/frentes/README.md):

| front | base | Gen4 | CO |
|---|---|---|---|
| A — skip | GEN4-REL1 / RC1 `8b19a729…` | works (measured 16.0 GT/s) | refused `0x000000FF` — skip omits chipset validation |
| B — clean | 8902 `962de598…` (chipset check ON) | killed at request 30 | works, offset −22 accepted 8/8 (B2/REVET-P2 line) |

(The `962de598…` "clean" base is the official image `04ddae2d0650353e…`
plus a V2-era setup mod that exposed a "GEN 4" option; documented in
biosmod_8902_co/RASTRO.md §P, A22 provenance note.) The accepted steady
state was **RC1 (Gen4) ↔ B2/REVET-P2 (CO −22), one flash of switching**
(src: biosmod_8902_co/RELATORIO-FINAL-8902.md, Adendo final item 3).

The two controlled neutralization flashes of the endgame (both on the
clean/official side, both read by the coordinator) — table and combined
conclusion verbatim from the endgame handoff:

| flash | CAP | patch | boot | CO | roots | conclusion |
|---|---|---|---|---|---|---|
| 35 | A31/E07-RESTORE | 12 B: 6× `l8ui→movi aX,0` in the A/B loads of slot 0x98 of restore `FUN_0001b780` (e07) | sane | −22 ✓ | **8.0/8.0** | restore NOT the applier |
| 36 | A32/TE-UNDO | 4 B: 2× JZ→NOP on the gates of writer `FUN_09d66535` (TE 21be6180) | sane | — | **8.0/8.0** | TE-gate NOT the applier |

> "os DOIS aplicadores flash-visíveis da família 0x0904 foram neutralizados
> em placa, cada um num flash controlado, e o clamp persistiu nos dois ⇒ o
> aplicador do Gen3 está FORA do flash editável testado (microcode NBIO /
> hardware / e03-commit vivo por rota não-testada). Coerente com M19/§WW."
>
> "the TWO flash-visible appliers of the 0x0904 family were neutralized on
> the board, each in a controlled flash, and the clamp persisted in both ⇒
> the applier of Gen3 is OUTSIDE the editable flash tested (NBIO microcode /
> hardware / a live e03-commit via an untested route). Consistent with
> M19/§WW." (src: biosmod_8902_co/HANDOFF-FINAL-20261122.md §2; RASTRO.md
> §BBB/§CCC)

§DDD then hollowed these two negatives: both targets (e07 @`0x86d500`, the
TE-gated `0x12f/0x130` = `DLF_EXCHANGE_EN`/`DLF_HDR_SCALE_MODE` — Data Link
Feature straps, unrelated to speed) sit in never-loaded blobs or unrelated
registers, so "flashes 34/35 negatives say nothing about the clamp" — the
decisive board measurements of the endgame are instead A34 and A35 (src:
biosmod_8902_co/RASTRO.md §DDD).

**A34** (`20f3ba79…`) edited 2 data bytes of the **active** driver's
whitelist (entries 0 and 23, `entry[7]` 01→00, @CAP `0x480a77`/`0x480b8b`) —
the first real test of PSP verification on a loaded blob. Result (flash 37):
**NON-POST**; offline psptool confirmed base `verified(A407)/sha256_ok` vs
A34 `veri-failed(A407)/sha256_inconsistent`. ⇒ "o PSP verifica todo blob que
carrega; 'editar blob AMD assinado carregado' está MORTO COM MEDIÇÃO" — "the
PSP verifies every blob it loads; 'editing a loaded signed AMD blob' is DEAD
WITH MEASUREMENT" (src: biosmod_8902_co/RASTRO.md §EEE, §FFF; board recovery
by FlashBack, owner action).

The poison interlude (flashes 25–34: setting Setup GEN 4 → roots 8.0; 8.0
surviving CLRTC, F5 defaults and reflash; SPI dump proving ROM == the flashed
CAP; APOB rewritten yet policy unchanged) ended with §DDD's reinterpretation:
with the clamp re-applied by the driver every boot, a persistent poisoned
state "deixa de ser necessário (provável fantasma)" — "ceases to be
necessary (probably a ghost)" (src: biosmod_8902_co/RASTRO.md §CC–§OO, §DDD;
arc detail in [10-negative-results.md](10-negative-results.md)). Final board
state of the campaign: **A28** (sha `ec3277b3…`) = Gen3 + CO + PBO exposed,
the "best clean BIOS"; A35 = A28 + the no-effect strap rewrite
(src: biosmod_8902_co/RASTRO.md §KK, §FFF "Estado das frentes").

## 6. What x86 could and could not reach (SMN aperture map)

Three read-only probe families plus write tests drew the map (probe detail in
[08-smn-probes.md](08-smn-probes.md)):

| target | route | result | ref |
|---|---|---|---|
| NBIO `0x038xxxxx` | CF8/CFC direct | **routed, alive** (witness `0x001A43B9`; 62/64 block decoded; writes=0 honored) | flash 10/11 (RASTRO §A 37; trabalhos/37) |
| box-12 message QCB `0x03b10700/704/718` | CF8/CFC | **all FF**; the faithful replica write test (A20/GATE12: flag/msg/cmd `0x0a` at both ports `0x03b10718`/`71c`) **did not echo** — writes are filtered from the QCB; decisive echoes elsewhere: SET(0)=`0xFF` in DXE, SET(−22) refused 8/8 in OS ⇒ **M3 triple-measured: the x86→box-12 route does not exist** | flash 22 (RASTRO §M/§N) |
| SMU pages `0x0101_xxxx`/`0x0301_xxxx` | CF8/CFC | **all-FF** (probe 2592/2592 readings, RC1 base) | flash 15 (RASTRO §A 47, §B M22) |
| PSP-peripheral page `0x0904_xxxx` | CF8/CFC | **FF/0** with live controls in the same boot (witness locked) ⇒ PÁGINA_FORA, not visible to the SMN gateway | flash 16 (RASTRO §A 52, §B M22) |
| CO ports `0x01010998`/`0x01010500` | content census | constants occur **only inside the SMU body** (~74.7 MB expanded, both bases, control-positive) ⇒ the CO-port emitter is the SMU itself (M23) | RASTRO §B M23 |

Induction kept honest by the campaign: FF alone is not proof of absence
(the "unclaimed = FF" premise false-fired in flash 10); every negative above
required double-decoded live controls in the same boot
(src: biosmod_8902_co/analises/03-vetting-straps/PARECER-NOVO-MODELO.md, M3/M22 critique).

Net effect: the one handler that would open the CO gate **unconditionally**
— `0x1dee4` (mailbox cmd `0x0a`, 7 instructions, sets byte
`[0x7b4c+0x14]←1`) — has no emitter the x86 can drive: x86 never submits
mailbox messages (M16), the replica write is filtered (M3), the message boxes
are unreachable (M22), and the SMU's own CO ports are SMU-internal (M23).

## 7. Where the chain stands

The final state, verbatim (src: biosmod_8902_co/RASTRO.md §FFF, 22/11):
"Estado das frentes: B (limpa) = CO+PBO com Gen3 (A28 `ec3277b3…`; A35 =
A28 + regravação sem efeito). A (skip) = Gen4 sem CO (RC1 `8b19a729…`).
Combo: sem caminho fundado restante" — "Front status: B (clean) = CO+PBO
with Gen3; A (skip) = Gen4 without CO. Combo: no founded path remaining."
What was left was explicitly low-chance: offline public-semantics research on
the RSMU registers `+0x01c`/`+0x020`/`+0x914` before any new x86 write CAP;
blind writes into the three `0x3230` groups (violates the echo doctrine);
chipset-devid spoofing (the devid read is done by the PSP, out of known x86
reach). Reopening triggers, documented and outside offline reach: extracted
on-chip NBIO microcode, an AMD service/policy document for Zen3, a dump of
another board/vendor showing the mechanism, APML/hardware access
(src: RASTRO.md §N, §FFF; HANDOFF-FINAL-20261122.md §3).

## Open questions

1. **Flash 23→24 board effect vs §DDD.** The A21→A23 PSP patches (driver
   0.11.0.87 copies) coincided with measured root changes (PEG 8.0→16.0;
   flash 24 = 16.0/16.0 + CO), yet §DDD concludes those drivers never load on
   this machine. §BB itself notes conflicting 23/24 records and lost raw.
   Unresolved: what actually freed Gen4 on flash 24 (before the later
   8.0-everywhere era)?
2. **A35 non-discrimination.** Which of (a)–(e) holds — write discarded vs
   other-group lock vs one-shot sampling vs core numbering vs cave never
   executed on board. The A34 discriminator died (no POST)
   (src: biosmod_8902_co/trabalhos/92-a35-strap-regrava.md).
3. **Semantics of `0xFFF0001C..23` strobes and bit 21 of `0x0904_9914/D914`**
   — "possible lock", not identified (src: RASTRO.md §DDD, §FFF).
4. **PCIe core numbering** used by the x86 strap wrapper (0/1 inferred, not
   measured) (src: RASTRO.md §EEE).
5. **TOS svc-table of 0.11.0.87 never located** — an acknowledged gap in the
   legacy-chain reconstruction (src: RASTRO.md §A line 51, M21).

## Sources

- `biosmod_8902_co/RASTRO.md` — master campaign log (§A index; §B dead-path
  registry M1–M27, with M28–M30 registered later in the log; §N campaign close; §P–§KK front-B/PSP-patch era and the
  poison arc; §BB unified clamp model; §QQ–§CCC e07/TE endgame; §DDD–§FFF
  active-directory correction, A34/A35 results).
- `biosmod_8902_co/RELATORIO-FINAL-8902.md` — phase-1 close and the 21/11
  addendum (A20 triple measurement, AGESA corpus, "excluded by construction"
  verdict).
- `biosmod_8902_co/HANDOFF-FINAL-20261122.md` — endgame map (§1 physical
  state; §2 flashes 35/36 table + combined conclusion; §3 endgame; §4
  RE-closed chain + erratas).
- `biosmod_8902_co/frentes/README.md` — two-front master map (A skip / B clean).
- `biosmod_8902_co/frentes/A-gen4-com-skip/README.md` — front A forensics
  (skip bit, request 9, `0x1dee4` gate).
- `biosmod_8902_co/STATUS.md` — campaign diary; FLASH 12/13 blocks (W1/W1-A1
  NO_STATE readings).
- `biosmod_8902_co/analises/16-diretorio-psp-ativo/out/resultado-a28.txt` —
  active-driver `0x3230` disassembly commentary, caller `0xaa62`, 24-row
  whitelist table.
- `biosmod_8902_co/analises/16-diretorio-psp-ativo/fonte-publica-oxide/sys_io_milan_pcie_rsmu.h` —
  public Oxide header naming strap `0x84` = GEN4_DIS.
- `biosmod_8902_co/analises/14-writer-census/README.md` — writer census
  method and TE candidate.
- `biosmod_8902_co/analises/03-vetting-straps/PARECER-NOVO-MODELO.md` —
  architectural synthesis, surfaces table, FF-is-not-proof critique.
- `biosmod_8902_co/trabalhos/37-sonda-nbio-frente-b.md` — NBIO-B1 read map,
  W_VIVA verdict (flash 11).
- `biosmod_8902_co/trabalhos/38-sonda-viva-l1-automatica.md` — VIVA-L1 runtime
  probe, 64/64 identical DXE→OS clamp block (boot #5).
- `biosmod_8902_co/trabalhos/39-patch-w1-proxy-unclamp.md` — W1 spec
  (proxy write, echo doctrine, pre-registered branches).
- `biosmod_8902_co/trabalhos/43-mapa-gen4-ate-fim-de-treino.md` —
  chain-of-levers map for front B.
- `biosmod_8902_co/trabalhos/52-sonda-pagina-0904.md` — page-`0x0904` read
  probe (PÁGINA_FORA, flash 16).
- `biosmod_8902_co/trabalhos/92-a35-strap-regrava.md` — A35 strap re-write
  build, result, and non-discriminated alternatives.
- `biosmod_v2/diagnostics/8902-boot-trace-v2.6-full-smu-20261116/hardware-capture-20261116/REPORT.md` —
  request-30 LinkCap bracket (three roots, Gen4 bit lost).
