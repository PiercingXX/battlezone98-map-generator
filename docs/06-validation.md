# 06 — Validation

Three tiers, cheapest first. A map must clear each tier before it reaches the next.

| Tier | Cost | Catches |
|---|---|---|
| 1. Structural | ms | malformed files, broken invariants |
| 2. Design | seconds | unplayable/unfair layouts |
| 3. In-game | minutes | everything the first two cannot model |

---

## Tier 1 — Structural

Pure file correctness. Zero tolerance: any failure is a hard error.

### Round-trip
- Every `.bzn` in the reference corpus of community Workshop maps parses and re-emits
  **byte-identically** (128 files).
- Every stock `.HG2` round-trips byte-identically (36 files).

### Per-map invariants
- `.trn` `[Size]` `Width`/`Depth` == HG2 header `zonesX*1280` / `zonesZ*1280`
- HG2 / MAT / LGT byte counts match the size table in `docs/01`
- BZN `size` == object count; `seq_count` == `max(seqno)+1`
- `obj_addr` contiguous from `00000001`
- exactly one `player` object, `team = 1`
- trailing `[AiMission]/[AOIs]/[AiPaths]` present with sizes `0`

> **`TerrainName` MUST equal the base map name. [CORRECTED 2026-08-11]**
>
> This section previously said the opposite — that `msn_filename` and `TerrainName` are
> vestigial residue, that "93 of 128 stock corpus files disagree with their own name", and
> that validating them was "the single most likely way to waste a day chasing a
> non-bug". **That claim is backwards, and following it shipped 10 maps that cannot
> load.** The generator left the BZN template's placeholder in place, and every map died
> at load with `Could not load terrain stock.trn`. The engine resolves terrain through
> `TerrainName`.
>
> Re-measured against the pinned corpus snapshot (AGENTS.md rule 1 — reality wins):
>
> | Field | Reality |
> |---|---|
> | `TerrainName` == base map name | **125 of 128** |
> | `msn_filename` == `<base>.bzn` | 122 of 128 |
>
> The only `TerrainName` exceptions are `ulltst26`'s three variants, which name a
> nonexistent `SBPUI`. That single outlier is what the original claim generalised from.
>
> Variants share the base map's terrain: `xx01open_SW.bzn` carries
> `TerrainName = xx01open`, not `xx01open_SW`.
>
> **Tier 1 must assert:** every `.bzn`'s `TerrainName` names a terrain whose `.trn`,
> `.hg2`, `.mat` and `.lgt` all ship in the same pack. `msn_filename` is genuinely
> loose and need not be enforced, but is written as `<base>.bzn` to match the corpus.

### Cross-file consistency
- For **our generated maps only**: each variant's terrain files exist under the
  basename implied by the BZN's filename (not by `TerrainName`)
- `.des` stated GEYSERS / SCRAP counts == actual `_S` object counts *(corpus maps do
  this correctly — `uexmap10` says 16/280 and has 16/280)*
- `.ini` `maxPlayers` consistent with deathmatch spawn count
- Every object `PrjID` exists as an ODF in the pack or the base game
- Every asset the `.trn` references (atlas, sky, palette, cloud textures) exists

### Ground snapping
- Every object's Y is within **1.5 m** of the bilinear-interpolated terrain height at
  its X/Z. Threshold from measured corpus error (max 1.04 m).

---

## Tier 2 — Design

Implements the rules in `docs/04`. Errors block; warnings need review.

| Check | Rule | Severity |
|---|---|---|
| Full ground connectivity of all bases and economy | C1 | **error** |
| No enclosed traps > 200 m² | C2 | **error** |
| ≥2 topologically distinct base-to-base routes | C3 | **error** |
| No main-route corridor < 30 m wide | C4 | warning |
| ≥18% of map under 5° slope | T1 | **error** |
| Modal raw height in 500–1500 | T2 | warning |
| p99 raw height < 3900 | T3 | **error** |
| Playable basin ringed by impassable terrain | T4 | **error** |
| Base buildable pocket ≥ 4,000 m² | B1 | **error** |
| Base separation 35–60% of diagonal | B2 | warning |
| Spawn cluster geometry | B3 | **error** |
| No base-to-base line of sight at spawn | B4 | warning |
| Geysers on buildable ground (5°, 20 m radius) | E3 | **error** |
| Per-base economy within 5% | E4 | **error** |
| 30–50% of geysers contested | E5 | warning |
| Density within corpus range | E1/E2 | warning |

### The calibration test — do this first

> **Run the Tier 2 validators against all 35 stock corpus maps before using them on
> anything generated.**

**[PREMISE CORRECTED 2026-08-11 — first full corpus run.]** The original claim
below ("every stock map must pass all error checks") proved false: hand-made
stock maps *routinely* violate our generation-policy rules while being beloved —
Channels is 15.9% flat because canyon IS the map (T1), many maps do not ring
their edges (T4), spawn-cluster centroids sit on rough ground (B1), and every
map carries disconnected pockets (C2, since recalibrated to a warning at the
corpus p99). The corrected calibration gate (`tests/test_rules.py`) asserts what
actually is invariant: **no validator crashes, no error class outside the
known-tolerated set {T1, T4, B1}, and C1 only on the two whitelisted water/pit
maps (`ubltstg2`, `uexmap15` — see docs/09)**. T1/T4/B1 remain hard errors for
*generated* maps: they are policy we impose on ourselves, not corpus law.
`T1`'s floor is corrected to 17.5% (uexmap10 measures 17.7%, and the original
18% claimed to derive from it).

Original text, for the record: every stock map must pass all **error**-severity
checks. If `uexmap10` fails your
connectivity check, your connectivity check is wrong. Warnings may legitimately fire on
stock maps (they are hand-made and idiosyncratic) — record which, and use that as the
expected-warning baseline.

This is the single highest-value test in the project. It is the only thing standing
between you and a validator suite that is confidently, invisibly miscalibrated.

---

## Tier 3 — In-game

The game has **no command-line switch to load a map**. Menu automation is brittle. Use
the Lua harness instead.

### The harness

The standard map boilerplate loads **`bzfile.dll`** — *"enables game directory file
reading/writing"* from Lua — and **`exu.dll`** for extra engine queries. That gives a
write path out of the running game.

Ship a `<mapname>MAP.lua` alongside test builds (the per-map hook slot the script
layer already supports) that on mission start:

1. dumps engine-reported terrain dimensions and object counts
2. walks every `eggeizr1` / `npscr*` / `pspwn_1` and records engine position vs. the
   position we wrote — **catches ground-snap and coordinate-convention errors**
3. writes a JSON/CSV result file into the game directory
4. optionally drives a test unit between base pairs to sanity-check pathing

The agent then reads that file back and asserts on it. **Remove the harness `MAP.lua`
before packaging for release.**

### Log checking

Regardless of harness, after every test launch scan:

- `BZLogger.txt` — game/script errors *(this is 2.9 MB on this install; read the tail)*
- `BZOgreLogfile.log` — renderer, missing materials/meshes
- `crc32mission.log` / `crc32host.log` — mission file integrity

**Any new error or warning naming our map is a failure**, even if the map appears to
load. Capture a clean baseline of both logs from a stock corpus map first so you can diff.

### Manual playtest gate

Tiers 1–2 cannot judge pacing, readability, or visual character (`docs/04` §6). Every
map that ships must be played once by a human. Budget for this — it is 10 maps × a few
minutes each, and it is the only check on the things that actually make a map fun.

---

## Reporting

One directory per candidate:

```
build/candidates/<seed>/
├── report.json      all checks, pass/fail, measured values
├── preview.png      top-down shaded terrain + object overlay
├── connectivity.png reachable regions, routes, chokepoints
├── economy.png      per-base assignment and contested nodes
└── map/             the actual generated files
```

`report.json` must record **measured values, not just verdicts** — `"flat_pct": 22.4`
not `"T1": "pass"`. When a rule needs retuning later, the measurements are what let you
retune it against history instead of guessing.
