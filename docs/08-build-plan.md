# 08 — Build plan

Seven phases. Each has a hard acceptance gate. **Do not start a phase before its
predecessor's gate passes** — the ordering exists because each phase's correctness
depends on the last one being actually right rather than approximately right.

Effort figures assume a competent agent working with the specs in this repo.

---

## Phase 0 — Environment and ground truth
**~0.5 day**

- Python venv with `numpy`, `scipy`, `Pillow`, `imageio` (none currently installed).
- Vendor WorldBuilder under `third_party/`.
- Snapshot read-only copies of the reference corpus of community Workshop maps and the
  stock `Edit/trn` templates.
- Capture baseline `BZLogger.txt` / `BZOgreLogfile.log` from a clean stock-map launch,
  for later diffing.

**Gate:** a script can enumerate all 36 corpus maps and print size, variants and object
counts.

---

## Phase 1 — Formats layer
**~3 days. The highest-risk phase; do not rush it.**

Implement `formats/`: `hg2`, `mat`, `lgt`, `trn`, `bzn`, `des`, `ini`, `odf`, `vxt`.

**Gate (all must pass):**
1. All **128** corpus `.bzn` files parse and re-emit **byte-identically**.
2. All **36** `.HG2` files round-trip byte-identically.
3. `HeightMap.sample_m()` agrees with stock object Y positions within **1.5 m**
   across ≥3 maps of different sizes.
4. `.trn` round-trips with comments and ordering preserved.

If a BZN will not round-trip, quarantine it with a written explanation. Do not loosen
the test to make it pass.

---

## Phase 2 — Renderer and inspection
**~1 day. Cheap, and it pays for itself immediately.**

Top-down shaded terrain render with object overlay; connectivity and economy overlays.

**Gate:** render all 35 stock maps. They must look like coherent places. This doubles as
an independent check that Phase 1's zone-major decoding is right — a layout bug is
instantly obvious in a render and nearly invisible in a hex dump.

---

## Phase 3 — First generated map, end to end
**~2 days**

The narrowest possible slice: one hand-specified 2560 m map. Hard-code the layout —
two bases, a handful of geysers and scrap. No procedural generation yet.

Produce a full file set, install to a test mod dir, launch, load it.

**Gate:**
1. The map loads in-game in all three variants.
2. No new errors in `BZLogger.txt` or `BZOgreLogfile.log` vs. the Phase 0 baseline.
3. The in-game Lua harness confirms engine object positions match authored positions.
4. A human drives around it and confirms terrain, geysers and scrap are where the
   preview render says they are.

**This is the phase that proves the whole thesis.** Everything before it is inference;
this is the first time the engine agrees. Resolve the `.LGT` question here
(`docs/09` E1) — it is the last unknown that can block loading.

---

## Phase 4 — Validators
**~2 days**

Implement Tiers 1 and 2 from `docs/06`.

**Gate:**
1. **All 35 stock corpus maps pass every error-severity check.** Non-negotiable — this is
   the calibration test.
2. The expected-warning baseline for stock maps is recorded.
3. Deliberately broken fixtures (disconnected geyser, unbuildable base, trap pocket,
   flat-map with 0% buildable) are each caught by the right rule.

Point 3 matters as much as point 1: a validator that passes everything is
indistinguishable from no validator at all.

---

## Phase 5 — Generation
**~4 days. The open-ended one.**

Layout graph → terrain synthesis → economy → spawns → variants, per `docs/04` §7.

**Gate:**
1. 20 candidates generated from 20 seeds.
2. **≥10 pass all error-severity checks.** (A 3:1 or 4:1 cull is expected and fine —
   if the pass rate is far below that, fix generation rather than loosening validators.)
3. Renders show visibly distinct layouts, not one layout re-rolled.
4. Fixed seed reproduces byte-identical output.

---

## Phase 6 — The ten maps
**~3 days**

Generate a large candidate pool, cull, curate to 10 meeting the diversity requirement in
`docs/00`: ≥3 terrain sizes, ≥4 worlds, ≥3 layout archetypes, ≥2 non-1v1.

Name them, write descriptions and thumbnails, playtest each.

**Gate:**
1. 10 maps, all validators clean.
2. Each loads in-game in every shipped variant, no new log errors.
3. **Each played by a human and judged playable.**
4. Diversity requirement satisfied and documented.

---

## Phase 7 — Package
**~1 day**

Assemble the pack per `docs/07`. Verify terrain-name collisions against installed
Workshop content and the base game. Write the Workshop description.

**Gate:** pack assembled and validated; upload left as a human step.

---

## Summary

| Phase | Effort | Risk |
|---|---|---|
| 0 Environment | 0.5 d | low |
| 1 Formats | 3 d | **high** — BZN round-trip |
| 2 Renderer | 1 d | low |
| 3 First map end-to-end | 2 d | **high** — LGT, engine acceptance |
| 4 Validators | 2 d | medium — calibration |
| 5 Generation | 4 d | **high** — open-ended quality |
| 6 Ten maps | 3 d | medium |
| 7 Package | 1 d | low |

**~16.5 working days.** Phases 1, 3 and 5 hold essentially all the risk.

The plan front-loads the two questions that could sink the project — "can we write a
BZN the engine accepts?" (Phase 1+3) and "can we generate terrain worth playing?"
(Phase 5). If Phase 3 fails, that is known by roughly day 7, having spent nothing on
generation infrastructure that would have been wasted.
