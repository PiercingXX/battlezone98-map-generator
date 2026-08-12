# 00 — Project brief

## What we are building

A toolchain that lets an AI agent generate complete, playable, balanced **multiplayer
maps** end-to-end: terrain, object placement, metadata, thumbnails, and
packaging — with automated validation strong enough that a human only has to judge
*feel*, not correctness.

## Deliverables

### D1 — The toolchain (`bzmap/`)
A Python package that can read, write, validate and generate every file in a corpus map.
See `docs/05-architecture.md`.

### D2 — The Expansion Pack
A standalone Steam Workshop item containing **10 new maps**. See `docs/07-packaging.md`.

Each of the 10 maps ships with:
- a terrain set (`.trn`, `.HG2`, `.MAT`, `.LGT`, `.vxt`)
- **at minimum** the `_S` (Strategy) and `_SW` (Wingman Teams) BZN variants, plus the
  base deathmatch `.bzn`
- `.ini`, `.des`, `.odf`, `.lua`, and a `.png` thumbnail

### D3 — The maintainer package
A separate, clearly-scoped set of experimental changes and findings to hand to the
pack maintainer for possible upstream inclusion.

## Scope boundaries

**In scope:** map generation, validation, packaging, and the test harness.

**Out of scope** (do not build these):
- New units, weapons, ODFs, meshes, or textures. We ship *maps*, using the existing
  asset set. Custom terrain atlases are the one exception, and only if a map needs a
  world that does not already exist.
- Changes to upstream Lua modules. Anything we want changed there goes to the maintainer
  as a proposal (D3), not as a fork.
- Campaign or single-player mission scripting.
- Engine patches, OpenShim work.

## Definition of done

The project is done when **all** of the following hold:

1. Round-trip test passes: every stock corpus `.bzn` parses and re-emits byte-identically.
2. All 10 maps pass the full offline validator suite with zero errors.
3. All 10 maps load in-game without errors in `BZLogger.txt`, in every variant shipped.
4. Each map has been played at least once by a human and judged playable.
5. The pack is assembled, thumbnailed, and ready to upload (upload itself is a human step).
6. The maintainer package (D3) is written and self-contained.

## The diversity requirement

Ten maps generated from one algorithm with ten seeds is a failure condition, not a
success. The 10 maps must span:

- **At least 3 distinct terrain sizes** from {1280, 2560, 3840, 5120} m.
- **At least 4 distinct worlds/atlases** (the corpus uses Mars, Venus, Europa, Io,
  Achilles, Ganymede, Elysium, Titan, Moon — see `Edit/trn/` for stock terrain templates).
- **At least 3 distinct layout archetypes** — e.g. canyon-network, open-basin-with-
  chokepoints, plateau-and-valley. Do not ship ten canyon maps.
- **A spread of player counts** in the `_S` variant: the corpus median is 2 (1v1), but
  3-, 4- and 5-player strat maps all exist. Ship at least two non-1v1 maps.

## Why this is worth doing

The received wisdom is that this is not possible. It is worth being precise about why
that belief exists and where it is actually right:

| The claim | Reality |
|---|---|
| "BZN is a binary format you can't write" | False. Mission files in the reference corpus of community Workshop maps are ASCII (`binarySave = false`). |
| "There's no map editor outside the game" | Mostly false. `MakeTRN.exe` ships with the game; WorldBuilder covers terrain. |
| "Nobody has ever written a BZN writer" | **True.** This is the real gap, and it is the core of D1. |
| "An AI can't design a map that plays well" | **Partly true, and the real risk.** Mitigated by making quality measurable — see `docs/04`. |

The honest summary: the file formats are a solved problem that nobody had bothered to
solve. Map *quality* is the actual research question, and it is why validation
(`docs/06`) is weighted as heavily as generation.
