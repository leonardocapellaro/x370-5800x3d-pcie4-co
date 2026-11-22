# 07 — Curve Optimizer & PBO: from hidden menus to native unlock

## Summary

On the 5800X3D the PBO submenu of the ASUS page and the PBO page of "AMD
Overclocking" are hidden by **one capability byte** (`AOD_SETUP[0xdf]`) that
AMD's setup driver writes and then deliberately zeroes; nothing in the
firmware reads that byte except the two IFR `SUPPRESS_IF` links. The whole
Curve Optimizer application chain — table builder, SMU DXE driver, MP1
messages `0x35`/`0x36` — was already alive on this machine (read live from
NVRAM), so opening the menu door was enough: CO became settable in the setup
with no injection. The PBO boost override was meanwhile *mis-scaled* on X3D
parts (`base = fuse_field × 25` with a low fuse field), which is why the owner
had to type 1250–1350 in the old BIOS; our A36 image (`sha f87ba18d…`, 37
bytes of x86) fixes the scale to `4550 + N` (ceiling 200), NOPs the two
flag-clearing stores across the three AOD driver copies, and changes nothing
else. This doc also maps the PBO Scalar path (MP1 `0x2f`, ungated), the ASUS
front-end quirks (hidden numeric + UTF-16 string pairs, the "stored = typed +
1" rule), and the `.CMO` user-profile format. How the Gen4 skip path kills CO
is doc 06 §2; the clamp itself is doc 05.

## 1. Why the menus are hidden on the 5800X3D

Three copies of the AMD setup/capability driver ship in the 8902 DXE volume —
`a2702a3c`, `55538d1e`, `07d279a1` (identical twins where `a2702a3c ≡
55538d1e`); the family selector `fe7d8450` installs the Vermeer GUID when
`CPUID & 0x0fff0f00 == 0xa20f00` and the package is AM4, so on this machine
the AOD copy that runs is `a2702a3c` (with SMU DXE driver `9a29bbe9`; the
Matisse SMU DXE `871349b8` and the second selector `cb9b43dd` exist but are
not on the Vermeer route). The capability routine links the PBO form flag and
then zeroes it (`analises/17-menu-pbo-co/out/`, capstone disassembly):

> "Rotina de capacidade do driver AOD (`0x15bc` na cópia `a2702a3c`): a
> tabela liga `AOD_SETUP[0xdf]` (`PcdVfrForm_AOD_PBO`) e o código a zera em
> dois pontos — `0x16ac` (bit 1 da capacidade ausente) e `0x18ad` (caminho do
> fusível 'OC desabilitado', só lido). Nenhum código lê `[0xdf]`; só o IFR:
> link PBO da ASUS (`SUPPRESS_IF NOT(qid 0x4f0==1)`, form `0x2718`) e link
> PBO da AMD (qid `0x193`)."
>
> "Capability routine of the AOD driver (`0x15bc` in the `a2702a3c` copy):
> the table links `AOD_SETUP[0xdf]` (`PcdVfrForm_AOD_PBO`) and the code zeroes
> it at two points — `0x16ac` (capability bit 1 absent) and `0x18ad` (the
> 'OC disabled' fuse path, read only). No code reads `[0xdf]`; only the IFR:
> the ASUS PBO link (`SUPPRESS_IF NOT(qid 0x4f0==1)`, form `0x2718`) and the
> AMD PBO link (qid `0x193`)." (src: biosmod_8902_co/trabalhos/93-a36-pbo-co-nativo.md
> "Operação normal (lida no código)")

The IFR dumps confirm the consumers. In the ASUS setup IFR, inside the
Extreme Tweaker form (id `0x2718`), the reference to the PBO submenu (form id
`0x292b`, "Precision Boost Overdrive") is wrapped in
`SUPPRESS_IF NOT(qid 0x4f0 == 1)`, and qid `0x4f0` is a hidden `NUMERIC`
bound to varstore `0xf000` (AOD_SETUP) offset `0xdf` (a second
`SUPPRESS_IF qid 0x480 in ['0x4','0x80','0x200'] NOT` also guards it)
(src: analises/17-menu-pbo-co/out/setup_ifr_all.txt lines 2183–2192, 3914,
11927). In the AMD page IFR, the "Precision Boost Overdrive" reference (form
`0x10`) is gated by `qid 0x193`, itself the hidden `NUMERIC` at AOD_SETUP
offset `0xdf`; the "Curve Optimizer" sub-page (form `0x27`) is gated by
`qid 0x133` = AOD_SETUP `[0x16d]` (or PBO mode `[0x8e] == 2`) (src:
analises/17-menu-pbo-co/out/aod_ifr_all.txt lines 42–52, 263–275, 2664,
2806–2809, 3452, 3600–3604, 3644). So: one byte hides both doors, and only
the IFR reads it.

## 2. The live flag map (read-only NVRAM capture)

Before building anything we read the live variables from `/sys/firmware/efi/efivars`
(read-only, no sudo) into `capturas/20261122-ocmr-varstore/`
(`aod_setup.efivar.bin`, `amdsetup.efivar.bin`, `ocmr.efivar.bin`,
`autodetectdata.efivar.bin`) (src: biosmod_8902_co/trabalhos/93 "Fontes";
STATUS.md 22/11 tarde). In the AOD_SETUP varstore the CO chain was already
armed:

| AOD_SETUP offset | value | meaning (IFR binding) |
|---|---|---|
| `[0x16d]` | `1` | CO capability — gates the "Curve Optimizer" link (qid `0x133`) |
| `[0x16e]` | `1` | capability sibling (hidden qid `0x17f`) |
| `[0x16f]` | `1` | capability sibling (hidden qid `0x17e`) |
| `[0x270]` | `8` | core count visible to the menu (qid `0x17d`) |
| `[0x170]` | `0` | CO mode: `Disabled` (0/1/2 = Disabled/All Cores/Per Core) |
| `[0xdf]` | `0` | PBO form flag — the only byte zeroed (hidden qid `0x193`) |

The chain "already runs on this X3D"; what was missing was only the door
`(src: RASTRO.md §GGG; trabalhos/93 "CO")`.

## 3. The application chain (native) and the readback evidence

Read from the binaries: setup module `e68c55b8` reads `AOD_SETUP`, builds the
per-core `{id, margin}` table and publishes it as PCD `0x39c` when
`[0x170] != 0`; the Vermeer SMU DXE driver `9a29bbe9` then sends the MP1
messages — `0x36` for all-cores, `0x35` for per-core. These are the same
messages the `ruv.py` service sends from Linux `(src: trabalhos/93
"Operação normal"; RASTRO.md §GGG; doc 04 §5)`.

Readback evidence exists on both sides of the armed/clean split (full story in
doc 06 §2). In the V2-era forensics on the **armed** Gen4 image, the service
logged `set to: -22 readback: 0` on all eight cores, and the analysis showed
why the log claimed success anyway: `set_core_offset` sends `0x35` and
*ignores the return*, the printed value is the requested one, not a
confirmed one `(src: biosmod_v2/diagnostics/curve-optimizer-readback-20261117/REPORT.md)`.
On the **clean** native base the mirror holds: CO −22 was confirmed with echo
8/8 (REVET-P2, flashes 6/8) — see doc 06 §2 and doc 11.

## 4. The boost formula — why "1250–1350" was needed

The boost-override consumer is `9a29bbe9 @0x8e9`:

> "`base = ((SMN 0x5D2C4 >> 17) & 0xff) × 25`; `v = token 0xed`;
> `v ≤ 2000 ⇒ alvo = base + v`; senão `−v ≤ 1000 ⇒ alvo = base + v`
> (negativo); grava o token."
>
> "base = ((SMN 0x5D2C4 >> 17) & 0xff) × 25; v = token 0xed; v ≤ 2000 ⇒
> target = base + v; otherwise −v ≤ 1000 ⇒ target = base + v (negative); the
> token is written back." (src: trabalhos/93 "Boost")

`SMN 0x5D2C4 >> 17 & 0xff` is a fused frequency field (25 MHz units). On X3D
parts that field reads low — **INFERRED at ~3300–3450 MHz from the owner's
experience, never measured** (live read of SMN `0x5D2C4` was outside the
authorized probe list of task 38) — so a menu value of ~1250–1350 was needed
to push the target past the interesting range. The owner's account:

> "No X3D esse campo de fusível é baixo (por isso você precisava digitar
> ~1250–1350 para ter efeito)."
>
> "On the X3D this fuse field is low (that is why you had to type ~1250–1350
> for it to have an effect)." (src: construcoes/93-a36-pbo-co-nativo-safe/README.md
> "O que muda", item 3)

The fuse itself is only read; nothing in A36 alters it. Whether the X3D's SMU
honours Fmax above 4550 is **not verified here** — the owner's experience with
the old BIOS says it does (README "O que NÃO foi medido").

## 5. The PBO Scalar path

ASUS page: `ONEOF` qid `0x20e` (OCMR `0x1a7a`, Auto/Manual) selects
`Customized Precision Boost Overdrive Scalar` qid `0x20f` (OCMR `0x1a7b`,
size 4, values 200…1000 = 2X…10X). PEIM `356241d4 @0x10b9` forwards the raw
number as token `0x35`. The AMD page is equivalent: `AOD[0xa4] == 1` (qid
`0xec`) with PBO mode `AOD[0x8e] == 2` (Advanced), value `AOD[0xa5]` (qid
`0xed`, 100…1000) is forwarded by AMD PEIM `c8f6d366 @0x9dc2721` into the
same token `0x35`. Consumer: `9a29bbe9 @0x1c46` (`lea ecx,[rbp+0x31]`) sends
MP1 **`0x2f`** with the raw value — no capability gate, no fuse gate. The A36
patch touches no byte of this path, so there was nothing for it to "fix": the
number already reaches the SMU today; what the SMU *does* with it is the
signed firmware's decision (unmeasured here; public expectation on X3D parts
is small) `(src: trabalhos/93 "Adendo" (a); RASTRO.md §GGG adendo;
analises/17-menu-pbo-co/out/pei_aod_c8f6d366.dis.txt)`.

## 6. The ASUS front-end quirks map (OCMR varstore, PBO page)

The OCMR varstore (`VARSTORE_OCMR_SETTINGS`, 7611 B, IFR varstore `0x20`)
carries the ASUS overclocking page. The PBO sub-page (form `0x292b`) pairs a
visible `STRING` (or `ONEOF`) with a **hidden `NUMERIC`** that holds the real
value (`SUPPRESS_IF TRUE`); the values that matter:

| control | visible qid / OCMR | hidden numeric qid / OCMR | notes |
|---|---|---|---|
| Precision Boost Overdrive | qid `0x20a` @ `0x19fb` | — | Auto=15, Disabled=0, Enabled=1, Manual=2 |
| PPT Limit | qid `0x292c` @ `0x19fe` (string) | qid `0x20b` @ `0x19fc` (size 2) | |
| TDC Limit | qid `0x292d` @ `0x1a28` (string) | qid `0x20c` @ `0x1a26` (size 2) | |
| EDC Limit | qid `0x292e` @ `0x1a52` (string) | qid `0x20d` @ `0x1a50` (size 2) | |
| PBO Scalar selector | qid `0x20e` @ `0x1a7a` | — | Auto=0 / Manual=1 |
| PBO Scalar (custom) | qid `0x20f` @ `0x1a7b` | — | 2X=200 … 10X=1000 |
| Max CPU Boost Clock Override | qid `0x292f` @ `0x1a83` (string) | qid `0x210` @ `0x1a7f` (size 4) | see +1 rule |
| Platform Thermal Throttle Limit | qid `0x211` @ `0x1aab` | numeric @ `0x1aac` | owner: Manual / 110 |
| PBO Fmax Enhancer | qid `0x209` @ `0x1ab0` | — | separate suppressif |

The **"stored = typed + 1, 0 = Auto"** rule: the owner's profile shows the
mechanism — text `"1350"` at `0x1a83` with hidden number `1351` at `0x1a7f`;
PEIM `356241d4` performs the `dec` on the way out. Consequently the owner's
*real* limits are **PPT 114 / TDC 75 / EDC 115** (we had misread 115/76/116
before recording this correction):

> "Boost: texto `0x1a83`=\"1350\", número oculto `0x1a7f`=1351 (a ASUS guarda
> digitado+1; PEIM faz `dec`). Na A36, 1350 > 200 ⇒ ignorado (4550). Mesma
> regra +1 em PPT/TDC/EDC: os limites reais do dono são **114/75/115**."
>
> "Boost: text `0x1a83`="1350", hidden number `0x1a7f`=1351 (ASUS stores
> typed+1; the PEIM does the `dec`). On the A36, 1350 > 200 ⇒ ignored (4550).
> Same +1 rule for PPT/TDC/EDC: the owner's real limits are 114/75/115."
> (src: trabalhos/93 "Adendo" — "Conflito de valor")

## 7. The A36 build — 37 bytes, native unlock

Base: official 8902 (sha `04ddae2d…`); **no** PSP NOPs and **no** AMIBCP
11-byte hack — both become unnecessary. The change is 37 bytes of x86 in
FVMAIN, AMD-signed content byte-identical to official
`(src: construcoes/93-a36-pbo-co-nativo-safe/README.md)`:

| module | PE site | before | after |
|---|---|---|---|
| `a2702a3c`, `55538d1e` | `0x16ac`, `0x18ad` | `mov [rbx+0xdf], bpl` | `nop` (7 B) |
| `07d279a1` | `0x175c`, `0x195d` | idem | `nop` (7 B) |
| `9a29bbe9` | `0x8e9` | `shr r11d,17; movzx ebx,r11b; imul ebx,ebx,25` | `mov ebx,4550; nop` |
| `9a29bbe9` | `0x90f` | `cmp eax,2000` | `cmp eax,200` |

Pipeline: FVMAIN LZMA decompressed → bytes swapped → recompressed with the
original properties (3 498 515 B ≤ 3 510 957 B) → back in place, FF padding;
Matisse `871349b8` untouched. **Verify 68/68** (independent `verify.py`): CAP
diff confined to the stream, everything else byte-identical to official;
FVMAIN 538 files identical in list, diff == exactly the 37 expected bytes;
FFS headers and non-PE32 sections identical; no relocations at the sites; a
capstone sweep of each module shows only the site instructions changed and
zero `mov [rbx+0xdf], bpl` remaining; twins `a2702a3c ≡ 55538d1e` preserved;
a **boost mini-interpreter** executes the patched block:
`0→4550, 25→4575, 100→4650, 200→4750; 201/1250/1350/2000→4550` (ignored);
`−25→4525, −1000→3550, −1001→4550` — independent of the fuse; a positive
control reproduces the old formula on the unpatched module. Build reproducible
byte-identical ×2. Artifacts: CAP `C6H.A36.PBOCO.CAP` sha
`f87ba18d677e6ae79c8a3a5118be87fcebba97f5958690718521f89efbd87a22`;
`out/verification.json` sha `a75023ed…`; `out/patch.json` sha `20e4bfc1…`
`(src: trabalhos/93 "Verificação"; construcoes/93-a36-pbo-co-nativo-safe/README.md)`.

**Board status (honest):** staged at `KINGSTON/FLASH-NOW-20261122-A36-PBOCO/`;
**flash 39 was never executed in the campaign record** — the board ended on
A35 (owner flash, boot 13:04:40) with the A28 recovery preserved in `old/`,
and at 14:05 the USB root still held the long filename instead of the
required `C6H.CAP` name (owner was warned) `(src: STATUS.md 22/11 ~13:10,
~14h10)`. The prediction matrix (menus visible, `ruv.py --list` shows the
setup CO without manual application, peak ≈ 4550+N, …) is in the build README.

## 8. The `.CMO` user-profile format

A BIOS user profile (`Tool → ASUS User Profile`) is an **EFI 1.1 compressed
stream** (8-byte header, PBIT=4). Our stdlib codec (`eficomp.py`) and the
EDK2 reference compressor (`EfiCompress.c` sha `b0844e05…`,
`Decompress.c` sha `bfd71b62…`) both decode it; the byte-exact control:
recompressing the profile's decompressed image with the reference compressor
reproduces the owner's file **byte for byte** (15 481 B) — the BIOS uses that
exact compressor `(src: trabalhos/93 "Adendo" (b);
analises/18-perfil-cmo/scripts/efitool.c)`.

Decompressed (106 402 B) the layout is: `0x48`-byte header + C-typedef schema
text (76 057 B) + six hex-text sections:

| section | bytes |
|---|---|
| `SETUP_DATA` | 681 |
| `VARSTORE_OCMR_SETTINGS` | 7611 |
| `USB_SUPPORT_SETUP` | 49 |
| `NETWORK_STACK` | 8 |
| `QFAN_DATA` | 120 |
| `CBS_CONFIG` | 1553 |

**There is no `AOD_SETUP` section ⇒ the AMD Overclocking page — Curve
Optimizer included — cannot be stored in a profile.** The loader (`899407d7
@0x5aa2..0x5b1d`) runs four `memcmp`-style checks: `[0..0xc) ==
"$ProfileData"`; `[0xf..0x2d)` = board name string; `[0x38..0x40) ==
CPUID & 0x0fff0f00` (computed `0xA20F00` at `0x58e3`); format byte
`[0x2d] == 01`. No checksum; `[0xc..0xf)` and the size word `[0x30]` are not
compared. The owner's file passes all four, and the A36 keeps `899407d7`
byte-identical (its FV diff is the 37 bytes in the other four modules). The
profile's OCMR section equals the live NVRAM OCMR with zero diffs — the
profile *is* what is in use. The corrected profile (`fix_profile.py`) changes
only OCMR offsets `0x1a7f,0x1a80,0x1a83,0x1a85,0x1a87,0x1a89`: hidden boost
`1351→201`, text `"1350"→"200"` (6 bytes, 7 text characters; re-emission of
the untouched section verified byte-identical). Delivery:
`final_settings_A36.CMO` 15 478 B sha `1d085cce…`; original
`final_settings.CMO` sha `3cb5c6d1…` untouched
`(src: trabalhos/93 "Adendo" (b); STATUS.md 22/11 ~14h10;
construcoes/93-a36-pbo-co-nativo-safe/README.md "Perfil salvo")`.

## 9. Which knob lives where (ASUS page vs AMD page)

| knob | ASUS page (OCMR, vs `0x20`) | AMD page (AOD_SETUP, vs `0xf000`) |
|---|---|---|
| PBO enable | `0x19fb` | `[0x8e]` (Auto/Disable/Enabled/Advanced) |
| PBO Limits selector | implied by PPT/TDC/EDC entry | `[0x8f]` (qid `0xe6`) |
| PPT / TDC / EDC [A/W] | `0x19fc`/`0x1a26`/`0x1a50` (hidden numerics) | `[0x90]`/`[0x94]`/SOC EDC `[0xa0]` … |
| PBO Scalar | sel `0x1a7a` + val `0x1a7b` (2X–10X) | sel `[0xa4]` + val `[0xa5]` (1X–10X) |
| Boost Clock Override | text `0x1a83` + num `0x1a7f` | `[0xb6]` Enabled/Disabled or Disabled/Positive/Negative |
| Curve Optimizer (mode/sign/magnitude) | **absent** | `[0x170]`/`[0x171]`/`[0x172]`; per-core signs `[0x174..]`, magnitudes `[0x1b4..]` (form `0x27`) |
| Thermal throttle limit | `0x1aab` + `0x1aac` | (AMD page variant exists; not mapped) |

Both front-ends feed the same SMU parameters; **which page wins when they
disagree is unmeasured** — our guidance to the owner is to keep the same
numbers on both (or ASUS side at Auto). The AMD-only extras (per-core CO,
1X scalar option, negative boost list) and the ASUS-only quirks (+1 storage,
UTF-16 strings) are the practical differences
`(src: analises/17-menu-pbo-co/out/setup_ifr_all.txt, aod_ifr_all.txt;
construcoes/93-a36-pbo-co-nativo-safe/README.md "Como usar depois do flash")`.

## Open questions

- Actual value of the X3D fuse field (`SMN 0x5D2C4 >> 17 & 0xff`) — inferred
  ~3300–3450, never measured.
- Whether the X3D SMU honours Fmax > 4550 (owner experience says yes).
- ASUS×AMD page precedence when values diverge.
- What the signed SMU does with the scalar on X3D (public expectation: small).
- Whether FlashBack preserves saved setup options (README risk note).
- Why the 11 AMIBCP bits made the page visible in the earlier hack (not
  determined; the flag path above explains visibility without them).

## Sources

- `biosmod_8902_co/trabalhos/93-a36-pbo-co-nativo.md` (+ adendo 22/11 ~14h) — full task: questions, code-read operation, patch table, verify, unmeasured list, Scalar/.CMO adendo.
- `biosmod_8902_co/construcoes/93-a36-pbo-co-nativo-safe/README.md` — A36 design, usage steps, prediction matrix, risks, profile guidance, unmeasured items.
- `biosmod_8902_co/analises/17-menu-pbo-co/out/` — capstone disassembly batch (`a2702a3c/55538d1e/07d279a1/9a29bbe9/871349b8/e68c55b8/fe7d8450/cb9b43dd/c8f6d366/899407d7`), IFR dumps `setup_ifr_all.txt` / `aod_ifr_all.txt`.
- `biosmod_8902_co/capturas/20261122-ocmr-varstore/` — read-only efivar capture (AOD_SETUP, AmdSetup, OCMR).
- `biosmod_8902_co/analises/18-perfil-cmo/` — .CMO codec (`eficomp.py`, `efitool.c`, `fix_profile.py`, `cmo.py`, `dump_ocmr.py`), decompressed images, round-trip artifacts.
- `biosmod_8902_co/RASTRO.md` §GGG (+adendo) — master-log summary of all A36/.CMO findings.
- `biosmod_8902_co/STATUS.md` (22/11 blocks: A36 built/staged; .CMO corrected; F9 consultation) — diary with board/USB state at each step.
- `biosmod_v2/diagnostics/curve-optimizer-readback-20261117/REPORT.md` — readback forensics (`set to: -22 readback: 0`; ruv.py ignores the SMU return).
- Cross-doc: skip kills CO `docs/06-gen4-skip-and-era.md` §2; MP1 messages in boot order `docs/04-boot-timeline.md` §5; builds catalog `docs/11-build-catalog.md`; SMN probe authorization `docs/08-smn-probes.md`.
