# 02 — BZN mission file specification

**This is the core new work.** No public BZN *writer* exists. WorldBuilder parses BZN
(both ASCII and binary) but cannot emit it.

Mission files in the reference corpus of community Workshop maps declare
`binarySave = false` and are **plain ASCII**. A binary variant
exists in the wild (older/stock content); we only need to write ASCII.

Reference material in this repo:
- `reference/bzn-object-template.txt` — one complete verbatim object block
- `reference/bzn-header-tail-template.txt` — file header and trailing sections

---

## 1. The critical syntax rule

There are **two** key/value forms and they differ in where the value lives:

```
key [1] =
VALUE_ON_NEXT_LINE

key = VALUE_ON_SAME_LINE
```

Getting this wrong is the most likely way to produce a file the engine silently
mis-parses. Empty values still occupy their line:

```
param [1] =
                    <- this blank line IS the value
name =              <- empty value, same line
```

Line endings are **CRLF**. Nested fields are indented with **one or two leading spaces**
(`  x [1] =` inside `pos`, ` mass [1] =` inside `euler`). Indentation appears to be
cosmetic but **reproduce it exactly** — do not normalise it.

Floats are written in C `%g`-style: `1294.88`, `-2.13606e-037`, `1e+030`. Note the
three-digit exponents. Preserve this formatting when round-tripping.

---

## 2. File structure

```
<header fields>
[GameObject]
  <34 or 38 fields>
[GameObject]
  ...
[AiMission]
[AOIs]
size [1] =
0
[AiPaths]
count [1] =
0
```

The `[AiMission]` / `[AOIs]` / `[AiPaths]` block appears **once, after the last
GameObject**. Every corpus multiplayer map has empty AOIs and AiPaths (`0` / `0`).
`[AiMission]` has no body.

### Header

```
version [1] =
2016
binarySave [1] =
false
msn_filename = uexmap10.bzn
seq_count [1] =
330
missionSave [1] =
true
TerrainName = uexmap10
size [1] =
299
```

| Field | Meaning |
|---|---|
| `version` | `2016` on all corpus maps. |
| `binarySave` | `false`. |
| `msn_filename` | Base name **without** variant suffix — `uexmap10_S.bzn` declares `uexmap10.bzn`. **Vestigial, see below.** |
| `seq_count` | `max(seqno) + 1`. Not the object count. |
| `missionSave` | `true`. |
| `TerrainName` | Terrain basename. **Vestigial, see below.** |
| `size` | **Number of `[GameObject]` blocks.** |

### ⚠️ `msn_filename` and `TerrainName` are vestigial — do not validate them

Measured across all 128 corpus BZN files:

- **0 of 90** variant files put the suffix in `msn_filename`. `uexmap10_S.bzn` says
  `uexmap10.bzn`.
- **93 of 128** have an `msn_filename` that does not match their own filename.
- The corpus contains outright junk: `uarracda_S.bzn` declares `uarracda.trn` (wrong
  extension); `ubltstg2*.bzn` declares `ubltstG2.BZN` (wrong case); **`ulltst26_*.bzn`
  declares `TerrainName = SBPUI`, and `SBPUI.trn` does not exist anywhere.**

`ulltst26` is a shipping corpus map and it works. Therefore the engine **resolves terrain
from the BZN's own filename and ignores both fields.** They are editor residue.

Consequences:
1. **The emitter must round-trip these fields verbatim.** Any writer that "corrects"
   them on write fails the round-trip test on 93 of 128 files and will send you hunting
   a bug that does not exist.
2. **The validator must not enforce filename agreement.** See `docs/06`.
3. For newly generated maps, set `msn_filename = <basename>.bzn` (no suffix) and
   `TerrainName = <basename>` — match the corpus's *intent*, and rely on the filename
   for actual resolution.

Note `size` (299) and `seq_count` (330) differ: stock files carry sparse editor-assigned
sequence numbers. For generated files, assigning `seqno = 1..N` contiguously and
`seq_count = N + 1` is consistent and safe.

---

## 3. Object schema

Every object has the **same 34 fields in the same order**. The `player` object has
**38** — four extra fields inserted after `transform`. Verified across all object classes
in the corpus.

### The 34-field standard order

```
PrjID          seqno          pos            team           label
isUser         obj_addr       transform      illumination   pos            (second pos!)
euler          seqNo          name           isCritical     isObjective
isSelected     isVisible      seen           healthRatio    curHealth
maxHealth      ammoRatio      curAmmo        maxAmmo        priority
what           who            where          param          aiProcess
isCargo        independence   curPilot       perceivedTeam
```

**Gotchas in that list:**
- `pos` appears **twice** — once before `team`, once after `illumination`. Both carry the
  same x/y/z in every stock object. Not a parsing error; reproduce both.
- `seqno` (lowercase o) and `seqNo` (capital N) are **different fields** holding the
  **same value** in every stock object.
- `euler` is a container whose body is the rigid-body state (`mass`, `v`, `omega`,
  `Accel`, …) — its own value is empty.

### Player-only extra fields

Inserted between `transform` and `illumination`:

```
abandoned  cloakState  cloakTransBeginTime  cloakTransEndTime
```

### Composite field bodies

`pos` (2-space indent):
```
pos [1] =
  x [1] =
625.345
  y [1] =
55.6
  z [1] =
782.817
```

`transform` (2-space indent): a 3×3 basis plus translation, in order
`right_x right_y right_z up_x up_y up_z front_x front_y front_z posit_x posit_y posit_z`.

`euler` (1-space indent): `mass mass_inv v_mag v_mag_inv I k_i` then vectors
`v`, `omega`, `Accel` (each with 2-space-indented `x`/`y`/`z`).

For a **static prop** (geyser, scrap, spawn point) the whole rigid-body block is inert:
```
 mass [1] =            0
 mass_inv [1] =        1e+030
 v_mag [1] =           0
 v_mag_inv [1] =       1e+030
 I [1] =               1
 k_i [1] =             0
 v / omega / Accel     all zero
```
(shown here collapsed — see `reference/bzn-object-template.txt` for real layout)

---

## 4. Transform: encoding rotation

Stock transforms are pure yaw rotations about Y:

```
right = ( cos θ, 0, -sin θ)
up    = ( 0,     1,  0    )
front = ( sin θ, 0,  cos θ)
posit = ( x, y, z )                # duplicates the `pos` field
```

Verified on all 14 spawn points of `uexmap10_SW`: e.g. `right=(0.539,·,-0.843)`,
`front=(0.843,·,0.539)` → θ = 57.4°.

Some props carry a slight tilt in `up` to match the terrain normal (a geyser at
`up=(0.019992, 0.9996, -0.019992)`). This is cosmetic; emitting a clean `up=(0,1,0)`
is acceptable. **INFERRED** — confirm visually in-game during Phase 3.

---

## 5. Identity fields — the conventions

| Field | Rule |
|---|---|
| `obj_addr` | 8-digit **hex**, contiguous `00000001..N` in file order. Verified contiguous on all three variants of `uexmap10`. |
| `seqno` / `seqNo` | Unique per object, same value in both fields. Contiguous `1..N` is fine. |
| `label` | `<PrjID><index>_<role>` — e.g. `eggeizr10_geyser`, `npscr32_scrap`, `pspwn_10_spawnpnt`, `abhang13_repairdepot`, `absupp13_supplydepot`, `player0_wingman`. The `<index>` is per-class and **not** required to be dense (stock files skip numbers). |
| `name` | Empty on all multiplayer map objects. |
| `team` | `0` = neutral/world. `1` = team one. `8` = team two (wingman/team modes). |

Observed `role` suffixes: `geyser`, `scrap`, `spawnpnt`, `wingman`, `repairdepot`,
`supplydepot`.

### Per-class visibility flags (copy these exactly)

| Class | `isVisible` | `seen` | `illumination` | `team` |
|---|---|---|---|---|
| `player` | 2 | 2 | 1 | 1 |
| `eggeizr1` (geyser) | 0 | 0 | 0 | 0 |
| `npscr1/2/3` (scrap) | 1 | 1 | 0 | 0 |
| `pspwn_1` (spawn point) | 1 | 1 | 0 | 0 |
| `abhang` / `absupp` | 0 | 0 | 0 | 1 or 8 |

---

## 6. Writer requirements

### R1 — Round-trip fidelity is the acceptance gate

```
parse(f) -> emit() must be byte-identical to f, for all 128 BZN files in the corpus.
```

Build the parser and emitter as a matched pair and make this test the first thing that
passes. It catches: line-ending errors, the two key/value forms, indentation, float
formatting, field ordering, and the duplicate-`pos` trap — all at once.

Expect a small number of genuine corpus oddities. If a file cannot round-trip, quarantine
it with a written explanation rather than loosening the test for everything.

### R2 — Template-and-mutate, not synthesis

Build objects by cloning a known-good block and substituting values. Do **not**
assemble field lists from this document — this document is a description of the corpus,
and the corpus is the authority.

```python
obj = template("eggeizr1")          # verbatim block from reference/
obj.set_position(x, y, z)           # updates pos, second pos, and transform.posit_*
obj.set_yaw(theta)                  # updates transform basis
obj.set_identity(seqno=4, addr=2, label="eggeizr10_geyser")
```

`set_position` must update **all three** places a position appears. A writer that
updates `pos` but not `transform.posit_*` will produce objects that render in one place
and collide in another — a bug that is very hard to see and very easy to ship.

### R3 — Ground snapping

Object Y comes from the heightmap: `y = sample(x, z) * 0.1`. Sample with bilinear
interpolation, not nearest-neighbour — stock objects sit within ~1 m of the interpolated
surface, and nearest-neighbour on a 5 m grid will float or sink objects on slopes.

### R4 — Invariants the emitter must enforce

- `size` == number of GameObject blocks
- `seq_count` == `max(seqno) + 1`
- `obj_addr` contiguous from `00000001`
- `msn_filename` / `TerrainName`: **preserved verbatim when round-tripping**; set to
  `<basename>.bzn` / `<basename>` for newly generated maps. Never rewritten on load.
- exactly one `player` object, `team = 1`
- trailing `[AiMission]/[AOIs]/[AiPaths]` block present, sizes `0`

---

## 7. What we are *not* implementing

- **Binary BZN writing.** The corpus is all-ASCII. WorldBuilder has a binary *reader*
  (`BinaryBZNParser`) if you ever need to read stock 1998-era content.
- **AiPaths / AOIs authoring.** Every corpus multiplayer map has these empty. If a future
  map needs AI paths, that is a separate spec.
- **`[AiMission]` bodies.** Empty throughout the corpus.
