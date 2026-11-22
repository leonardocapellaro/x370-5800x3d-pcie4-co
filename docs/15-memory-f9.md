# 15 — Memory training and the intermittent "F9" on hot boots

## Summary

The owner reported intermittent POST code **F9** on "hot boots" after memory
stress or after applying BIOS settings, with fully stable memory in the OS.
We answered read-only only — no build, no flash, nothing changed by any agent
`(src: biosmod_8902_co/STATUS.md 22/11 ~14h45)`. The hardware is a mixed set
of four dual-rank G.Skill kits running above their model-rated speed; our
readings (SPD/sensors via sysfs, profile values via the `.CMO` dump) are
consistent with *training* failing when the DIMMs are warm while *operation*
stays fine. We gave a ranked knob list as engineering advice, not measurements.

## Owner-reported symptom (owner-observed)

Intermittent **F9** on warm/hot reboots — notably after RAM stress and after
applying BIOS settings — with no errors once the OS is up. Public AMI
POST-code references associate F9 with memory-initialization/training failure
(public knowledge; we used it as context only, and the coordinator's read of
the symptom — "treino de memória falhando com pente quente", "memory training
failing with a hot DIMM" — matches; that read is explicitly labeled in the
source as advice not yet measured on the board) `(src:
biosmod_8902_co/STATUS.md 22/11 ~14h45)`.

## Inventory (read-only, live, no sudo)

From sysfs (SPD + sensor reads): 4× 16 GB G.Skill DIMMs, dual-rank, Samsung
8 Gb DRAM — **two different kits mixed**: 2× `F4-3600C17-16GTZR` and
2× `F4-3600C16-16GTZN` (both model-rated "3600"; the profile runs them at
DDR4-3800). Only two DIMM temperature sensors (jc42) were exposed:
**47.5 °C and 49.3 °C** with no memory stress at idle
`(src: biosmod_8902_co/STATUS.md 22/11 ~14h45, "Lido ao vivo")`.

## The profile's training-relevant values

Read from the owner's saved profile (`analises/18-perfil-cmo/
scripts/dump_ocmr.py` over the decompressed `final_settings.bin`; cross-checked
against the IFR) and the STATUS block:

| item | value |
|---|---|
| Memory ratio / FCLK | DDR4-3800 (ratio 57) / 1900 MHz |
| Primary timings | 16-17-16-16-32, Cmd2T 1T |
| Gear Down Mode (GDM) | Auto |
| ProcODT | 36.9 Ω |
| Rtt Nom / Wr / Park | RZQ/7 / RZQ/3 / RZQ/1 |
| CAD bus drive strengths (CLK/ADDR-CMD/CS-ODT/CKE) | 24 / 20 / 24 / 24 Ω |
| DRAM voltage | 1.43 V |
| DRAM VBoot | Auto |
| VSOC (SoC) | Manual 1.075 V |
| VDDG CCD / IOD | 1.05 / 1.05 V |
| CLDO VDDP | 0.95 V |
| 1.8V PLL | 1.85 V |
| Fail count | Auto |
| PBO Scalar / thermal limit | Manual 10X / Manual 110 °C |

## Interpretation (engineering reading, not measurements)

- **Training vs operation.** F9 appears at POST, i.e. during memory
  training/reference-code execution; the OS being stable says the cell-level
  operation at the same frequency is fine. The failure is therefore in the
  training margin under conditions (warm DIMMs, mixed dual-rank kits,
  3800 > rated 3600, 1T, GDM off) — not a hard defect. Hot boots right after
  stress or right after applying settings are exactly the worst-case training
  windows.
- **The scalar is not a suspect.** PBO/PBO-scalar MP1 messages (incl. `0x2f`)
  are sent by the SMU DXE driver **after** memory training in the boot order
  (doc 04 §5; STATUS: "Scalar não participa (é enviado em DXE, depois do
  treino)"). A POST-time F9 cannot be caused by a DXE-later message
  `(src: biosmod_8902_co/STATUS.md 22/11 ~14h45)`.
- **Mixed kits at 1T** with Gear Down on Auto is a classic training
  marginality source: dual-rank loading doubles ODT/DQ demands, and Auto
  leaves GDM to AGESA's judgement.

## Ranked knob recommendations (engineering advice; one change at a time)

Order given to the owner (STATUS records the sequence; margin figures are
advice, not measurements) `(src: biosmod_8902_co/STATUS.md 22/11 ~14h45)`:

1. **Cooling/airflow over the DIMMs first** — the two exposed sensors show
   ~48–49 °C already at idle; training failures that appear hot boot are
   thermally sensitive.
2. **DRAM VBoot = the DRAM voltage (1.43 V)** instead of Auto — removes a
   variable-rail element from the training window.
3. **Small VSOC/VDDG headroom (≥ 40–50 mV over current)** — more margin for
   the uncore paths training exercises (1.075/1.05/1.05 today).
4. **Gear Down explicit (Enabled)** instead of Auto — removes AGESA's
   per-boot judgement on a mixed 4-DIMM 1T setup.
5. **Frequency fallback 3733, then 3600** — the kits' own model number is
   3600; 3800 is an overclock on mixed dual-rank parts.
6. **Terminations last** (ProcODT 36.9 Ω, Rtt 7/3/1, CAD 24/20/24/24) —
   most invasive class, least likely to be the hot-boot variable; we did not
   touch or rank any change here beyond "last".

## What would confirm

Per-knob A/B on hot boots only: apply one change, run 3–5 stress-then-hot-
reboot cycles (the failing condition), compare F9 occurrence; revert if no
effect (the one-change-at-a-time rule the owner already accepted). No such
cycle has been run in the campaign record — this doc records the question and
the advice, not an experiment.

## Sources

- `biosmod_8902_co/STATUS.md` 22/11 ~14h45 block — owner F9 consultation, profile values read by `dump_ocmr.py`, live SPD/jc42 readings, the advice sequence ("Uma mudança por vez"), "nenhuma construção".
- `biosmod_8902_co/analises/18-perfil-cmo/scripts/dump_ocmr.py` + `out/final_settings.bin` — profile-vs-IFR value dump used to confirm each table entry.
- `biosmod_8902_co/analises/17-menu-pbo-co/out/setup_ifr_all.txt` — IFR backing the OCMR option names/offsets.
- Cross-doc: boot position of MP1/PBO messages `docs/04-boot-timeline.md` §5; `.CMO` format `docs/07-co-pbo-menus.md` §8.
- Public knowledge: AMI POST-code association of F9 with memory init/training (context only, not re-derived here).
