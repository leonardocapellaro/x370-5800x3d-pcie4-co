# 02 — Methodology: an offline, pre-registered, multi-AI firmware campaign

## Summary

This campaign touched a running machine's firmware for nine days without ever letting a
software agent flash, reboot, or write a live register. What made that safe — and what made
its ~70 builds and ~40 flashes produce publishable conclusions instead of folklore — is a
small set of disciplines: strict division of hands between agents and the owner;
pre-registered prediction matrices (observable + decision criterion + what-refutes, written
before any build); an "echo" rule for every write; a deterministic build pipeline with an
independent coordinator re-check; a master anti-repetition registry (`RASTRO.md`); a
multi-AI harness in which a second model wrote adversarial opinions that corrected the team;
and a rule that every own error was recorded with its lesson. This document is the workflow;
the verdicts it produced live in [docs/05](05-gen4-the-clamp.md) and
[docs/10](10-negative-results.md).

## 1. Division of hands: the offline doctrine

Agents (the coordinator plus one worker subagent at a time) only ever **read, analyze,
build and verify**. The human owner is the only hand on the board: only he flashes, reboots
and changes NVRAM — recovery included, via USB FlashBack
`(src: biosmod_8902_co/HANDOFF-FINAL-20261122.md §7 "Flash/escrita NVRAM/escrita viva: SÓ o dono"; CLAUDE.md "Limites e entrega")`.
Even the single authorized live channel (installed 21/11) was read-only SMN probing by a
service the owner installed with one sudo step, with a kill-switch file he controls
`(src: CLAUDE.md aditamento 20261119T21:49Z; docs/08 §3)`. Hard fences applied regardless
of any experiment: **no fuse/OTP/authorization state in any scenario**, AMD-signed content
byte-identical in every daily build, no published binaries `(src: RASTRO.md M11; HANDOFF-FINAL §7)`.
Scope expansions came only by explicit owner decree, each recorded (the 18/11 policy
revision permitting embedded experimental writes; the 19/11 authorization of offline
weakness research) `(src: CLAUDE.md aditamentos 20261118 / 20261119T03:10Z)`.

## 2. Pre-registration: observable, criterion, refuter

Every experiment began as a task spec with one skeleton — question, sources, normal
operation, observable, **evidence that refutes the hypothesis**, result, next discriminator
`(src: biosmod_8902_co/trabalhos/*.md)`. Before any build shipped for flash, its
**prediction matrix** was written: named branches plus the decision each forces — e.g. W1's
`DIAG / W_ESCRITA_MORTA / W_ESCRITA_VIVA_G3 / W_ESCRITA_VIVA_G4` and A16's
`TARGET4_G4 / TARGET4_G3 / TARGET_MORTA / DIAG` `(src: biosmod_8902_co/trabalhos/39-patch-w1-proxy-unclamp.md; RASTRO.md §G)`.
The endgame validated the practice: the two neutralization results "caíram exatamente nas
linhas previstas" — fell exactly on the predicted rows `(src: HANDOFF-FINAL §7)`. Nothing
was called dead without a measurement, and volatile-log images require a post-read
**before** reboot `(src: HANDOFF-FINAL §7; docs/11 §7)`.

## 3. The echo doctrine

Every write inside a built CAP is bracketed: **read the target before, write, read back to
confirm the echo, log all three** — no blind writes, ever `(src: CLAUDE.md política 20261118; RASTRO.md M19 note)`.
The doctrine gave the campaign its two strongest negative proofs: the first x86 write to
the PSP message gate (A20/GATE12, flash 22) echoed *closed* on both ports, and the proxy
write `0x03810054:=1` (W1-A15/A16, then A26v2) **echoed 1 yet changed nothing** — which is
why those hypotheses could be refuted cleanly instead of left ambiguous
`(src: docs/05 §4/§6; docs/10 "NBIO proxy write"; RASTRO §M/§AB–§CC)`.
The same care applies to *reading*: `FF` is never proof of absence by itself (that premise
false-fired in flash 10); every negative required double-decoded live controls in the same
boot `(src: docs/05 §6)`.

## 4. Build discipline: pinned bases, determinism, replay, the "régua"

One house pipeline ran every CAP (full detail in docs/11 §7, docs/14): `prepare.py`
extracts FFS/sections and patches come from a **table** (address → value), never hand-edited
bytes; `build.py` pins the base image's SHA-256 and **refuses to run** on an unexpected
input; `release.py` runs twice and the outputs must be **byte-identical**; `verify.py` runs
the full suite (600+ checks on mature builds) plus ASan/UBSan host tests of the probe C and
a real-EDK2 dispatch-order test, and **QEMU/OVMF replay** of probe logic against archived
board readings — with the honest limit logged (M13): the bench gates probe logic, never
PSP/BL behavior `(src: HANDOFF-FINAL §6; docs/14; RASTRO M13)`. On top, the **coordinator's
independent re-check** (house name *régua*): re-run the release from scratch, re-derive the
target table from the spec, run a per-task `verifNN.py` gate. Two invariants close the
loop: the **confined-diff rule** (the image diff must be confined to the patched region,
everything else byte-identical to the pinned base — 37 bytes total for A36) and **staged
re-verification** (the copy on the USB stick has its SHA-256 re-checked before the owner
flashes) `(src: HANDOFF-FINAL §6 "Regras de diff"; docs/11 §7; tools/build/fvmain_bytepatch.py)`.
Every raw measurement, including negatives, is preserved with its SHA — "são as negativas
que fecham as hipóteses" `(src: HANDOFF-FINAL §7)`.

## 5. RASTRO: anti-repetition as a first-class artifact

Mid-campaign (20/11, under the owner's "investigate until every breach is exhausted"
directive) the team created `RASTRO.md`, consulted **before every task dispatch** and
updated at every verdict: §A one-line task index, §B dead ends M1–M30 (each with the
evidence that closed it and the trigger that would justify reopening), §C/§D live breach
maps `(src: CLAUDE.md aditamento 20261120T0600Z; docs/12)`. The attached rule: a dead path
may only be retried with a *new* hypothesis attacking exactly the proven weak link. The
registry's published form is [docs/10](10-negative-results.md).

## 6. Multi-AI harness

Visible coordination ran in Claude Code on **local model sessions** (opening the campaign
on a local Qwen build with model identity checked at start; the model changed twice, each
change handled by a written handoff) `(src: CLAUDE.md step 1; HANDOFF-NOVA-SESSAO-20261120.md; HANDOFF-NOVO-MODELO-20261121.md)`.
Worker subagents ran **strictly one at a time**, each confined to its own tree, and the
coordinator audited every delivered artifact before accepting it `(src: CLAUDE.md step 2; BUILD-NOTES.md "one worker at a time")`.
An **adversarial consultant** (Codex, reached through the owner) received the state
periodically and wrote dated written opinions ("Parecer do Codex"), with an advisory review
agenda plus receipts in `revisoes/`; opinions were **never accepted raw** — each was
checked against artifacts, and the consultant's five campaign reviews "viraram erratas"
(became recorded errata, §TT–§ZZ of the master log) `(src: STATUS.md "Parecer do Codex" blocks; HANDOFF-FINAL §8)`.
Two concrete corrections:

- **T53, 20/11 16:53:** Codex argued the stronger, narrower reading of the PEI-dispatch
  result — the boot block is installed by a **producer external to every FFS**, and
  "BL/ROM" is only a *named hypothesis*; the coordinator accepted and corrected the queue
  wording `(src: STATUS.md 16:53:05 opinion + disposition; RASTRO §A line 53)`.
- **T51, 20/11:** the worker's own erratum (three `0904f1xx` dwords were THUMB instruction
  halves, not data) was confirmed byte a byte by the coordinator — who in the same task had
  to record his own error (below) `(src: RASTRO §A line 51; docs/09 Lessons)`.

## 7. Errata discipline

Every error — agent's or coordinator's — was "lavrada": recorded with its lesson, so it
could not propagate silently. Three representative entries:

- **"Byte-combining ≠ pointer" (T24/T30):** an early chain assumed that byte values which
  *could* fill a pointer table meant something *did* point there; the correction records
  the lesson verbatim `(src: RASTRO §A lines 24/30; docs/09 Lessons)`.
- **Big-endian false-negative (T51):** the coordinator's `0x0904xxxx` key scans had run
  big-endian, producing a false "zero keys in the SMU"; the little-endian scan found the
  exact doorbell keys. House corollary: a negative scan is only worth the exact literal
  searched `(src: RASTRO §A line 51; HANDOFF-FINAL §6)`.
- **Brief ≠ source (this repo's writing phase):** the coordinator's brief for doc 05
  conflated two different proxy-write experiments (the W1/A15 echo-proven write and the
  A26v2 TARGET_MORTA line); worker W2 checked the sources instead of trusting the brief and
  caught it. Standing rule: **sources over briefs** `(src: BUILD-NOTES.md W2 audit)`.

Related good behavior worth recording: when a spec was physically impossible (W1's brief
wanted an untouched APRIORI *and* a post-request-30 hook, while the hook point is in PEI),
the worker **stopped without improvising** and escalated; the coordinator issued a
documented correction `(src: CLAUDE.md 39 record "RES1")`.

## 8. The owner always knows

A permanent rule from 19/11: at every board measurement and every dispatch the team
explains in plain language **what was read (the numbers), what it means (which hypothesis
died or survived), and what happens next** — the owner only flashes, but never works in the
dark `(src: CLAUDE.md "Regra de comunicação com o dono", 19/11, permanente)`. Each session
also keeps a live diary (`STATUS.md`) and closes with explicit handoffs.

## Sources

- `biosmod_8902_co/CLAUDE.md` — campaign rules, owner directives/aditamentos, communication rule, worker policy.
- `biosmod_8902_co/HANDOFF-FINAL-20261122.md` — house rules (§7), pipeline and lessons (§6), second-opinion process (§8).
- `biosmod_8902_co/RASTRO.md` — master registry: M1–M30, breaches, errata records.
- `biosmod_8902_co/STATUS.md` — diary, including the dated "Parecer do Codex" blocks and dispositions.
- `biosmod_8902_co/trabalhos/39-patch-w1-proxy-unclamp.md` — example pre-registered prediction matrix.
- `biosmod_8902_co/HANDOFF-NOVA-SESSAO-20261120.md`, `HANDOFF-NOVO-MODELO-20261121.md` — model-change handoffs.
- `BUILD-NOTES.md` (this repo) — writer-queue audit: one worker at a time; the W2 brief-conflation catch.
- [docs/05](05-gen4-the-clamp.md), [docs/08](08-smn-probes.md), [docs/10](10-negative-results.md),
  [docs/11](11-build-catalog.md), [docs/14](14-tooling.md) — where the disciplines' results are written up.
