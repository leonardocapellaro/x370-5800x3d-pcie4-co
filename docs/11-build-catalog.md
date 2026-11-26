# 11 — Build catalog: every CAP we built

## Summary

This is the complete catalog of firmware images (ASUS `.CAP` files) built across
the two campaign eras: the predecessor "V2" campaign (`biosmod_v2`, 14–17 Nov
2026) and the "8902" campaign (18–22 Nov 2026). For each entry: name, base
image, purpose, SHA-256 exactly as recorded in the research tree, flash number
or staging status, and the board verdict. The campaign ended with A28/A23 as
the accepted daily BIOS (Gen3 roots, working CO, PBO exposed) and A31 as the
proven recovery CAP (src: biosmod_8902_co/HANDOFF-FINAL-20261122.md §3).

**No binaries are published in this repo.** Names and hashes only — the hashes
are the chain of custody, verifiable against the research-tree READMEs. Every
hash below is copied VERBATIM from a source file; none was recomputed here.
Where a source genuinely records no hash, the row says `sha not recorded`.

Naming: `C6H.` = Crosshair VI Hero. Family codes: `CO*` (V2 curve-optimizer
probes), `SV*` (V2 skip-vetting), `SONDA*` (Port. "probe"), `REVET*` (CO flip
patches), `MESA*`, `SMN12-*`, `NBIO-B*`, `W1*`, `PEIPROBE`, `SMU101`, `PG0904`,
`OBSPEI*` (observer family), `W1-A15`, then the `A16…A36` sprint.

## 0. Base images

| Image | SHA-256 (full) | What it is |
|---|---|---|
| Official 8902, untouched | `04ddae2d0650353ec7bafa50a281528791a74694960f2104ac9d53657b0b6bba` | stock ASUS 8902, reference for all diffs (src: biosmod_8902_co/STATUS.md) |
| "962" = official + V2 Gen4 mod | `962de5988e2c06da092ef7f296089b7006cfbdc5f9821641d287e5e21117466b` | the "clean" 8902 base of the 8902 campaign (checking ON, Gen3); base of most probes (src: STATUS.md; docs 05/06) |
| GEN4-REL1 = "RC1" | `8b19a72945703ffaf61a1f6886d82bc2c70100c0f3004666933ea7ecfcb4074f` | V2-era release with chipset-validation skip: Gen4 ×16 GPU + Gen4 ×4 M.2 measured, but SMU refuses CO (`0x000000FF`); the safe anchor of the whole campaign (src: biosmod_v2/diagnostics/8902-gen4-co-handoff-20261117/HANDOFF.md; STATUS.md) |

REL1 module anchors kept for extraction checks: `ba0bce8a3d4de9cb6dcf650b2d7aa0b15c4a672f3194b88b11649cd259228acc` and `3df17e6cf6546f5ad25d099d3606e8ac1e64e9c7d995220b1a9e741405d2ce44` (src: biosmod_8902_co/construcoes/, REL1 anchors).

## 1. V2 era (14–17 Nov 2026) — predecessor campaign

Outcomes here are summarized from the V2 handoff; the full story is in docs 05/06/08 §6.

| Image | SHA-256 (as recorded) | Purpose | Outcome |
|---|---|---|---|
| CO1 | sha not recorded | first CO readback probe | closed CO-readback line (src: handoff table; V2 dir `8902-gen4-co1-probe-20261117` records no SHA-256) |
| CO2 | `7605d8b95846fad1966d997b3c238a9e7f6a27e3d1d994d532033f56178a7442` | CO unlock attempt | closed (src: V2 `8902-gen4-co2-unlock-20261117`) |
| CO3 | `a3b86fa8e2154b950b40a15983806f800decd8b9b2f7e0913f9f6ef7d3dd2562` | mailbox path probe | closed (src: V2 `8902-gen4-co3-mailbox-20261117`) |
| CO6 | `c529fa8f93415a08ae993cdab46f1d597ee87b89f8ea7d95716ccc714984a80e` (dir also records `2564305edb0465a043deab8254d14987385d9b9172f6d9e5d5a650632e3660e6`) | strap revert | strap lever closed (src: V2 `8902-gen4-co6-strap-revert-20261117`; two SHAs in one dir — see discrepancies) |
| CO7 | `82372d4a9133cb210e19ee4aee86e40f7f00ee956210715c821588f536f0a3b1` | strap byte | closed (src: V2 `8902-gen4-co7-strap-byte-20261117`) |
| CO8 | `91f6a8b690b476dab1be9907f89cd93a0c14a54b40e3060ba22e2f15b8d6821c` | native SMN CO | closed (src: V2 `8902-gen4-co8-native-smn-20261117`) |
| CO9 | `77e980d274ecb30fbaf40aa9d91ef725bf79a2d2b38da1a2e0521e9581d3f300` | CO service variant | −22 path established (src: handoff CAP table) |
| CO10 (observer) | `a6b06fd36452b58efa86fcee5d3a2221ef78a74f8f1e7c5031c7b615190ea6ab` | boot-time CO observer | observer pattern proven on board; source of the request-30 capture set (src: handoff CAP table) |
| CO10b | `3ca9f29b71090f3e724b5e3f049377c00f7a15462b5aa808499cc365fee68c40` | observer iteration | −22 read in OS via owner's boot service (src: handoff CAP table) |
| SV1/SV2 (skip-vetting) | sha not recorded | first PSP-skip experiments | origin of the REL1 skip lineage (src: V2 dir `8902-gen4-skip-vetting-20261116`; no SHA in its .md) |
| SV3 | `7b72a7e4d698df78c7f7517fa82943b17f22be6938f9a5e768407959595b7f45` | reset-reason probe | (src: V2 `8902-gen4-sv3-reset-reason-20261117`) |
| SV4 | `6e38958181db8989925af60039a83cac51b2e23b4fb54b617bf8f9592bab39dc` | MCA probe | (src: V2 `8902-gen4-sv4-mca-20261117`) |
| SV5 | `d726a46accdf195ad7dc653dc87240d9822744b37e5138143c0fb0bd8d25c879` | bisect | (src: V2 `8902-gen4-sv5-bisect-20261117`) |
| SV6 | `fd7f60b3f59fa5dc95f7859fb98106c8012f741f8f1f28c3af6deba0a4094dc6` | boot-done probe | (src: V2 `8902-gen4-sv6-bootdone-20261117`) |
| GEN4-REL1 (=RC1) | `8b19a72945703ffaf61a1f6886d82bc2c70100c0f3004666933ea7ecfcb4074f` | release: skip + Gen4 | Gen4 works, CO refused → front A of 8902 campaign (src: handoff) |

## 2. Early 8902 probes and the two solution halves (18 Nov, pre-series + flashes 1–8)

The numbered flash diary starts at 1 = COAPP (src: STATUS.md flash order). The
SONDA3-V2 / SONDA4-V2 runs are V2-built images flashed on the board before /
beside that numbering (src: STATUS.md "linha das sondas").

| Image | SHA-256 (as recorded) | Base | Purpose | Flash / stage | Verdict |
|---|---|---|---|---|---|
| SONDA3 (C6H.SONDA3.CAP) | `3180ec2fda41c492090747af5e9173451e39d047c1347a10a2bb27bcbaf33dee` | 962de598… | post-check unclamp probe (trabalhos/03) | board (STATUS calls the run "SONDA3-V2", 18/11) | `0x02` TRAVADO_PÓS_30 both ports, restore verified (src: STATUS.md) |
| SONDA4 (V2 image) | sha not recorded | — | pre-30 window probe | board ("SONDA4-V2", 18/11) | `0x02` TRAVADO_PRÉ_30; clamp 4→3 of request 30 observed live (src: STATUS.md) |
| SONDA5-V5 | `51084b6d83d1514149043eb5d010217e072164f193c4668db3eca1653b4e6dc0` | 962de598… | post-`Original()` write window inside slot-5 | flash 2 (18/11 16:51) | writes with NO echo ⇒ no capacity write window (src: STATUS.md; docs 05 §2, 08) |
| COAPP | `f37248c6f38a0a85b989e17004783a33c0e72fc37aa72631c8f6ce8006168f90` | clean | CO-app observer, log CO state | flash 1 | observer alive on clean base (src: STATUS.md) |
| COAPP-R1 | `0936a41fc130a7b22f72d5061a2ffd31b1f24cc1aee116632700ef675c758e6e` | REL1 | same on REL1, log the `0xFF` refusal with state | flash 3 | refusal logged (src: STATUS.md) |
| COAPP-B2 | `90b0643dd3144481ba9f29df89f8b077deab07c4a3f928e905eb4c70c406b006` | REL1 | iteration | flash 4 | (src: STATUS.md) |
| REVET-P1 | `56f70f9bf82181a1ebbce0b5b41e26e2b260d6881db976eb56b25c1c8e1660cb` | REL1 | CO flip attempt 1 | flash 5 | reads only — never wrote the proxy (src: STATUS.md; RASTRO §linha 25 "REVET só leu") |
| REVET-P2 | `0360ec8272bf353719272b218c5773eab69ec1b85fd51eea34d4b893817409c0` | REL1 | CO flip, working half | flash 6 | the documented CO half of the final pair (src: STATUS.md; RELATORIO-FINAL-8902.md) |
| SWAP7306 | `94859606b86723acc393edf405c2bb09daeb244ba6990419456bc9662793db7a` | 7306 | era probe: last BIOS that took Gen4 natively | flash 7 | F9 storm + FlashBack recovery; withdrawn, jamais reflash (src: STATUS.md) |
| MESA-C1 | `f106efb61661ff30963ecbd968f8f15da102bc153ef6ce13b84406c6cd73ab29` | clean | CO "mesa" combo attempt | flash 8 | CO reproduced 8/8, base stays Gen3 (src: STATUS.md) |

## 3. SMN-probe negatives (19 Nov, flashes 9–16)

All read-only SMN (CF8/CFC) probes unless noted; doctrine of echo throughout
(docs 08/10). All on clean 8902 `962de598…` except SMU101 (REL1 base).

| Image | SHA-256 (as recorded) | Flash | Question | Verdict |
|---|---|---|---|---|
| SMN12-A1 | `c330209bd8e60a3c157939d88bf9223f4a7996d8ba506ce8a520d9b322260db6` | 9 | decode PSP caixa-12 window `0x03b10700` | region decoded, but the 700/704/718 triple read FF (src: STATUS.md; RASTRO) |
| SMN12-A2 | `4c89b093f00c7323912ab5bcd0a1bf45e8bb4bb7857735167e340d59c1e76146` | 10 | full aperture map, 3 blocks | M2_FORA — triple all-FF with live controls ⇒ x86→caixa-12 route dead, final negation of front A's wire leg (src: STATUS.md) |
| NBIO-B1 | `0b688ea46a502b300eb8965bde6ce5cb9d74ac05d8b92d831a74b2fd0e4012f9` | 11 | NBIO policy block `0x0381xxxx` map | W_VIVA — witness `0x001A43B9` live on clean base (src: STATUS.md) |
| W1 | `9b5a7d7b65c498f620365e40c323282c10301b3f59d78dde17fab0cac317199b` | 12 | write `0x03810054:=1` once, echo, post-30 | NO_STATE — PEIM never dispatched (empty PEI log) (src: STATUS.md) |
| W1-A1 | `6f5a34e58ebc3a5b4358db6b3f47cf889d5aac7ea9cfba12de65bcae5e5ca384` | 13 | only delta: 16-aligned entry point | NO_STATE again ⇒ entry-alignment hypothesis dead by measurement (src: STATUS.md) |
| PEIPROBE-A1 | `2c9d6c195c014a8c91bc9317f1cf25318ddaa6aca23d9029e97f5564ec7dd9a7` | 14 | read IDTR-based dispatch tables from PEI | NUNCA_DESPACHOU — third PEIM death; content/GUID/alignment all excluded (src: STATUS.md) |
| SMU101-A1 | `6b7fd2a85e068757ddd3d85c6cbab23f688c6c0b110e27507276877acdcbe16b` | 15 | map pages `0x0101xxxx`/`0x0301xxxx` (REL1 base) | A_MORTA — all FF; SMU pages never route via direct CF8 (M22) (src: STATUS.md) |
| PG0904 | `28dd70ff6c1878ae0058ea8c42320b7f64157b0c8aab1dbb6a9fcf99ab36f65d` | 16 | map page `0x0904` (Zen3 policy banks) | PÁGINA_FORA — FF/0 with live controls same boot; third instrument for M22 (src: STATUS.md; docs 10) |

## 4. OBSPEI observer family (20 Nov, flashes 17–21; variants built 20–21 Nov)

Goal: dump HOBs / find the PEI dispatch-gate producer (docs 04 §3, 08 §5).
T55 spec: `biosmod_8902_co/trabalhos/55-observador-dxe-hob-ctx-nvram.md`.

| Image | SHA-256 (as recorded) | Flash / stage | Verdict |
|---|---|---|---|
| OBSPEI-A1 | `21da0f78ea67bd24ebbb1b1c3b6acf2e288a681565087c11f4426f2203d69c77` | flash 17 | module dispatched, but 32 KB volatile log lost |
| OBSPEI-A2 | `025670167a026c7c4b41e73433b66dc844ccdb2eef8fae09790123d3331a86c4` | flash 18 | POST code-61 hang — **JAMAIS REFLASHAR** |
| OBSPEI-A3 | `244876ef76cc7c4233322904ca41508f347ce5315fb6b1cb5a11c357db313b9c` | flash 19 | store corrupted |
| (recovery) | RC1 | flash 20 | recovery boot between A3 and A4 |
| OBSPEI-A4 | `555ddc6881ee5eb0bc6e015e9f6a1b70a1e023182d36043cc162e53add53ed6d` | flash 21 | M27-safe log class; CTX_GONE — observer line closed |
| OBSPEI-A5.ORDER | `3d2eb288379fab537a34e65e7c95862e5975581c46d4e03309e15672137f5848` | built; not USB-written | offline PEIM-dispatch iteration (src: construcoes/60-obspei-a5-order/README.md) |
| OBSPEI-A6.CTX | `1aedd0bd179d5c34815390a660ba59206b7e0cf9e56825042c1e5eac817fbe10` | built; not USB-written | (src: construcoes/61-obspei-a6-ctx/README.md) |
| OBSPEI-A7.HOBHIT | `f7047cb910296f7a2b28d110d724bbfd7a95d142df6636b61dcbabce509951d4` | built; not USB-written | (src: construcoes/62-obspei-a7-hobhit/README.md) |
| OBSPEI-A8.MULTIBOOT | `a4afe1d5fd67090a069dbda6fb16977ee4a308fd2e9daf824c32f7266f52e7f4` | built; not USB-written | (src: construcoes/63-obspei-a8-multiboot/README.md) |
| OBSPEI-A9.STATE | `d749536e1cc99ff3e464ad372e63cfbbc5ad005bbd1e6a247617edd3511b9413` | built; not USB-written | (src: construcoes/64-obspei-a9-state/README.md) |
| OBSPEI-A10.INSTANCE | `d749536e1cc99ff3e464ad372e63cfbbc5ad005bbd1e6a247617edd3511b9413` | built; not USB-written | same SHA recorded for A9 and A10 — see discrepancies (src: construcoes/65-obspei-a10-instance/README.md) |
| OBSPEI-A11.VZL1 | `9cbe6aacece9d1324b877ea91dae8b0de669eb6c0e57c80c3bb5be4b8ed1c893` | built; not USB-written | native VZL1 container alone not enough |
| OBSPEI-A12.BASE | `fa4e1f928571654ce3c02337f928b16ff61a99de7b36fc363a0781d17a04bb23` | built; not USB-written | (src: construcoes/67-obspei-a12-base/README.md) |
| OBSPEI-A13.MATRIX | `40d0114be760dff8e224a13d47e24c8266fbfc40a9c2797875d35d5219e18a11` | **staged** `FLASH-NOW-20261121-OBSPEI-A13-MATRIX`; never flashed | listed in "jamais reflashar" set (src: RASTRO §linha 207) |
| OBSPEI-A14.SAFE | `71d9675520af1d60b473451a34312b499270c4c6e69d2ede0862a25badd08faf` | built (README: board-tested: no) | packaging later called "A14-proven" by the A15 build — see discrepancies |

## 5. W1-A15 and the PEI-lever continuation (21 Nov, unnumbered flashes, then flash 22)

| Image | SHA-256 (as recorded) | Flash / stage | Verdict |
|---|---|---|---|
| W1-A15.SAFE | `bb0f2237aae590a60ce959173142ce5ff864003dbd4b4fb71bde402848e1ee42` | board, 21/11 morning (number not recorded in RASTRO; between flashes 21 and 22) | dump read post-boot: `Proxy54R2B=1` but Target Link Speed stayed 3 ⇒ **proxy alone refuted** (src: RASTRO §F; construcoes/71-w1-a15-safe/README.md) |
| A16/TARGET4 | `fed9b41e364a9a9b446d0f8d9908aba34110720827cabcdac2fc11396265f9b0` | board, 21/11 ~13:24 (unnumbered in RASTRO) | TARGET_MORTA — window measured, target rejected; proxy write echoed and persisted (src: RASTRO §G) |
| A17/CAP2 | `dd31eb70c3d4c73d9e6153d3a253c570cef6cad563615d42e26b115692fe227c` | board, ~13:47 (unnumbered) | CAP2_MORTA — LnkCap2 does not accept Gen4 bit post-30 (src: RASTRO §I) |
| A18/LC29 | `f7c39a36dbc6d99748411fdc737cf75646b13e4af47d4b9eb6a3e760560ee8bc` | board, ~14:41 (unnumbered) | LC29_CAP2_MORTA — bit29 clear echoes, cap2 still locked (src: RASTRO §K) |
| A19/TARGET-OVERRIDE | `0bf057f029fab861713dc1267da0d942bf1e8dddc0958726baceeecf8affefa9` | board, ~14:41 (unnumbered) | boot stuck at **POST code 36** — unsafe form; jamais reflash (src: RASTRO §K) |
| A20/GATE12 | `7da3d8fffc327de7729b41c154e0806dfdf353b48e0fbf4f17cb1500eefdb4b0` | **flash 22** (~16:30) | GATE_FECHADO measured on both ports — first x86 write to the caixa gate, closed (src: RASTRO §M) |

## 6. A-series endgame sprint (21–26 Nov, flashes 23–48)

The clamp-model and PSP-chain story is docs 05/09; outcomes below.

| Image | SHA-256 (as recorded) | Flash / stage | Verdict |
|---|---|---|---|
| A21/PSPPATCH | `6380ac54e486ed742fe27164529cee2ef227d53ea007b0815b9d91cf640a780c` | flash 23 | CO −22 restored + M.2 trained 16.0; GPU root 8.0 (src: RASTRO; the §Q flash-23 record was later corrected — see discrepancies) |
| A22/CBSUNLOCK | `5892f3901a39075f1c0f0994ed08b8156f3ed32be91c8eec0af12b5f324f5638` | staged `FLASH-NOW-20261121-A22-CBSUNLOCK`; no standalone flash recorded | CBS-menu unlock patch (src: RASTRO §~314) |
| A23/PSPPATCH2 | `707b93c36a2772cfe31f75527829a3c9f00ebd89ac8576ab5f29c692095e9422` | flashes 24 and 28 | with GEN4 set the roots read max=16.0 (flash 24) then clamped 8.0 (flash 28) — NVRAM/state poison found (src: RASTRO §X and flash-24/25 lines) |
| A24/COMBO | `b7b4a930be64499fc63150c08cc77bb96fbb0ceebf5fbfb64a0d77312a2f2eb8` | flash 25 | roots clamp 8.0 — "poison event" line (src: RASTRO) |
| A25/COMBOREL1 | `d371c7e57cff4973073a640d919307e9c67f60984fa33064478d8dcf773b3df8` | staged; **deprecated, never flashed** | known result (skip = Gen4 no CO); kept as reference (src: RASTRO §X) |
| A26/TARGET4 v1 | `0d89c03c14c136df4de014740484dc051a1284191ab06fb0c20aacef789a02b2` | **rejected before flash** | A16's mask would be present (src: RASTRO) |
| A26v2/TARGET4 | `79d49998d80e068b65a369399f50e7f90916241ea68c20fc778d4dcc965dafbe` | flashes 26 and 27 | TARGET_MORTA; flash 27 = stale-log episode (src: RASTRO) |
| A27/WIPER | `8c3d20961948c0a6ab12a5028b89e3785b4e996d5d17bea155c2ea28164033dc` | **never staged, never flashed** | owner decree archived the wiper approach (M30) (src: RASTRO) |
| A28/G4PBO | `ec3277b38da8f6b692445bbe548693f0bda6199395a50fc9f5e27b4ce1da2168` | flash 32 | usable interim: PBO visible via 11 front bytes validated; XMP-retrain boot = flash 33 stayed Gen3 (src: RASTRO; HANDOFF-FINAL §3) |
| A28 gambiarra | `ea1d7f4a16726039fd4220f836d3faa2252cdd421a0f6009ebae51d77d523fad` | board variant made by owner | owner-side variant of A28 (src: RASTRO) |
| A29/PSP-FLOW | `21b4f8ff2a2dde8a38980b3c333ba845ff4da102d154a3e1509449f87b572f0f` | flash 34 | glitches — REPROVADA; changing return semantics breaks subsystems (src: HANDOFF-FINAL §7) |
| A31/E07-RESTORE | `2f0ede6b3374848ef9c2eb35627b8dd9c9adf532c0109d5105c5665d469a0786` | flash 35 | healthy, CO ok, Gen3 persists ⇒ e07 restore is NOT the applier; A31 = proven safety-net CAP (src: HANDOFF-FINAL §2) |
| A32/TE-UNDO | `3d5d7388398d87d1a8ef5896890b4b452f6fc5e513e4d9da0b679970a82e36f2` | flash 36 (board state at campaign close, booted 22/11 11:54) | healthy, Gen3 persists ⇒ TE gate is NOT the applier (src: HANDOFF-FINAL §1–2) |
| A33/COMBO | `5c2e5bfae077052f89c17e6f80ab0505e92926ef8d38ef85b566df6f4264c2e5` | staged; **never flashed** | lost marginal value once A31 and A32 were both negative individually (src: HANDOFF-FINAL §3) |
| A34/WLX370 | `20f3ba79caa6579ab2c9e48fc15f68701b8b22b9c7eb7ce1b2532cf0664b0d79` | flash 37 (order 37/38 inferred) | NÃO-POST — PSP refuses to load an edited signed driver; signature check measured live (src: RASTRO §FFF) |
| A35/STRAPREGRAVA | `de80fdbccea530241160dd5a868d237a1fba583316f539ce7e44f7544a566c22` | flash 38 (order inferred) | healthy, Gen3 persists (src: RASTRO §EEE) |
| A36/PBO-CO | `f87ba18d677e6ae79c8a3a5118be87fcebba97f5958690718521f89efbd87a22` | staged `FLASH-NOW-20261122-A36-PBOCO`; flash 39 pending at log close | native menu unlock: 37 x86 bytes in FVMAIN, 6 stores NOPed (AOD trio) — the menu answer (docs 07; src: RASTRO §GGG) |
| A37/PTDID-43D1 | `09350a09b415474edad3cffa4a14594ad1e3c647f485be24f3db5bb8b0d61e87` | flash 40 (+ second boot after a PSU power cut) | base A36; 84 bytes only in the chipset firmware `_PT_` (guarded `43b9→43d1` write at reset/init + SKU constant + sum32). Result `43b9`, roots max 8.0 ⇒ M32; first reading invalid (upload skipped) — [docs/17](17-chipset-8051-firmware.md) (src: RASTRO §HHH–§III) |
| A38/SWEEP | `bad4773ecc128866e01078d7e38a31a4fca8646232ca6fa53ca7e0d700693ba2` | staged `FLASH-NOW-20261125-A38-SWEEP`; flash number not recorded | base A36; 133 bytes only in `_PT_`; read-only hardware-page sweep into chip RAM. Never read: the host XDATA window is PEI-only (src: RASTRO §JJJ) |
| A39/VIDDID-8550 | `f59385ccef86295c7422e5924c4adb66397b2bf97434e730a07cd591d4431392` | flash 42 (after PSU cut) | base A36; 99 bytes only in `_PT_`; guarded write at `01:8552` + status over the new config-space channel. `43b9`; `F4..F7 = 11 12 42 00` ⇒ hooks ran, nothing written, register holds `1242` ⇒ M33 — [docs/18](18-chipset-8051-id-hunt.md) (src: RASTRO §LLL) |
| A40/CAROUSEL | `dc589ed5eb43d8ff5e5769ae495e82ddeeae343cad3b8a3a268aeec61498d9c8` | flash 43 | base A36; 600 bytes only in `_PT_`; read-only sweep of page 01, state in XDATA. Routine ran, state lost, sweep never started — no verdict (src: RASTRO §MMM–§NNN) |
| A41/MEMINT | `863b318668f7723f24605aa67399c055b00d2493b2b463453d6eb8f59c8b910b` | flash 44 | base A36; 547 bytes only in `_PT_`; same sweep, state in internal RAM. Killed by the interrupt stack after the first page — no verdict (src: RASTRO §NNN–§OOO) |
| A42/ABOVE-STACK | `0e205813f253b7846efe02e677d661a5421ee42bf67de5721caecbdb5db01815` | flash 45 | base A36; only `_PT_`; stack-free sweep. **Complete**: ID pair at `01:005E..5F` (known) and one hit at `01:58A2..A3` (src: RASTRO §OOO–§PPP) |
| A43/WRITE-58A3 (full) | `943b3638d1e2fee796d6536873c923f0b04f45b439b9a07bc33ec3585583083f` | flash 46 | base A36; only `_PT_`; guarded+echoed writes to `01:58A3`/`01:005E` + two firmware ID literals swapped. Guard never satisfied (cell is not a copy), no hardware write, ID `43b9` (src: RASTRO §PPP) |
| A43 minimal | `d30e026d17ba1dcd3f0054b61908a34c54f89ec5010661c91d7bbebbfcbf605d` | staged, **not flashed** | the two cell writes only; kept as an optional control (src: RASTRO §PPP, §QQQ) |
| A44/STRAP-ID | `4a6e4d9979a15440fc7c341b42f1c76bd088876d9bd52f560ca1e48c35222753` | flash 47 | base A36; 50 bytes in the unsigned TE `21be6180` (A35 skeleton); guarded write of `43d1` to the NBIF0 ID strap `SMN 0x10134000`. `0c:00.0` still `148a` ⇒ M36 — [docs/19](19-final-sweep-and-closure.md) (src: RASTRO §TTT–§UUU) |
| A45/STRAP-BLIND | `ced7a7c22d03bebbee786008df431522e2bb4abebb48f727666077dc670212f9` | flash 48 | base A36; same hook; unguarded write (`0x100043d1` when the strap reads `FFFFFFFF`) — the only blind write of the campaign, owner-ordered. `0c:00.0` still `148a`, SMN control alive ⇒ M37, campaign closed (src: RASTRO §VVV–§WWW) |

Related hash (not a CAP): delivered profile `final_settings_A36.CMO`
`1d085ccea29b84a6629f25dabd281695ccc8ee4edd0223e2af77b474e3964cb1` (boost
1350→200; docs 07 for format) (src: RASTRO §GGG).

## 7. How each build was made and verified

Single house pipeline, applied identically to the 8902-era CAPs above
(details and commands in docs 03 §"Safe rebuild rules" and docs 14):

1. `prepare.py` extracts FFS/sections from the base CAP; patches are generated
   from a **table** (address→value), never hand-edited bytes.
2. `build.py` inserts the probe module(s) or applies the byte patches; LZMA
   FVMAIN rebuilds use the in-place swap recipe with `nice_len=273` (docs 03),
   and PKCS#7 signatures are preserved (docs 09; flash 37 proved PSP still
   verifies what it loads).
3. `release.py` is run twice; the two outputs must be **byte-identical**
   (determinism gate).
4. `verify.py` runs the full check suite (600+ checks on mature builds; e.g.
   A31 21/21, A32 18/18, A33 6/6 cross-check — src: HANDOFF-FINAL §6), plus
   host suites (ASan/UBSan unit tests of probe C), real-EDK2 dispatch-order
   tests, and QEMU/OVMF replay of the probe logic (bench harness returns
   rc=33 for "ran, logged" — docs 14, `biosmod_8902_co/bancada-uefi/`).
5. The coordinator independently re-runs the release, re-reads the target
   table against the spec, and runs his own `verifNN.py` gate script per task.
6. Staging: copy to `KINGSTON/FLASH-NOW-<date>-<name>/`, then **re-verify the
   SHA-256 of the copy on the stick**; only then does the owner flash (manual,
   FlashBack or EZFlash). No agent ever touches the board (docs 02).
7. Every flash has a pre-registered prediction matrix (branch names such as
   `W_VIVA`/`W_MORTA`, `GATE_FECHADO`, `PÁGINA_FORA`) and a post-read before
   reboot for volatile-log images (docs 02/10).

## Source discrepancies kept (not silently fixed)

- RASTRO §AAA cites A31 as a 63-hex string `2f0ede6b…05c566dfbb9c6a9`; the
  authoritative `construcoes/88-a31-e07-restore-safe/` record (64 hex) is used
  in the table above.
- `construcoes/64-obspei-a9-state/` and `construcoes/65-obspei-a10-instance/`
  record the **same** SHA-256 (`d749536e…`) for two different named builds.
- Flash numbers 29 and 31 cannot be pinned to a specific image from the
  sources located here (RASTRO line ~840 shows a matrix recorded for flash 31
  — "menus/16.0 pós-XMP/16.0 direto/8.0" — without an image name); "flash 30"
  reads as an SPI-dump event, not a flash; "flash 33" is an XMP retrain boot on
  A28, not a new image.
- A15–A19 were flashed 21/11 without numbers in RASTRO; one later RASTRO line
  (~500) loosely calls the A16-module event "flash 22", while §M numbers
  flash 22 = A20/GATE12.
- Flash 23 was first recorded as "Gen4 died" (RASTRO §Q) and retracted by §Z/§BB
  (truth: NVMe trained 16.0 with CO −22 on the same boot; GPU root 8.0).
- `construcoes/70-obspei-a14-safe/README.md` says "Board-tested: no" while the
  successor `71-w1-a15-safe/README.md` calls A14's packaging "A14-proven".
- The CO6 V2 directory records two SHAs (`2564305e…` and `c529fa8f…`); both are
  shown above.
- STATUS.md early text mentions "576 leituras" for SMN12-A2 where the final
  spec/record is 1168 readings.

## Sources

- `biosmod_8902_co/STATUS.md` — campaign diary: flash order 1–8 block, full SHA-256 records for the probe/solution-half series, SONDA verdicts.
- `biosmod_8902_co/RASTRO.md` — master log: §A task index, §B M-registry, §F–§M (A15→A20, flash 22), §X (A25), flash-24/25 lines, §EEE/§FFF/§GGG (A34–A36).
- `biosmod_8902_co/HANDOFF-FINAL-20261122.md` — endgame map: A31/A32 flash table, A28 backups, A33 devaluation, .CMO pointer context.
- `biosmod_8902_co/RELATORIO-FINAL-8902.md` — phase-1 close: REVET-P2 + RC1 as documented halves.
- `biosmod_8902_co/construcoes/*/README.md` — per-build SHA-256, staging status, board-tested flags (59–72, 76–93).
- `biosmod_v2/diagnostics/8902-gen4-co-handoff-20261117/HANDOFF.md` — V2-era CAP table (CO9/CO10/CO10b/REL1) and outcomes.
- `biosmod_v2/diagnostics/8902-gen4-co{2,3,6,7,8}-*/` and `8902-gen4-sv{3,4,5,6}-*/` — per-image SHA-256 lines.
- This repo: docs 02 (methodology), 03 (rebuild rules), 05 (clamp/fronts), 07 (menu unlock/.CMO), 08 (probes), 09 (PSP chain), 10 (M-registry), 14 (tooling).
