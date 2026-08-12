# 16 — START HERE: making a Battlezone map in this repo

**You are an AI agent asked to make a BZ98R map. Read this page, then follow
[`docs/15`](15-map-authoring-policy.md). Everything here was paid for with a
broken build or a play-test.**

## The four documents, in reading order

| Doc | What it gives you |
|---|---|
| **This page** | engine facts, operator preferences, the feedback ledger |
| [`docs/15`](15-map-authoring-policy.md) | the authoring procedure + the "perfect prompt" example |
| [`docs/14`](14-map-quality-requirements.md) | the measurable quality bar (MUST/SHOULD, by ID) |
| [`docs/13`](13-map-design-research.md) | numbers from the reference corpus of community Workshop maps / sourced design theory, when you need the *why* |

## Engine facts that will break your map if you don't know them

1. **Terrain stems are ≤ 8 chars** — the engine truncates script lookups; a
   9-char stem loads with NO script, silently (the final character is dropped
   from the `.lua` lookup). The packer refuses longer stems.
2. **Game assets do not cross workshop items.** ODFs/meshes/sounds/textures
   resolve from the base game + the map's own pack only. Lua crosses via
   RequireFix `package.path`; assets never do. The testing overlay pack
   therefore ships the whole asset layer.
3. **`<stem>MAP.lua` is the per-map script hook** (plus `<stem>_SMAP.lua` etc.
   per variant). Module shape: `local SBPMapScript = {} … return SBPMapScript`.
   The Lua state is SHARED with the SBP modules — their globals (e.g.
   `SIZ_Interval`, `ImpactZoneInterval`) are readable and writable from your
   map script. That is how per-map dynamic behavior is done.
4. **Scrap Impact Zones** are configured in the map `.odf`
   (`[ScrapImpactZone]`: `SIZ_EnableScrapImpactZone`, `SIZ_Interval` seconds,
   `SIZ_OnlyUseSIZPathPoints`) and aimed with BZN **paths named `siz1`–`siz9`**.
   For randomized pacing, re-roll `SIZ_Interval` from the MAP script whenever
   `ImpactZoneInterval` resets (it zeroes after each fire).
5. **Water and lush vegetation are MESHES, not terrain** — and we generate them
   in Python now (no Blender). Texture-painting water/plants "looks nothing like
   Oasis" (operator, correct). Use `bzmap/generate/meshgen.py`:
   `build_water_surface` (Oasis's real water material on a surface that fills
   below a waterline) and `build_plant_field` (alpha billboards). The OGRE
   writer is `bzmap/formats/mesh.py`. See the "Per-map meshes" section below for
   the rules (emissive water so it's not black in shadow; sink plant billboards
   ~2.5 m; ship `.mesh`/`.material`; place the object at origin, team 0).
6. **The in-game map radar renders from the `.LGT` lightmap** — zero-fill
   renders it black. The packer bakes one; never ship zeros.
7. **BZN gotchas** (all packer-repaired, but author correctly): exactly one
   `isUser=1` on the player; the player block is the 74-field craft layout;
   seqnos 1-based; `name = MultSTMission` + `sObject = size+1` trailer;
   teams — player 1, economy/spawns 0, wingman second base 8; never co-locate
   solid buildings (≥ 40 m).
8. **Lives, observer mode, vehicle swaps** run through `exu.dll` +
   shared GAMEMODE scripts, loaded from the subscribed game-mode pack.
   Do not override game-mode modules.

## The operator's calibration (learned from play-tests — treat as policy)

- **"Medium" means 1280 m** to this operator, not the corpus-modal 2560.
  When in doubt about size, go smaller.
- **Terrain monotony is the #1 complaint.** Every map needs: directional
  ridge grain (Hills-of-War style), knolls to hide BEHIND, gullies to hide
  IN, and a dominant landmark. Uniform noise reads as "shit" even when the
  stats pass. More variation than you think is right.
- **Scatter economy reads as broken.** Scrap in pools, always (docs/14 A3).
- **Chokepoints are welcome as identity** — a single land bridge was an
  explicit ask (docs/14 B3 deviation, operator-approved when it IS the map).
- **Impassable must be IMPASSABLE.** Verify topologically: sever the intended
  crossing and assert the halves disconnect. "Steep-ish" gets driven over.
- **Feature widths:** a "narrow" bridge ≈ 40–50 m. An "80 m wide" trench
  means the gap, with walls beyond it.
- Lobby names: **real names**, never slugs. Author line: **Made by
  Skippy** on originals; imports keep their creators' credit. Steam
  description is pinned in the Workshop VDF — edit it there only.
  Title/visibility are web-managed; never add them to the VDF.
- The operator play-tests fast and reports bluntly. Ship small iterations,
  keep the steamcmd command ready, verify the workshop sync (files byte-match)
  before they launch, and read the operator's log bundles for every failure.

## The feedback ledger (what each play-test taught)

| Round | Verdict | Root cause / fix |
|---|---|---|
| "Could not load terrain stock.trn" | template placeholder left in BZNs | TerrainName rule in docs/06 was BACKWARDS; fixed + validated |
| kicked to lobby | no `isUser=1` (blank craft ODF) | player object marked |
| kicked to lobby | player block had 70 fields, not 74 | craft fields inserted |
| kicked to lobby | seqno 0-based | corpus: no seqno 0 exists |
| kicked to lobby | no `MultSTMission` trailer | trailer added |
| scripts dead on map | `require("RequireFix")` unreachable | the testing overlay pack ships RequireFix |
| crash at eject; overlays missing | cross-pack assets; computed names | ship full asset layer |
| minimap blank | all-zero LGT | LGT format reverse-engineered, baked |
| scrap allied green | economy team 1 | corpus: team 0, 24k/24k |
| Monke "wayyy too big" | 2560 as "medium" | operator medium = 1280 |
| Monke scriptless | 9-char stem truncated | 8-char engine limit |
| Trench "shit": passable, wide bridge, no water, monotone | texture-painted water/plants; shallow | deeper trench, sheer walls, narrow bridge, ridges/knolls/gullies |
| plants floating; water invisible; **no scrap on radar** | nearest-cell snap; additive blend; scrap `isVisible=0` | bilinear+sink; alpha_blend; visibility packer pass |
| Scrap Impact Zone never fired | SBP SIZ config path unreliable | self-driven from the map script |
| wingman crash "AssignedSpawnPoint nil" | `_SW` had 2 spawns, needs 14 | packer copies base spawn ring into short `_SW`/`_ST` |
| wingman "wrong side" spawns | `_SW` spawns ALTERNATED sides | side-GROUP spawns: all team-A side (indices 1-7) then team-B (8-14) |
| impact zone stuck "T-998" marker | spawned `impactzn` and never managed it | drop `impactzn`; the meteor+blast+scrap are the visible sequence |
| SIZ script crash "compare nil" | `GetTime()` is nil in the pre-game lobby | guard `if now == nil then return end` at the top of Update |
| SIZ crash line 31 (2nd time) | a `local` decl (RingTimer) silently lost in an edit | build now lints every MAP.lua for undeclared state vars, fails loudly |
| water a small floating sheet | translucent surface below the trench lip | opaque (alpha ~0.9, depth_write on), raised to just under the brim |
| centre feature off the land bridge | meandering trench: bridge middle != map centre | place it at the trench-axis X for that Z, not P_CENTER

## Object-field gotchas that don't crash but ruin the map

These load fine and look done, then fail in play. All are packer-repaired now,
but know them:

- **Scrap needs `isVisible = 1` and `seen = 1`.** The generator emitted `0/0`,
  which made scrap **invisible on radar and untargetable by scavengers** ("no
  scrap on radar"). Corpus scrap and spawns are `1/1`; geysers are `0/0` (leave
  those). Packer pass: `write_bzn_visibility`.
- **Environmental mesh objects are team 0**, not the player's team — the
  corpus `desrten1` water is team 0. A team-1 static building confuses unit/radar logic.
- **Economy teams:** scrap/geysers/spawns team 0, player team 1, wingman
  second base team 8.
- **Wingman/strategy-teams need the FULL spawn ring.** Corpus maps ship base = 14
  `pspwn_1`, `_S` (strategy) = 2, and **`_SW` (wingman) = 14** — because
  wingman/teams modes assign players to spawn-point *numbers*, and a short
  `MapSpawnPoints` list makes `MapSpawnPoints[n]` nil and crashes
  `GAMEMODE_Wingman_Teams.lua` ("attempt to index global 'AssignedSpawnPoint'").
  So: base and `_SW` (and `_ST`) carry ~14 spawns; only `_S` uses 2. The packer
  guarantees it (`write_bzn_team_spawns` copies the base ring into any short
  team variant), but author `_SW`/`_ST` with the full ring directly.
  **The GAMEMODE scripts read spawns by FIXED LINE OFFSET** from the raw BZN text (PrjID at
  `[GameObject]`+2, transform at +20..+42) — so the BZN object block layout is
  load-bearing; clone from a known-good block, never hand-assemble field order.

## Per-map meshes: water, plants, any geometry (AUTOMATED — no Blender)

The operator's water/plant asks are solved by generated OGRE meshes, not
texture painting (texture painting "looks nothing like Oasis" — the operator is
right). The tooling:

- `bzmap/formats/mesh.py` — writes OGRE `MeshSerializer_v1.100` `.mesh` files
  (the BZ98R dialect, reverse-engineered from `desrten1.mesh`). POSITION +
  NORMAL + TEXCOORD, 16-bit indices, world-space vertices.
- `bzmap/generate/meshgen.py` — `build_water_surface` (fills every cell below a
  waterline; uses Oasis's **actual** water material — blue, scrolling
  `thecavew.png`) and `build_plant_field` (alpha cross-billboards using the
  `EoPlnt01` bush texture).

Rules learned shipping the first ones:

- Place ONE static object per mesh at world origin `(0,0,0)`, team 0, PrjID ==
  the mesh stem (≤ 8 chars); the engine binds `<PrjID>.mesh` by name. Add it to
  every variant BZN. ODF class `i76building2` (static geometry).
- **Ship `.mesh`/`.material`/`.dds`** — they're in the assembler whitelist now,
  but a per-map mesh with a non-whitelisted suffix is silently dropped.
- **Water must be `scene_blend alpha_blend`, not additive** — additive water is
  near-invisible over dark ground. Referenced textures must ship (or be
  base-game like `BZBase.material`, which every material imports).
- **Plants: bilinear-sample the ground and sink the base ~1.5 m** — nearest-cell
  sampling floats billboards over the engine's smooth terrain.
- **Heightfield relief caps at ~390 m** (12-bit). A "10× deeper" trench past
  that can't coexist with a playfield — raise the playfield, drop the floor, and
  say so; don't silently clip.

## Scripting the impact zone / dynamic events

- The SBP **Scrap Impact Zone config** (`[ScrapImpactZone]` odf + `siz1`–`siz9`
  BZN paths) **did not fire in testing** — its state machine has conditions
  that are hard to satisfy and untestable offline. **Drive timed events from
  the map script instead** (`GetTime()` + `BuildObject`), like the Fury spawner.
  Full impact sequence (match the SBP one): ~15 s before, `BuildObject("SIZ", ...)`
  (the falling-meteor visual) and pulse `MakeExplosion("SBPRminE", ...)` for the
  red danger rings; on impact remove the meteor, `MakeExplosion("SIZxpl", pos)`,
  `BuildObject("impactzn", 0, pos)`, `BuildObject("sfieldC", 0, pos)` (scrap).
  Set `SIZ_EnableScrapImpactZone = 0` so the SBP one doesn't fight yours.
- Map-script globals are SHARED with the SBP modules, but prefer owning your own
  timer state to reading theirs — it's testable and can't be starved by their
  conditions.

## Verification before you say "done"

`luac5.1 -p` every lua · packer exit 0 · docs/14 MUST table with measured
values · topological tests for any intended im/passability · state plainly
that nothing is verified in-game until the operator plays it. Full procedure:
docs/15 §4–5.


(See plant-float note in the mesh section.)

## Debug render — verify geometry WITHOUT launching the game

`python -m bzmap.render.debug_map build/<map>` writes `<map>.debug.png`: shaded
terrain + water-mesh footprint + colour-coded object dots + legend. The authored
builds emit one automatically. It catches placement bugs (off-centre features,
wrong-side spawns, water pooling outside the trench, stacked buildings) that
otherwise cost a play-test. The same top-down render now feeds the **lobby thumbnail** (`.BMP`/`.png`, with water) and the **radar map** (the `.LGT` bake darkens water cells), so both in-game pictures show the actual map. **Use it before every upload.** Reading the PNG back
is how an agent 'sees' the map. It already caught water pooling in every gully
(fix: pass a `region_mask` to `build_water_surface` to confine water to the
trench).
