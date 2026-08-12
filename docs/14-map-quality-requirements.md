# 14 — Map quality requirements

What every map **must** have to possibly be good, and what it must not do.
Synthesized 2026-08-11 from:

- the reference corpus of community Workshop maps — all 36 maps measured,
  39 features (**CORPUS**);
- [`docs/13-map-design-research.md`](13-map-design-research.md) — sourced community
  and transferable design theory (**RESEARCH**, with its CONSENSUS/OPINION tags);
- [`docs/04-map-design-rules.md`](04-map-design-rules.md) — the original rules,
  **amended below where measurement disproved them**.

Every requirement is measurable so the validators can enforce it. MUST = build
fails; SHOULD = warning needing review. "Per player" means per strategy-mode
base/player slot.

---

## A. Economy recipe (the least negotiable part of the corpus)

| # | Requirement | Value | Source |
|---|---|---|---|
| A1 | MUST budget economy **per player**, never per km² | 4.5–6.5 geysers and 60–100 scrap per player | CORPUS (5 geysers, 70–120 scrap/base at every base count) ∩ RESEARCH (tournament pool: ~70 scrap/player) |
| A2 | MUST keep total scrap in corpus range | 180–434 pieces | CORPUS (hard floor: no shipping map has fewer than 180) |
| A3 | MUST **pool** scrap, never scatter | pools of ~8–12 pieces, intra-pool nearest-neighbor 5–9 m; whole-map clustering R ≤ 0.25 | CORPUS (lowest-variance feature in the pack: R 0.04–0.22, ~25 pools × ~10) |
| A4 | MUST push scrap outward | ≤ 30% of scrap within 300 m of a base; ≥ 35% beyond 600 m; median pool distance ≥ 450 m | CORPUS (median 516 m, 24% inside 300 m, 46% beyond 600 m) |
| A5 | MUST count **contestable economic sites**, not a contested percentage | 4–5 sites for 2 players; N+2..N+3 for N | RESEARCH (below 3, the first fight decides the game). *Amends docs/04 E5 (“30–50% geysers contested”).* |
| A6 | MUST give every base a **recovery zone** | ≥ 15,000 m² refuge per base, ≤ 5% of map scrap, off the shortest inter-base path | RESEARCH (anti-snowball lever missing from docs/04 entirely; naive fairness optimizers destroy it) |
| A7 | SHOULD decouple the contested center: geysers **without** scrap | center sites = power, not income | RESEARCH (center squatting is self-punishing when it earns nothing) |
| A8 | SHOULD place geysers closer to bases than scrap | geyser median distance < scrap median distance | CORPUS (true on 32/36 maps) |

## B. Spatial layout

| # | Requirement | Value | Source |
|---|---|---|---|
| B1 | MUST separate bases by absolute distance, not map fraction | 1300–1800 m straight-line | CORPUS (median 1533 m @2560, 1603 m @5120; r = +0.03 with size). *Amends docs/04 B2 (“35–60% of diagonal”) — the corpus uses an absolute commute.* |
| B2 | MUST hit a travel-time bin at **20 m/s** (Tank cruise, not Razor flavor text) | shortest drivable path 1800–4200 m ⇒ 90–210 s; declare the bin (Rush &lt;120 s / Standard / Macro &gt;180 s) in the map README | RESEARCH (no corpus ODF exceeds 45 m/s) |
| B3 | MUST provide ≥ 2 topologically distinct base-to-base routes | unchanged | docs/04 C3, corroborated |
| B4 | MUST make the **shortest** route the most exposed | shortest path has the lowest cover score of all routes; if violated, open it up rather than lengthen it | RESEARCH (Quake + StarCraft converge on this independently) |
| B5 | SHOULD mirror the base pockets and **vary the middle** | rot-180 symmetry high near bases, unconstrained centrally | RESEARCH ∩ CORPUS (global symmetry does not predict favorites; three favorites are near-zero) |

## C. Terrain composition (where map character actually lives)

| # | Requirement | Value | Source |
|---|---|---|---|
| C1 | MUST compose landforms, not noise | 100 m high-pass detail std ≤ 35 m (corpus max), target ≤ 15 m | CORPUS (xx01open failed at 49.2 m; corpus median 9.2) |
| C2 | MUST enforce a landmark hierarchy | 1 dominant peak/feature, 3–5 secondary, everything else minor; prominence spectrum must be top-heavy, not flat | RESEARCH (flat prominence = numeric signature of fBm noise) |
| C3 | MUST separate **build terrain from combat terrain** | flat pockets (≥ 4,000 m², slope &lt; 5°) at geyser/base sites; deliberately rough, unbuildable ground between them | RESEARCH (the one doctrine BZ mappers explicitly wrote down) + docs/04 B1 |
| C4 | SHOULD use ruggedness as the character axis | favorites: ~1.5× corpus height std, ~1.8× walls &gt;30° — big and rugged with the standard economy recipe | CORPUS (walls-% spans 56× across the pack; economy barely moves) |
| C5 | MUST keep hovercraft flow | ramps/bowls usable at speed; no slope wall directly behind a spawn | RESEARCH + docs/04 T-rules |

## D. Chokes and combat space

| # | Requirement | Value | Source |
|---|---|---|---|
| D1 | MUST cap choke **length**, not only width | no more than 250 m of continuous sub-60 m corridor before opening out | RESEARCH (long canyons freeze the AI and stall fights; amends docs/04 C4 which only bounded width) |
| D2 | MUST keep the center drivable | full ground connectivity of all bases + all economic sites (docs/04 C1) | corroborated |

## E. Conventions and packaging (corpus-hard)

| # | Requirement | Value | Source |
|---|---|---|---|
| E1 | MUST use `gameType = "K"` | all 36 corpus maps | CORPUS |
| E2 | MUST ship exactly 14 deathmatch spawns in the base `.bzn` | 34/36 maps | CORPUS |
| E3 | MUST declare 1–4 control points in the map `.odf` | 35/36 maps do; 18 declare 4 | CORPUS (xx01open shipped 0) |
| E4 | MUST fill `customtags` | non-empty, comma-separated | CORPUS (33/36) |
| E5 | MUST keep terrain stem ≤ 8 chars, `x*` namespace, full variant set (`base/_S/_ST/_SW`) | engine limit + collision namespace | measured in game (docs/07) |
| E6 | MUST count scrap by `classLabel = "scrap"`, not PrjID prefix | `npscr*` misses `sscr_1` (10 maps) and `blc-pell` (434 on Pac-Man) | CORPUS parser finding |

## F. Anti-requirements — the named failure modes

1. **Uniform scatter economy** (xx01open: R 0.79, 122 pools of 1.2 — worst single
   deviation from the corpus).
2. **Noise terrain** — normal macro stats with out-of-range detail roughness.
3. **Featureless open field** or its inverse, the **map-length canyon** (D1).
4. **All-safe or all-contested scrap** — either kills the mid-game (A4/A5).
5. **Fairness-optimized flatness** — perfect symmetry everywhere; corpus favorites
   don't have it and the optimizer destroys recovery zones (A6).
6. **Short-commute bases** (xx01open: 640 m — half the corpus floor).

---

## What the generator must change (implementation delta)

1. **Economy placer**: replace uniform scatter with a pool-based placer — ~N pools
   of 8–12, Poisson-disc between pools, 5–9 m jitter within; distance-band targets
   from A4; site counter from A5; recovery zone from A6.
2. **Terrain synth**: replace single-scale noise with landform composition —
   place the landmark hierarchy first (C2), carve build pockets (C3), then add
   detail noise bounded by C1's high-pass budget.
3. **Layout**: base separation from B1/B2 (absolute metres, path-time binned),
   route topology B3/B4 checks in the connectivity validator.
4. **Validators**: add every MUST above to Tier 2; A3/C1 are cheap array math.
5. **Packaging**: control points (E3), customtags (E4), classLabel-based scrap
   accounting (E6), and fix `read_trn`'s commented-section-header bug so
   `[TextureType*] // comment` blocks parse.
