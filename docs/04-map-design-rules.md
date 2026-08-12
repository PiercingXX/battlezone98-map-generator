# 04 — Map design rules

**This is the hard part.** File formats are solved. Whether a generated map is *good*
is the actual research question, and the strategy here is to convert as much of "good"
as possible into things a machine can measure.

Everything below is either measured from the reference corpus of community Workshop maps
or derived from it. Numbers marked **[corpus]** come from direct measurement and terrain
analysis of the corpus maps.

---

## 1. Terrain shape

### Measured slope profiles **[corpus]**

Slope here = `atan(Δheight / 5 m)` between adjacent grid cells.

| Map | size | median slope | p90 | %<5° | %<10° | %<15° | %<30° |
|---|---|---|---|---|---|---|---|
| `umoonwar` | 1280 | 4.6° | 27.5° | 54.8 | 71.7 | 80.2 | 91.8 |
| `uhecave` | 2560 | 4.6° | 38.7° | 52.9 | 65.4 | 73.7 | 85.3 |
| `bltop04` | 5120 | 10.2° | 39.4° | 35.5 | 49.3 | 62.4 | 82.9 |
| `uexmap10` | 2560 | 24.7° | 64.7° | 18.6 | 24.9 | 33.5 | 58.0 |

The spread is real and meaningful: `uhecave` and `umoonwar` are *open* maps, `uexmap10`
is a *canyon* map where most of the surface is wall. Both play. So there is no single
correct slope profile — but there is a **floor**:

> **Rule T1.** At least **18%** of the map must be under 5° slope, and that flat area
> must be *connected* and *distributed*, not one big plateau in a corner.

The 18% figure is the corpus minimum (`uexmap10`). Below that, there is nowhere to build.

### Base elevation

> **Rule T2.** The play surface sits on a plateau at nonzero raw height. Target a modal
> raw height of **500–1500** (50–150 m). Do not build up from 0.

Raw 0 means *undefined*, not sea level (see `docs/01`). Stock maps: `uexmap10` modal 988,
`uhecave` 1371, `umoonwar` 153. Starting at a mid-range plateau leaves headroom to carve
canyons downward as well as raise ridges.

> **Rule T3.** Never saturate. Keep the 99th percentile below raw 3900 (390 m); the
> 12-bit ceiling is 4095 and clipping produces flat-topped mesas that look broken.

### Boundaries

The traversable area is smaller than the terrain extent — `uesrtst1`'s own description
says *"Map Size: 1000mx1500m (traversible area)"* on a 2560 m terrain.

> **Rule T4.** Ring the playable basin with impassable terrain (>45° sustained). Do not
> let players drive to the literal edge of the heightmap.

---

## 2. Economy placement

### Density scales inversely with size **[corpus]**

Scrap total is roughly constant (~200–300 objects) regardless of terrain size, so large
maps are deliberately sparser.

> **Rule E1.** Geysers: target **1.5/km²** (corpus median). Stay inside 0.5–6.4/km².
> Practically: 2560 m → 12–20 geysers; 3840 m → 15–20; 5120 m → 12–25.

> **Rule E2.** Scrap: target **250–300** `npscr*` objects regardless of map size. Mix
> `npscr1/2/3` freely; the corpus uses all three in similar proportions
> (`uexmap10`: 95 / 102 / 83).

> **Rule E3.** Geysers must sit on ground that is **buildable** — slope under 5° across
> at least a 20 m radius. A geyser on a cliff face is dead economy and reads instantly
> as machine-generated.

### Fairness

> **Rule E4.** Per-base economy must be within **5%** across bases. Assign every geyser
> and scrap pool to its nearest spawn cluster by *path* distance (not straight-line) and
> compare totals.

> **Rule E5.** Contested economy is the point. **30–50%** of geysers should be
> roughly equidistant from two or more bases (within 15% path distance). A map where
> every geyser is safely inside someone's base has no reason to fight over.

---

## 3. Bases and spawns

> **Rule B1.** Each base needs a contiguous buildable pocket of **≥ 4,000 m²** with
> slope under 5° — enough for a recycler plus a real production line.

> **Rule B2.** Base separation: path distance between nearest bases should be
> **35–60%** of the map diagonal. Closer is a rush-fest; further and the game never
> starts.

> **Rule B3.** Spawn clusters: `_SW`/deathmatch = **14 spawns in `N_teams` clusters**.
> Within a cluster, spawns 12–70 m apart **[corpus: `uexmap10` min spacing 47 m]**,
> facing outward toward the map centre. `_S` = one spawn per strategy player.

> **Rule B4.** Bases must not have line-of-sight to each other at spawn. Check by
> ray-marching the heightmap between base centres — terrain must occlude.

---

## 4. Connectivity — the hard failure conditions

These are pass/fail, not tuning. A map that fails any of these is broken, however
pretty it looks.

> **Rule C1 — Full connectivity.** Every base, geyser and scrap pool must be reachable
> from every base by a ground path over terrain with slope ≤ 30°. Compute with a flood
> fill / A* over the 5 m grid. **Any unreachable economy object is a hard error.**

> **Rule C2 — No traps.** No enclosed pocket of traversable ground larger than 200 m²
> that connects to the rest of the map only through terrain steeper than 30°. Units
> drive in and cannot get out.

> **Rule C3 — Multiple approaches.** At least **2 topologically distinct** routes
> between any pair of bases. Verify by computing a shortest path, deleting a 30 m-wide
> corridor around it, and re-running the search — a second path must still exist.
> Single-corridor maps degenerate into one permanent stalemate at the choke.

> **Rule C4 — Chokepoint sanity.** No corridor on a main route narrower than **30 m**.
> Battlezone vehicles have real turning radii; narrower than this and pathfinding jams.
> **[INFERRED from vehicle scale — confirm in playtest, see docs/09.]**

---

## 5. Symmetry

The corpus is *not* strictly mirror-symmetric — these are hand-made maps with
asymmetric terrain and balanced economy. Two options:

- **Enforced symmetry** (rotational 180° or mirror): guarantees fairness, costs
  character, reads as generated. Good for 1v1.
- **Asymmetric terrain + balanced economy**: matches the corpus, needs Rules E4/E5 and
  B1/B2 to carry the fairness burden.

> **Rule S1.** For 1v1 `_S` maps, use **180° rotational symmetry** for the first
> generation. It makes fairness provable and removes a whole class of balance bugs.
> Prefer rotational over mirror — mirror symmetry produces unnatural matched pairs of
> landmarks that look obviously artificial.

> **Rule S2.** For 3+ player maps, use N-fold rotational symmetry about the map centre.

Break symmetry deliberately later, once the pipeline is trusted — not in the first ten.

---

## 6. What the validators cannot judge

Be honest about the limit. These require a human and are the reason for the playtest
gate in `docs/08`:

- **Pacing** — does the first engagement happen at a good time?
- **Readability** — can a player tell where they are without the map screen?
- **Visual character** — does it look like a place, or like filtered noise?
- **Sniping and sightlines** — several corpus maps are tagged `snipe`; long sightlines are
  a deliberate design choice, and the validators cannot tell "good sniping map" from
  "featureless plain".

Generation should produce **candidates**; validators cull the broken ones; a human picks
the ten that ship. Expect to generate substantially more than ten — plan for a 3:1 or
4:1 cull ratio and treat that as normal, not as failure.

---

## 7. Suggested generation approach

Not prescriptive — the agent may find better. But a sane starting point:

1. **Layout graph first, terrain second.** Place base sites and economy nodes as a
   graph, verify Rules B/E/C on the graph, *then* synthesise terrain that realises it.
   Generating noise and hoping a good layout falls out of it will waste most of the run.
2. **Carve, don't accumulate.** Start from a plateau at raw ~1000 and subtract canyons
   and basins. This naturally satisfies T2/T3 and gives connected flat ground for free.
3. **Erosion pass** for natural-looking slopes (`scipy` is already a WorldBuilder dep).
4. **Flatten base pockets and geyser pads explicitly** after erosion — do not hope they
   came out flat. Rules B1 and E3 are cheap to guarantee and expensive to fix.
5. **Validate, then place objects**, so object placement can rely on final terrain.
