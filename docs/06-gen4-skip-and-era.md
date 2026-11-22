# 06 — Gen4 by skip, and the official-BIOS era

## Summary

The clamp described in [05-gen4-the-clamp.md](05-gen4-the-clamp.md) was beaten on
this board once, by **not letting it run**: GEN4-REL1 (sha
`8b19a72945703ffaf61a1f6886d82bc2c70100c0f3004666933ea7ecfcb4074f`) sets the
DXIO `SKIP_PSP` variable to 1 in request 9 so the PSP chipset-vetting exchange
(services `0x1039`/`0x103a`) never fires inside request 30 — the anti-Gen4
strap `0xfffe0084` (`GEN4_DIS`) is then never written — and NOPs the one
"BIOS boot done" call (PSP mailbox command 6) that the PSP otherwise answers
with a sync-flood reset. GPU x16 + M.2 x4 at 16 GT/s were measured on the
board with these two edits (V2 era, 16–17 Nov 2026). The cost is symmetric:
the same vetting is the only event that opens the Curve Optimizer gate, so on
the armed REL1 the SMU refuses CO with `000000FF`. This doc details the skip
mechanism (which module, which bytes, which guards), the SV1→SV6 bisection
that found the boot-done signal, why the refusal is the two-faces-of-one-check
verdict, the official-era context (7306 the last Gen4 BIOS, the 7306×7403
differential, the AGESA corpus), the other V2 attempts at a cleaner path, and
what Gen4-daily actually meant in practice.

## 1. The REL1 "skip" path

### 1.1 What "skip the chipset validation" means, byte by byte

The causal chain, established statically in the SV1 diagnostic and later
confirmed by 8902-era forensics (T8):

- The SMU 56.76 global state machine (`0x3851c`, body sha256 `f4cb81d9…`)
  matches the public DXIO state names: 8 `VETTING`, 9 `GET_VET`, 12
  `NHP_TRAIN` (public knowledge). State 8 sends PSP message 3, state 9 sends
  message 4 and waits for a non-zero reply. **Both sends are skipped when
  context `+0x14` bit 8 is set.** (src:
  biosmod_v2/diagnostics/8902-gen4-skip-vetting-20261116/README.md)
- The host arms that bit: native TE `21BE` (`FUN_09d691c1`) sends request 9
  (`0x22`, `SET_VARIABLE`) with variable `0x0d` — the public DXIO `SKIP_PSP` —
  and **8902 sends value 0**. The SMU router case `0x22` stores bit 0 of that
  value into context `+0x14` bit 8. (src: same README)
- Message 3 is PSP driver service `0x1039` (VA `e0aa74`, driver body sha256
  `2564305e…`, body base `e00100`): chipset challenge/response, selecting the
  row of the ID table at `e16b70`. Message 4 is service `0x103a` (VA
  `e0a9dc`): it applies that row's three policy bytes. The X370 row (`43b9`)
  is `1,1,0,1`; its last byte tail-calls `e03230`, which writes strap index
  `0xfffe0084` = 1 through the index/data pairs `0x090497ac/b0` and
  `0x0904d7ac/b0`, plus eight entries `0xfff0001c..23` = 1 via
  `0x0904901c/20` and `0x0904d01c/20`, and sets bit 21 of `0x09049914` and
  `0x0904d914` (literals at `e03368..e03380`). (src: same README; the
  equivalent in the driver this machine actually loads is function `0x3230`,
  doc [05 §3.2](05-gen4-the-clamp.md))
- SV1's own summary: "The writer of the 4-to-3 capability clamp is now
  identified statically, and it is not in the SMU. It is the signed PSP
  driver, invoked by the SMU on request." (src: same README)

So the skip yields Gen4 **not** by out-writing the clamp but by making the
clamp-issuing leg of request 30 never exist — the strap/policy writes of
`0x103a`'s tail are simply never called (contrast doc
[05 §2](05-gen4-the-clamp.md): with vetting ON, request 30's PSP leg writes
the strap and LinkCap falls 4→3 in the same transaction).

### 1.2 What "the last boot signal" is

Setting `SKIP_PSP=1` alone produced a **reboot loop** (SV1). Bisection
(SV3–SV5, §1.3) found the culprit: at ReadyToBoot the AMD PSP DXE driver
(file GUID `D14EA3F9-8BD2-49A3-A636-C6F6C08037D5`) sends PSP mailbox
**command 6, "BIOS boot done"**, and with vetting skipped the PSP answers by
" derrubando a máquina com um *sync flood*" — "dropping the machine with a
*sync flood*". (src:
biosmod_v2/diagnostics/8902-gen4-release-20261117/METHODOLOGY.md §3.2)

REL1's second module suppresses exactly that one call — in memory only, the
flash content untouched.

### 1.3 The SV1→SV6 bisection (all flashed in the V2 era)

METHODOLOGY §4, verbatim rows (translated):

| Step | Question | Measured answer |
|---|---|---|
| ALL3 | Where does the Gen4 capability vanish? | At request 30, after the PSP vetting |
| SV1 | Does skipping vetting free Gen4? | Reboot loop with Gen4 selected |
| SV2 | Does the link ever train? | Yes: Gen4 x16, boot passes EndOfDxe |
| SV3 | What kind of reset? | Chipset register `0x08000800`: *sync flood* from an uncorrectable error (FCH `S5_RESET_STATUS` at `0xFED803C0`) |
| SV4 | At what point? | During ReadyToBoot processing |
| SV5 | Which module? | A search over three boots points at driver `D14EA3F9` (one marker per driver among 209, two boots suffice) |
| SV6 | Does removing command 6 fix it? | Yes, four consecutive boots in Gen4 |

(src: biosmod_v2/diagnostics/8902-gen4-release-20261117/METHODOLOGY.md §4)

### 1.4 What was actually patched (the release)

`build/C6H.GEN4-REL1.CAP`, SHA-256
`8b19a72945703ffaf61a1f6886d82bc2c70100c0f3004666933ea7ecfcb4074f`, base
`962de598…` (8902 with the Gen4 option already visible for `PCIEX16_1`). Two
modules added to the PEI volume, written only into free padding, everything
else byte-preserved (Setup, DXE volume, PSP directory, NVRAM identical):

- `src/gen4_pei.c` — first entry of the APRIORI list; reinstalls a copy of
  the native request interface and changes **one word of one request**:
  request 9 (`0x22`, var `0x0d`, native value 0, other words 0) forwards
  value 1. Guards, all mandatory: exact request shape; CPUID `00A20F12` and
  AM4 package; the native interface matches this BIOS byte-exactly; the Setup
  rule below. Any guard failing leaves the request untouched.
- `src/gen4_dxe.c` — at EndOfDxe, only if the PEI half says it acted: finds
  the loaded PSP DXE driver image, requires exactly one copy, image size
  `0x75a0`, and three code windows byte-identical to 8902 at `0x1658`,
  `0x171d`, `0x4928`; then overwrites **in memory** the five bytes of the
  call at `0x1731` with NOPs so command 6 ("boot done") is never sent.
- Setup rule: active by default (`Auto` = Gen4); off only when **both**
  `PCIEX16_1` and the M.2 are set to Gen1/2/3; a port set to Gen3 stays Gen3
  by itself; Clear CMOS does **not** disarm it.

(src: biosmod_v2/diagnostics/8902-gen4-release-20261117/README.md;
METHODOLOGY.md §§3, 5)

Board result (same two changes as SV6, then as REL1): PCIEX16_1 **Gen4 x16**,
M.2 **Gen4 x4**, chipset uplink Gen3 (still pinned by native request 38),
Windows and Fedora booted, firmware TPM self-test passed. Not tested:
suspend/resume, `PCIEX8_2`, `PCIEX16_1` on `Auto` observed only indirectly;
the GPU link showed corrected AER errors at Gen4 (front-A reading: "link da
GPU com AER correto `0x30c1` — erros corrigíveis em regime", "GPU link with
correct AER `0x30c1` — correctable errors under load"); one NVIDIA driver
hang in Fedora, cause left open. Only CPUID `00A20F12` is affected — any
other CPU stays native. (src: METHODOLOGY.md §§1, 8;
biosmod_8902_co/frentes/A-gen4-com-skip/README.md)

## 2. Why the skip kills CO/PBO

The same vetting is the only event that opens the SMU's CO gate. The chain,
from the 8902-era forensics (T8) on exactly this base:

> "o PEIM da REL1 envia request 9 (`0x22`/var `0x0d` SKIP_PSP)=1 → router do
> SMU grava bit 8 do dword +0x14 → no request 30 o SMU (SM `0x3851c`) pula as
> mensagens PSP svc `0x1039/0x103a` (o vetting) → o strap `0xfffe0084`
> (`PCIE_GEN4_DIS`) nunca é escrito (por isso o Gen4 vive). O handler SET de
> CO (`26ca8`) tem gate `[7b4c+0x14]!=0 && [146b0+0x40]==0` e responde FF sem
> encaminhar; o gate abre só durante o vetting do request 30 completo — que é
> exatamente a mesma passagem que escreve o strap anti-Gen4. … **request 30
> completo = CO aberto + Gen3; REL1 = Gen4 + CO fechado. Os dois estados são
> as duas metades da mesma chamada.**"
>
> "the REL1 PEIM sends request 9 (`0x22`/var `0x0d` SKIP_PSP)=1 → the SMU
> router stores bit 8 of dword +0x14 → at request 30 the SMU (SM `0x3851c`)
> skips the PSP svc `0x1039/0x103a` messages (the vetting) → the strap
> `0xfffe0084` (`PCIE_GEN4_DIS`) is never written (that's why Gen4 lives). The
> CO SET handler (`26ca8`) is gated on `[7b4c+0x14]!=0 && [146b0+0x40]==0` and
> answers FF without forwarding; the gate opens only during the vetting of a
> complete request 30 — which is exactly the same passage that writes the
> anti-Gen4 strap. … full request 30 = CO open + Gen3; REL1 = Gen4 + CO
> closed. The two states are the two halves of the same call." (src:
> biosmod_8902_co/frentes/A-gen4-com-skip/README.md, "Forense CONCLUÍDA (T8)")

and the phase-1 close:

> "pacote fechado: a mesma verificação que valida o chipset é a que puxa o
> strap, sem entrada host entre elas. Na REL1 (frente A) o pacote é o inverso:
> o caminho que libera Gen4 pula a validação, e o SMU então recusa CO."
>
> "closed package: the very verification that validates the chipset is the one
> that pulls the strap, with no host input between them. In REL1 (front A) the
> package is inverted: the path that frees Gen4 skips the validation, and the
> SMU then refuses CO." (src: biosmod_8902_co/RELATORIO-FINAL-8902.md,
> "Mecanismo conhecido do defeito")

**The measured refusal.** On the V2 handoff's two-state table: with the Gen4
path (GEN4-REL1/CO9, selectors Auto) the GPU ran Gen4 x16 and M.2 Gen4 x4
while "CO9 recebeu `000000FF` ao aplicar via canal normal. O Fedora pediu
`−22` e leu `0` em todos os núcleos" — "CO9 received `000000FF` applying via
the normal channel; Fedora asked `−22` and read `0` on every core". (src:
biosmod_v2/diagnostics/8902-gen4-co-handoff-20261117/HANDOFF.md §1) CO1 had
already shown the mirror image: with native checking, SET goes from refusal to
success **after** call 30; with the REL1 modification armed, SET returned `FF`
in all nine sampled stages. CO9's private-window reads were `FFFFFFFF` 16,000
of 16,000 times over ~20.3 ms while the native SET answered `000000FF` at all
nine stages and GET read 0 — GPU/M.2 Gen4 x16/x4 in the same boot. (src:
HANDOFF.md §5, CO1–CO9 table) Statically, the SMU 56.76.0 per-core adjust
evaluates an authorization condition for the restricted path before forwarding
to the chiplet controller, and the All-Cores route (MP1 `0x36`, a different
handler from per-core's MP1 `0x35`/RSMU `0x0A`) consults **the same
authorization condition** — so menu routes cannot dodge it either. (src:
HANDOFF.md §5, "Menu AMD Overclocking";
biosmod_v2/diagnostics/8902-gen4-co-aod-route-20261117/README.md)

Two honesty notes from the records. First, the refusal belongs to the
**armed** regime only: the same REL1 image with the modification disarmed
(both selectors Gen1/2/3 → fully native flow) accepts CO normally — REVET-P2
on the front-A base recorded CONFIRMA_A 8/8 with echo −22 (flash 6,
reproduced 8/8 at flash 8). (src: biosmod_8902_co/frentes/A-gen4-com-skip/README.md,
"flash 8"; biosmod_8902_co/frentes/README.md table)
Second, the **BDTEST causal separation**: omitting boot-done while keeping the
native check still produced CO with readback `−22` — "perder *boot done*
isoladamente não reproduz a falha de CO" — "losing *boot done* on its own does
not reproduce the CO failure" — pinning the CO refusal on the skip-vetting +
Gen4 combination, not on the suppressed notification. (src:
biosmod_v2/diagnostics/8902-gen4-co-handoff-20261117/HANDOFF.md §3) The later
8902-era check ran the same way: suppressing boot-done as a CO-gate lever was
"refutada por reuso de medição" — "refuted by measurement reuse" (armed chain +
echoed skip does NOT open the gate; T11). (src: biosmod_8902_co/RASTRO.md §A line 10)

## 3. The official era: 7306, 7403, and the corpus scan

Owner-stated empirical fact (repeated here for the era narrative; verdict
quotes in doc [05 §1](05-gen4-the-clamp.md)): 7306 was the last official BIOS
of this board that accepted Gen4 without a workaround — 7403 already did not —
and no official BIOS of any manufacturer gives Gen4 + Ryzen 5000 on
X370/X470 (only X570). (src: biosmod_8902_co/RELATORIO-FINAL-8902.md,
"gatilhos"; biosmod_8902_co/trabalhos/50-diff-7306-7403-alavanca-oficial.md)

The **AGESA corpus scan** (PSPTool, public knowledge; map in
biosmod_8902_co/analises/04-7306/): 7306 = ComboAM4v2PI 1.0.0.3 (Zen2 PSP;
module `0x16590` body `1e44811a`, *without* the strap); 7403..8101 = 1.0.0.x,
**pre-Vermeer** — they do not boot the 5800X3D at all; 8503..8801 = the X3D
era, **strap ON in every one**. The strap-writing function enters the PSP
between 7306 and 7403, in signed module `0x16590` (digest checks). Verdict:
"a janela 'sem strap' predata o Vermeer; a janela 'X3D' já nasceu travada" —
"the 'no-strap' window predates Vermeer; the 'X3D' window was born locked".
(src: biosmod_8902_co/RASTRO.md §N; §A line 17)

The **7306×7403 differential** (T50, `trabalhos/50`, worker
`construcoes/50-diff-7306-7403/`) treated the pair — same board, five days
apart, opposite Gen4 behavior — as a perfect differential. Pinned inputs: 7306
cap sha `f87a7fcfeb85142b576eec61a2cc1251f7f373eab98cbb4265aafb59c02f0422`,
7403 `3e35c6f18787e788129c0907d4e229becfe0be28a614123722e5351369be9da2`. The
V2-era module diff had already counted 2469 identical modules, 115
changed-bytes, 19 changed-metadata, 18 changed-unresolved, 0 added/removed
(biosmod_v2/data/diff/7306-7403.json). Verdict T10-A, accepted with
corrections — **the lever of the official pair is PSP-OS content**:

- 7403 **gains** a whitelist gate keyed on the FCH devid (`ctx+3`), consumed
  at the end of AUTH with a tail-call to a COMMIT that writes the
  `0x0904_90xx/D0xx` register family via `svc 0x7c` (write proven:
  `r0=addr, r1=val, r2=tam`); 7306 has no gate, no consumer, no tail — the
  pool values `0x0904901c/d01c/97ac/d7ac` are zero occurrences in the whole
  7306 CAP, all present in 7403; `svc 0x7c` count goes 53→74 with a
  contiguous cluster in the TAIL. (src: biosmod_8902_co/RASTRO.md §A line 50)
- The **SMU of the pair is byte-identical** (sha `ed15b19b…`, 108,608 B,
  7306@`0x2aa100` == 7403@`0x2b8d00`) ⇒ the lever is not the SMU.
- The two mailbox validators that had looked interesting (`72133706`,
  `841c04a6`) were **excused**: their changed regions (140 B/120 spans and
  153 B/128 spans) differ by exactly −0x40 each — a relink artifact — with
  the validator offsets themselves intact.

**What the diff did not prove**, as recorded: the *direction* of the mechanism
(enable-list vs clamp) was never proven — the worker's own caveat, "lavrada
pelo worker"; and on 8902 the named mechanism was found only in the PSP dir
the report labelled "dir6 INERTE Zen2 0.14.0.43" (module `e14` at CAP
`0x469f00`, 91,536 B, byte-identical RC1×clean; the 24×12 table at `0x480a70`)
and was declared absent from the then-"active" dir1 — a conclusion whose
directory labels were **later reversed by the §DDD re-audit** (the 0.14.0.43
module is in fact the one this machine loads, and its clamp function is
`0x3230`, doc [05 §3.1–3.2](05-gen4-the-clamp.md)). With that correction, the
T50 search-as-flash-content is still closed as M20: censuses of the official
pair (48,475,016 B each × {`0x03810054`, `0x001a43b9`, `0x0904901c`,
`0x0904d01c`}) returned zero, and "quem aplica o clamp no Zen3 rodante é OUTRA
implementação" — "whoever applies the clamp on the running Zen3 is ANOTHER
implementation". (src: biosmod_8902_co/RASTRO.md §A line 50, §B M20)

## 4. V2-era attempts at a cleaner path (pre-skip and beside it)

Full negative ledger: [10-negative-results.md](10-negative-results.md); build
catalog: [11-build-catalog.md](11-build-catalog.md).

| Attempt | Hypothesis → board outcome | Why closed |
|---|---|---|
| native-force | Inject extra native force `0x810 [0,1,4,0,0,0]` (GPU) / `[0,1,4,1,0,0]` (M.2) after completion event `0x0d`. **Flashed**; USB stopped, video apparently failed, recovered by CMOS reset | Force never captured executed; attribution unproven; image rejected (`REJECTED.json`) |
| gpu-only | One extra native node0 `0x810,[0,1,4,0,0,0]`, GPU-only. **Flashed**; capture BMG_0002 proved the force4 request executed and was ACKed, root target/capability/link stayed Gen3 x16; then USB failure, Q-code 22 | "ACK without Gen4" falsifies late speed-forcing as a workaround |
| SV1 | Skip the vetting exchange (request 9 value 1). **Flashed**; reboot loop with Gen4 selected | Loop traced to boot-done (SV3–SV5) → fixed only by SV6 |
| SV2 | Same + observe: does the link train? **Flashed**; Gen4 x16 trained, boot passed EndOfDxe | Reset later in ReadyToBoot persisted |
| SV3 | Name the reset type. `S5_RESET_STATUS` (`0xFED803C0`) = `0x08000800` sync flood | Diagnostic only |
| SV4 | Localize the reset window: during ReadyToBoot processing | Diagnostic only |
| SV5 | Bisect ReadyToBoot handlers (markers, 16→1 per driver, 209 candidates): driver `D14EA3F9` | Diagnostic only |
| SV6 | Remove command 6 → four consecutive Gen4 boots (GPU x16, SSD x4) | Became REL1; kept only with skip |
| secondary-policy | Gate only state 9's secondary op, keeping svc `0x103a`'s head. **Offline only, no CAP built** | Bypass would also suppress the register ops and a conditional svc `0x1037` transaction whose necessity for chipset/USB/boot is unresolved |
| patch-investigation | Find the clamp instruction inside SMU 56.76.0 (CAP `0x421400`). **Offline only** (`firmware_executed: false`) | `initial_capability_clamp_instruction_identified: false`; NOPping `0x308` forbidden |
| capability-path | A host-side UEFI pre-training op for capability independent of speed. **No CAP prepared/deployed** | Signed payloads excluded (no signing path); 7306/7403 transplant forbidden; late 0x810 force already rejected |
| A27 "wiper" | DXE that wipes the stale APOB region (SPI `0x101000-0x10e087`) at ReadyToBoot so AGESA regenerates policy from the patched ROM. Built, **never staged, never flashed** | Archived by owner decree **M30**: "vamos buscar soluções limpas e o mais próximas de uma nativa o possível, que seria uma x570" — "we'll seek clean solutions, as close to native as possible, which would be an X570"; no per-boot corruption on a daily machine |
| boot-done as lever | (post-M30 re-test of SV6's knob for the CO gate) | Ruled out by measurement reuse (T11) and banned by the standing house rule "sem wiper, sem SKIP_PSP, sem tocar boot-done" — "no wiper, no SKIP_PSP, no touching boot-done" |

(src: biosmod_v2/diagnostics/8902-gen4-native-force-20261116/{README.md,RESULT.md,REJECTED.json};
8902-gen4-gpu-only-20261116/{README.md,RESULT.md};
8902-gen4-secondary-policy-20261116/REPORT.md;
8902-gen4-patch-investigation-20261116/README.md;
8902-gen4-capability-path-20261116/PATCHABILITY.md;
biosmod_8902_co/RASTRO.md §II/§JJ (M30), §A line 10, line 971 rule block;
METHODOLOGY.md §4 for SV1–SV6)

## 5. What "Gen4 daily" looked like

In the V2 era GEN4-REL1 was literally the usage release: the handoff's
pendrive table lists `C6H-RC1.CAP` — "GEN4-REL1, **release de uso**" — "release
for use" (src:
biosmod_v2/diagnostics/8902-gen4-co-handoff-20261117/HANDOFF.md §1). In the
8902 campaign the same image is the front-A anchor, kept on the pendrive as
`C6H.CAP.ANCORA-RC1-8b19a729` and marked "NUNCA sobrescrever" — "NEVER
overwrite" (src: biosmod_8902_co/RELATORIO-FINAL-8902.md decision table;
biosmod_8902_co/frentes/A-gen4-com-skip/README.md "Ativos").

Because the two halves never coexist, the accepted steady state is a **flip
regime, one flash apart**:

> "Regime permanente: **RC1 (Gen4) ↔ B2/REVET-P2 (CO −22 8/8), 1 flash de
> alternância** — ambos provados em placa."
>
> "Steady regime: RC1 (Gen4) ↔ B2/REVET-P2 (CO −22 8/8), one flash to switch —
> both proven on the board." (src: biosmod_8902_co/RELATORIO-FINAL-8902.md,
> Adendo final item 3)

The final position for a single-BIOS setup is that Gen4 is **excluded**: the
combo was declared documented negative on both fronts (front A closed at T29;
front B at T32), and the endgame verdict of doc
[05 §7](05-gen4-the-clamp.md) makes it structural, not incidental. Daily Gen4
exists only as one of two images on the shelf, selected by which feature the
day calls for.

## Open questions

1. REL1's own first-boot log was never re-captured in the 8902-era records;
   all REL1/SV6 board readings quoted here come from the V2-era files. The
   `0x30c1` AER figure appears once (frentes/A README) and was not
   re-instrumented.
2. Whether `PCIEX8_2` reaches Gen4 under the skip was never tested (METHODOLOGY
   §8), and `PCIEX16_1` on `Auto` was only observed indirectly through the M.2.

## Sources

- `biosmod_v2/diagnostics/8902-gen4-skip-vetting-20261116/README.md` — SV1
  static map: SMU DXIO states, SKIP_PSP request 9, svc `0x1039/0x103a`,
  strap literals, armed guards.
- `biosmod_v2/diagnostics/8902-gen4-release-20261117/README.md` — GEN4-REL1
  release: image sha, the two modules, Setup rule, status.
- `biosmod_v2/diagnostics/8902-gen4-release-20261117/METHODOLOGY.md` — full
  PT methodology: result table, the two patches, SV1–SV6 bisection, build
  recipe, limits (AER, NVIDIA hang, PCIEX8_2).
- `biosmod_v2/diagnostics/8902-gen4-co-handoff-20261117/HANDOFF.md` — V2
  limits/history: two-state table, pendrive image SHAs, CO1–CO9 outcomes,
  BDTEST causal separation, AOD/All-Cores authorization condition.
- `biosmod_v2/diagnostics/8902-gen4-native-force-20261116/` — native force
  attempt (README/RESULT/REJECTED).
- `biosmod_v2/diagnostics/8902-gen4-gpu-only-20261116/` — GPU-only late force
  (README/RESULT; BMG_0002 ACK-without-Gen4).
- `biosmod_v2/diagnostics/8902-gen4-secondary-policy-20261116/REPORT.md` —
  state-9 gate-offline study and its unresolved svc `0x1037` dependency.
- `biosmod_v2/diagnostics/8902-gen4-patch-investigation-20261116/README.md` —
  SMU static RE, clamp instruction not found.
- `biosmod_v2/diagnostics/8902-gen4-capability-path-20261116/PATCHABILITY.md` —
  editable-surface table; 7306/7403 transplant forbidden; no CAP deployed.
- `biosmod_v2/diagnostics/8902-gen4-rel1-bdtest-20261117/build/validation.json`
  — offline revalidation of the REL1 patchset (never flashed; board evidence
  inherited from SV6).
- `biosmod_8902_co/frentes/README.md` — two-front master map (A skip / B clean).
- `biosmod_8902_co/frentes/A-gen4-com-skip/README.md` — front A: T8 causal
  chain for `000000FF`, "two halves of the same call", REVET-P2 CONFIRMA_A,
  anchor assets.
- `biosmod_8902_co/RELATORIO-FINAL-8902.md` — decision table (anchor
  `C6H.CAP.ANCORA-RC1-8b19a729`), defect mechanism, Adendo final (flip regime).
- `biosmod_8902_co/RASTRO.md` — §A index (lines 07/10/17/50), §B M20, §II/§JJ
  (A27 wiper, M30 decree, house rules), §N (campaign close, AGESA map).
- `biosmod_8902_co/trabalhos/50-diff-7306-7403-alavanca-oficial.md` — T50
  task spec: pinned 7306/7403 SHAs, V2 module-diff stats, question and
  termination criteria.
- `biosmod_8902_co/trabalhos/37-sonda-nbio-frente-b.md` and
  `biosmod_8902_co/HANDOFF-FINAL-20261122.md` — cross-checks on the RC1-vs-clean
  proxy reading (`0x03810054` = 1 on RC1 vs `0x001A43B9` clean).
