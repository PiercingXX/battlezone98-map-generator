# Battlezone 98 Map Generator

An AI map-generation toolchain (**`bzmap`**) and its packaging pipeline for
*Battlezone 98 Redux* (Steam AppID `301650`) multiplayer maps.

**Goal:** generate original, playable BZ98R multiplayer maps that clear a
measurable quality bar, and package them as a standalone Steam Workshop
expansion pack.

The toolchain covers the full pipeline: layout → terrain → economy → spawns →
variants generation, binary/text format writers for every file a map ships,
offline validators (structure, connectivity, balance), debug rendering, and
pack assembly.

---

## Read this in order

| Doc | What it covers |
|---|---|
| [`AGENTS.md`](AGENTS.md) | **Start here.** Operating rules for the build agent. |
| [`docs/00-project-brief.md`](docs/00-project-brief.md) | Scope, deliverables, definition of done. |
| [`docs/01-file-formats.md`](docs/01-file-formats.md) | Verified binary/text format specs (HG2, MAT, LGT, TRN…). |
| [`docs/02-bzn-spec.md`](docs/02-bzn-spec.md) | The BZN mission-file writer spec (implemented: `bzmap/formats/bzn.py`). |
| [`docs/04-map-design-rules.md`](docs/04-map-design-rules.md) | What makes a map playable and fair, as measurable criteria. |
| [`docs/05-architecture.md`](docs/05-architecture.md) | Module breakdown and data flow. |
| [`docs/06-validation.md`](docs/06-validation.md) | Offline validators + the in-game test harness. |
| [`docs/07-packaging.md`](docs/07-packaging.md) | Expansion-pack layout and Workshop publish. |
| [`docs/08-build-plan.md`](docs/08-build-plan.md) | Phased milestones with acceptance criteria. |
| [`docs/09-open-questions.md`](docs/09-open-questions.md) | Unknowns, risks, and the experiments that resolve them. |
| [`docs/13-map-design-research.md`](docs/13-map-design-research.md) | Sourced map-design research: BZ community wisdom + transferable theory. |
| [`docs/14-map-quality-requirements.md`](docs/14-map-quality-requirements.md) | **The bar.** Measurable requirements every map must meet to possibly be good. |
| [`docs/15-map-authoring-policy.md`](docs/15-map-authoring-policy.md) | **The policy.** How an agent turns an operator's idea into original maps. |
| [`docs/16-START-HERE-map-making.md`](docs/16-START-HERE-map-making.md) | **START HERE for map-making agents**: engine facts, operator calibration, the feedback ledger. |

`reference/` holds extracted ground-truth data (verbatim BZN templates).

---

## The one-paragraph version

A BZ98R multiplayer map is ~12 files sharing a basename (**≤ 8 characters** —
an engine limit, not a convention; longer stems load scriptless). The mission
file (`.bzn`) is **plain ASCII**, declaring `binarySave = false`. Terrain is a
`.HG2` heightmap (zone-major 256×256 blocks, 5 m grid, `height_m = raw × 0.1`)
plus a `.LGT` baked lightmap (format resolved in docs/01: one constant ambient
plane + per-zone shading; the in-game map radar renders from it). The map's
`.lua` is standard boilerplate. The BZN writer exists (`bzmap/formats/bzn.py`,
template-and-mutate) — as predicted, the file formats were the easy part.

The hard part is generating maps that *play well*. That is now specified
measurably: [`docs/14-map-quality-requirements.md`](docs/14-map-quality-requirements.md)
(the bar, from a 36-map corpus audit + sourced design research) and
[`docs/15-map-authoring-policy.md`](docs/15-map-authoring-policy.md) (how an
agent turns an operator's idea into an original map that clears it).

---

## Provenance of the facts in this repo

Everything in `docs/01`–`docs/04` was measured directly from the installed game
and a reference corpus of community Workshop maps on 2026-08-10, not taken from
documentation or recalled. Where a claim is inferred rather than verified, it is
labelled **INFERRED** inline. Where something is unknown, it is in
`docs/09-open-questions.md` rather than guessed at.

A second measurement wave (2026-08-11) produced `docs/13`–`docs/15`, measured
against a pinned snapshot of the corpus and against live in-game test sessions.
Several docs/01–07 claims were corrected in the same wave, each marked
**[CORRECTED]**/**[RESOLVED]**/**[CONFIRMED]** inline — reality won five times
(TerrainName rule, LGT format, thumbnail formats, the 8-character stem limit,
per-map `.png`).

Sources measured:

- Game: `~/.steam/steam/steamapps/common/Battlezone 98 Redux` (v2.2.301, Steam)
- A 36-map corpus of community Workshop multiplayer maps
- Shipped tools: `Edit/MakeTRN.exe` v2.1.2, `Edit/MakeMAP.exe`, `Edit/MakeZFS.exe`

## Upstream projects (credit + reuse)

- [`GrizzlyOne95/Battlezone98Redux_WorldBuilder`](https://github.com/GrizzlyOne95/Battlezone98Redux_WorldBuilder) — Python; generates TRN/HG2/MAT, atlases, skyboxes. **Reuse this.** MIT.
- [`GrizzlyOne95/bzfile`](https://github.com/GrizzlyOne95/bzfile) — Lua file I/O inside the game. Enables the in-game test harness.
- [`GrizzlyOne95/ExtraUtilities`](https://github.com/GrizzlyOne95/ExtraUtilities) — `exu.dll`; extra Lua engine queries.
- [`GrizzlyOne95/Battlezone98Redux_Shim`](https://github.com/GrizzlyOne95/Battlezone98Redux_Shim) — OpenShim runtime patch layer. Not required, but the escape hatch if engine-level hooks are ever needed.
