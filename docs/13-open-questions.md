# 13 — Open questions: what is still open, and what each one costs

## Summary

The reopening list, curated and deduplicated from the "Open questions" sections of
[docs/03](03-firmware-anatomy.md)–[docs/12](12-timeline.md) and [docs/15](15-memory-f9.md)
plus `HANDOFF-FINAL`. Each item says what evidence would close it and what it costs
(offline RE only / a board reading / a new CAP + owner flash / hardware access). Group 1 is
what could still change the Gen4+CO verdict; nothing in groups 2–3 can.

## 1. What could still change the verdict on the combo

1. **Read the on-chip NBIO microcode.** The clamp's applier is named only by elimination
   (writer absent from every expanded byte of both bases — M17–M19; both flash-visible
   appliers neutralized on-board in flashes 35/36 without effect). Closes with: an
   extracted on-chip microcode dump, a cross-board/cross-vendor dump exhibiting the store,
   or APML/hardware access. Cost: hardware-level tooling, outside every offline path we had
   `(src: docs/05 §7; docs/09 §8; docs/10 reopening table)`.
2. **An AMD service/policy document for Zen3** naming the svc/policy behind the strap.
   Closes: the "who commands the clamp" question by document, not elimination. Cost:
   documents only — none was found in public `(src: docs/05 §7; RASTRO §N)`.
3. **A pre-request-30 write window.** The post-30/pre-training PEI window **was** exercised
   (W1-A15 → A16/A17/A18, A26v2: the proxy echoed, the speed target stayed masked — "proxy
   alone" refuted, "the request is the poison" model). Never executed is a lever **before**
   request 30: our candidate PEIMs all died undispached (flashes 12/13/14) and LTSSM/PHY
   writes before native training hang boot (M28). Closes with: a dispatchable pre-30 hook,
   or a board measurement of the dispatch inputs via an M27-compliant observer redesign.
   Cost: 1–2 owner flashes, with no positive precedent to justify them `(src: docs/04 §3;
   docs/10 "PEI dispatch triple death"; docs/11 §5)`.
4. **Doorbell receipt on the actually-loaded SMU.** The proven key receipts sit in the
   never-loaded generation; the loaded 56.76.0 body was never re-scanned for the
   `67ac/77ac`-class keys. Cost: offline RE only, cheap `(src: docs/09 Open questions 1)`.
5. **The flash 23→24 anomaly** — PSP-patched images coincided with roots going 8.0→16.0
   although those drivers supposedly never load; records conflict and raw was lost. Closes
   with: offline forensics of surviving captures, then one re-instrumented reproduction
   (owner flash) `(src: docs/05 Open questions 1)`.
6. **A35 non-discrimination** (write discarded vs group lock vs one-shot sampling vs core
   numbering vs cave path never executed; the A34 discriminator died non-POST). Closes
   with: a discriminating CAP — but the owner closed the experimental matrix (§ZZ), so it
   needs his explicit re-opening. Cost: 1 owner flash `(src: docs/05 Open questions 2)`.
7. **Chain-completeness gaps:** the TOS service table of 0.11.0.87 (never located), the
   semantics of the `0x0904` strobes/bit 21, and the x86 wrapper's PCIe core numbering.
   Cost: offline RE (core numbering needs one board measurement); low leverage — after
   §DDD the legacy drivers never load `(src: docs/05 Open questions 3–5; docs/09 §8)`.
8. **Which block latches the PCI-visible chipset device ID.** The config-space diagnostic this item
   asked for was built (25 Nov): `01:005C` written without effect (M32), `01:8550` holds the ASMedia core
   ID `1242` (M33), a full sweep of hardware page 01 found no second stable copy, and the firmware's ID
   literals are not the source. Closes with: Promontory documentation or silicon-level work. Even then a
   changed ID would not be enough by itself (next item) `(src: docs/18 §9)`.
9. **A forged ID that also survives the function-2 challenge.** The active PSP driver wants a newer
   chipset's ID row **and** an approved challenge–response on function 2 of the same device (M35). The one
   idea that addressed both (B10: forged ID on an internal device, then a bus swap) died at its first gate:
   the NBIF device-ID strap does not respond to x86 writes at the only hook we can run (M36/M37). Closes
   with: a 400/500-series chipset, an x86-definable ID shown by another route, or an offline proof that the
   challenge needs no secret plus an x86-controllable responder. Cost: none of these is available on this
   board `(src: docs/19 §4)`.
10. **Whether the SMU honors boost above 4550 MHz on X3D** — inferred from the fuse
   formula, never measured (owner experience says yes). Closes with: OS clock readings on
   an A36 boot. Cost: board reading only `(src: docs/07 Open questions; docs/09 §8)`.

## 2. Unmeasured but cheap (cannot change the combo verdict)

- **PBO Scalar's real effect on X3D** (MP1 `0x2f`, ungated menu path; public expectation:
  small). Closes with: owner A/B in menus + load readings. Cost: menu time only
  `(src: docs/07 §5/Open questions)`.
- **ASUS-page × AMD-page precedence** when the two front-ends hold divergent values.
  Closes with: a deliberate divergence A/B in setup. Cost: menu time `(src: docs/07 Open questions)`.
- **The X3D fuse field** (`SMN 0x5D2C4 >> 17 & 0xff`, inferred ~3300–3450). Closes with:
  one read-only SMN probe — needs a probe module, so one flash (existing skeleton)
  `(src: docs/07 Open questions)`.
- **The F9 hot-boot knob list** (docs/15) has never been A/B-tested: one change per cycle,
  3–5 stress-then-hot-reboot cycles per knob, revert on no effect. Cost: owner cycles, no
  build `(src: docs/15 "What would confirm")`.
- **`PCIEX8_2` under the Gen4 skip was never tested**, and the lone `0x30c1` AER figure /
  REL1 first-boot log were never re-instrumented. Closes with: boot RC1 and read
  `lspci`. Cost: one owner flash back to RC1 `(src: docs/06 Open questions)`.
- **Reconcile the two circulating SMN register lists** (payload window `03b109c4..d8` vs
  submit/ring registers `03b10570/574/0524/0a40`) before either is reused; and whether the
  active-stack request 30 really uses the Cezanne-decoded `0x1039/0x103a` numbers. Cost:
  offline RE `(src: docs/04 Open questions; docs/08 Open questions)`.
- **Minor offline gaps:** e07 restore entry re-count (3+7 vs earlier 3+8); svc-numbering
  stability across TOS generations; VZL1 variant bytes `[04]/[06]` meaning; full PSP
  directory entry-table format; why the 11 AMIBCP bits sufficed in the earlier hack; why
  FlashBack (unlike EZFlash) does not enforce the FVMAIN signature. Cost: offline RE
  `(src: docs/03 Open questions; docs/07 Open questions; docs/09 Open questions 3–4)`.
- **Whether FlashBack preserves saved setup options** (flagged risk). Cost: free to
  observe at the next unavoidable flash `(src: docs/07 Open questions)`.

## 3. Small honest unknowns

- **Flash 39 (A36) board confirmation**: "pending at log close" — the owner may have run
  it afterward; closes with his word or any first-boot log. Cost: nothing
  `(src: docs/11 §6; docs/07 §7)`.
- **Flashes 29/31 are unattributed**, the 21/11-morning W1-A15/A16–A19 runs are unnumbered,
  and whether A14 was itself flashed is recorded both ways. The diary simply lacks the
  entries — flagged, not fixable `(src: docs/12 Open questions; docs/11 "Source discrepancies")`.
- **Residual PEI-dispatch cause** (byte-state vs external-loader return) after the offline
  hunt closed with SEC-as-caller and mode-never-0x11: needs an H1/H2-class board
  measurement; the observer line closed with CTX_GONE, so revival means the M27-safe
  redesign plus explicit owner approval `(src: docs/04/08 Open questions; RASTRO M24/M27)`.
- **The `A30-residual` reduced DXE collection** — a rider only, justified by no flash of
  its own `(src: HANDOFF-FINAL §5.2)`.

## Sources

- `biosmod_8902_co/HANDOFF-FINAL-20261122.md` — §3 endgame, §5 pending items.
- `biosmod_8902_co/RASTRO.md` — reopening triggers, M24/M27/M28, §ZZ/§N.
- [docs/03](03-firmware-anatomy.md), [docs/04](04-boot-timeline.md), [docs/05](05-gen4-the-clamp.md),
  [docs/06](06-gen4-skip-and-era.md), [docs/07](07-co-pbo-menus.md), [docs/08](08-smn-probes.md),
  [docs/09](09-psp-driver-re.md), [docs/10](10-negative-results.md), [docs/11](11-build-catalog.md),
  [docs/12](12-timeline.md), [docs/15](15-memory-f9.md) — per-doc "Open questions" sections
  consolidated here (deduplicated; identical items appear once).
