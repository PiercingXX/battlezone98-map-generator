# 15 — Map authoring policy

Standing orders for **any AI agent when the operator asks for a map
or a set of maps.** The operator supplies the *idea*; this policy turns it into
an original, shippable map that clears the quality bar. Follow it in order.

The two source documents, in authority order:

1. [`docs/14-map-quality-requirements.md`](14-map-quality-requirements.md) — the
   bar. Every MUST is a build gate.
2. [`docs/13-map-design-research.md`](13-map-design-research.md) — the *why*;
   consult it when a requirement conflicts with the operator's idea. When in
   doubt about a number, use the corpus median.

---

## 0. The prime rules

- **The operator's idea is the map's identity.** Requirements shape it; they never
  replace it. If the idea and a MUST collide, say so in one sentence, propose the
  closest compliant version, and build that — do not silently drop either.
- **Original means original.** The corpus supplies *ranges*, never layouts. Never
  clone or near-clone an existing map's geometry. Before building, write one
  sentence: "This map is about ___." If you can't, you don't have a design yet.
- **Never claim a map works in-game without an in-game run.** Offline validation
  is stated as offline validation. The operator play-tests.

## 1. Parse the brief

Extract from the operator's request; apply defaults for anything unspecified:

| Parameter | Default if unstated |
|---|---|
| World/theme | pick to fit the idea; use a stock `Edit/trn/<world>.trn` template |
| Size | 2560 m (corpus modal size) |
| Players/bases | 2 bases (two-team strategy) |
| Travel bin (docs/14 B2) | Standard (120–180 s at 20 m/s) |
| Gimmick/scripting | none |
| Name | ask only if nothing in the brief suggests one; otherwise coin it |

Restate the parsed brief in one short block before building, so the operator can
veto cheaply.

## 2. Design order of operations

Skeleton before terrain, terrain before economy, economy before script. Each step
consumes the previous one's output — never reorder.

1. **Layout skeleton.** Place base pockets (mirrored — docs/14 B5) at
   1300–1800 m separation (B1) hitting the travel bin (B2). Plan the route graph:
   ≥ 2 distinct routes (B3), shortest = most exposed (B4). Mark 4–5 contestable
   economic sites for 2 players, N+2..N+3 otherwise (A5), and one recovery zone
   per base, off the shortest path (A6).
2. **Terrain.** Landmarks first: one dominant feature, 3–5 secondary (C2) — the
   operator's idea usually *is* the dominant feature. Compose landforms around
   them; carve flat build pockets at every base and geyser site (C3, ≥ 4,000 m²,
   < 5° slope); then add detail noise **within the C1 budget** (100 m high-pass
   std ≤ 35 m, target ≤ 15). Choose a ruggedness level deliberately — it is the
   character axis (C4). Cap choke runs at 250 m of sub-60 m corridor (D1).
3. **Economy.** Budget per player: 4.5–6.5 geysers, 60–100 scrap (A1), total
   scrap ≥ 180 (A2). Place scrap **in pools** of 8–12 pieces, 5–9 m
   nearest-neighbor inside a pool (A3), distance-banded per A4 (≤ 30% within
   300 m of a base, ≥ 35% beyond 600 m). Geysers closer in than scrap (A8);
   center sites get geysers without scrap (A7). Ground-snap everything.
4. **Gimmick/scripting**, if the brief has one. Ship it as `<stem>MAP.lua` plus
   identical copies for each variant (`<stem>_SMAP.lua`, `_ST`, `_SW`) — the
   engine probes per-variant. Follow the corpus module shape (`local SBPMapScript = {}
   … return SBPMapScript`; see `uhecaveMAP.lua`). Bound every spawner (alive cap,
   fixed period); compile-check with `luac5.1 -p`.
5. **Metadata.** Author line is **Made by Skippy**, never anything else; `customtags` non-empty
   (E4); 1–4 control points in the `.odf` (E3); `.des` GEYSERS/SCRAP counts must
   equal the actual `_S` objects — count scrap by `classLabel = "scrap"` (E6).

## 3. Hard file-format constraints (the traps ledger)

Every one of these was learned by shipping a broken map. All are enforced or
repaired by the packer, but **author files correctly —
the packer's fix-up passes are safety nets, not authoring tools.**

- Terrain stem: **≤ 8 chars** (engine truncates script lookups — a 9-char stem
  loads scriptless), `x*` namespace, collision-checked against installed content.
- Full file set per map: `.trn .hg2 .mat .lgt .vxt .bzn(_S/_ST/_SW) .ini .des
  .odf` (+ `.BMP`/`.png` rendered by the packer).
- **Spawn points per variant:** base and `_SW`/`_ST` carry ~14 `pspwn_1`; only
  `_S` uses 2. Too few in a team variant crashes wingman mode (docs/16). The
  packer backfills, but author them right.
- `.trn`: template from the **stock** world file (`Edit/trn/<world>.trn`), patch
  `[Size]` to origin; know the world's `[TextureType*]` semantics before painting
  the `.MAT` (e.g. Io: 0 ground, 1 Lava Pool, 4 Hardened Lava).
- `.bzn`: clone blocks from a known-good map (template-and-mutate — AGENTS.md
  rule 3). `TerrainName` = stem; exactly one `isUser = 1` on the
  player; player block carries the 74-field craft layout; seqnos 1-based and
  unique; `size`/`seq_count` coherent; `name = MultSTMission` +
  `sObject = size+1` trailer; teams: player 1, scrap/geysers/spawns 0, wingman
  second base 8.
- **Never co-locate solid buildings** — ≥ 40 m separation (interpenetrating
  solids never come to rest and churn collision state every frame).
- `.LGT`: zero-fill is acceptable in `build/<stem>/` — the packer bakes a real
  lightmap — but never ship zeros directly (black in-game minimap).
- Determinism: fixed RNG seeds, recorded in the build script; no wall-clock.

## 3b. Render and LOOK before you validate

The packer emits a top-down debug PNG per map to the build debug directory (terrain + water + object dots + legend), and the lobby thumbnail and radar are generated from the same render. **Read the debug PNG back and verify geometry** (features centred, spawns on the right side, water only where intended) before claiming anything — it catches placement bugs without a play-test.

## 4. Validation gates — before telling the operator anything is done

1. `luac5.1 -p` on every shipped `.lua`.
2. The packer build completes with exit 0 and picks the map up.
3. Structural self-check on every `.bzn` (the checks in §3; the verification
   snippets in this repo's history show the shape).
4. Every docs/14 **MUST** measured and passing; **SHOULD** violations listed
   explicitly in the report, with the reason.
5. Tier 2 validators (`bzmap/validate/`) where they apply.

## 5. Report format

One block per map: the identity sentence; the parsed brief; a table of docs/14
requirement → measured value → pass/fail; SHOULD deviations with reasons; what is
**not** verified (always includes "not yet loaded in game" until the operator has
run it). Then stop and wait for play-test feedback — do not iterate speculatively.

## 6. Sets of maps

When asked for N maps: N distinct identity sentences first (AGENTS.md rule 6 —
ten maps means ten *distinct* maps; vary the character axis: ruggedness, travel
bin, route topology, world). Get a nod on the list if N > 3, then build each map
through §§1–5 independently. A set shares the recipe, never the layout.

---

## Appendix — the "perfect prompt" example

An operator prompt does not need every field below — the policy fills defaults —
but the more of these it pins, the less the agent guesses. This example pins
everything worth pinning. Copy it, delete what you don't care about, and keep
the *identity sentence* above all else.

> **Make me a map called `xxRift01`, lobby name "Meridian Rift".**
>
> **Identity (one sentence):** two mining outposts race to control a collapsed
> canyon rim where all the scrap fell — whoever holds the rim road chokes the
> other's economy.
>
> **World & mood:** Ganymede palette, dusky; rugged (favorites-tier: ~1.5×
> corpus height variance) but with clean flat build pockets — combat ground
> rough, build ground flat, sharply separated.
>
> **Size & pace:** 2560 m. Standard travel bin — 120–180 s base-to-base at
> tank speed (20 m/s), so path length 2400–3600 m. Bases mirrored, ~1500 m
> apart straight-line.
>
> **Terrain composition:** ONE dominant landmark — the collapsed rim, a
> crescent-shaped scarp sweeping through the middle third; 3–4 secondary
> features (a mesa behind each base, two watchtower knolls on the flanks);
> everything else minor. Detail roughness inside corpus limits (≤ 35 m
> high-pass at 100 m scale — landforms, not noise). Rim the map edge
> impassable.
>
> **Routes:** exactly 3 base-to-base routes: the rim road (shortest, MOST
> exposed — no cover on it), and two flank valleys (longer, more cover). No
> choke longer than 250 m under 60 m wide. No route sees a base from spawn.
>
> **Economy:** per-player recipe — 5 geysers and ~85 scrap per player, 2
> players. Scrap in pools of 8–12 (5–9 m spacing inside a pool), pushed
> outward: ≤30% within 300 m of a base, the biggest pools ON the contested
> rim. 5 contestable sites total. Geysers closer in than scrap; the two rim
> sites get geysers with NO scrap beside them. One low-value recovery pool
> tucked behind each base, off every route.
>
> **Mechanics:** Scrap Impact Zones every ~5 min, path-pinned to the two rim
> sites only (`siz1`/`siz2` + `SIZ_OnlyUseSIZPathPoints`). No other scripting.
>
> **Metadata:** customtags "strat, rim, chokepoint, ganymede"; .des blurb that
> sells the identity in two lines; Made by Skippy; control points at the rim
> sites and both mesas.
>
> **Deviations I pre-approve:** none — flag anything that can't hit docs/14
> and propose the closest compliant version before building.
>
> **What done means:** luac-clean, packer builds it, every docs/14 MUST
> measured and shown to me in the report table, and you tell me plainly it has
> never been loaded in game.

Why this prompt works (the checklist behind it):

1. **Identity first** — one sentence an agent can test every decision against.
2. **Every number is a docs/14 requirement**, not taste: travel bin (B2), base
   separation (B1), pool shape (A3), distance bands (A4), site count (A5),
   recovery zones (A6), center-geyser rule (A7), landmark hierarchy (C2),
   detail budget (C1), choke length (D1), exposed-shortest-route (B4).
3. **The routes are named and counted** — route topology is the thing agents
   most often leave implicit, and it is the map.
4. **Mechanics name the engine feature** (SIZ path points), not a wish.
5. **Deviations are pre-cleared or forbidden explicitly**, so the agent knows
   whether to ask or to comply.
6. **"Done" is defined** — including the honesty clause about in-game testing.
