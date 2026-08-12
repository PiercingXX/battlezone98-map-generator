# 01 — File formats

All measurements taken 2026-08-10 from the installed game (v2.2.301, Steam) and a
reference corpus of community Workshop maps. Claims are **VERIFIED** unless marked **INFERRED**.

A map is a set of files sharing a basename ("terrain name"). Extensions are
case-inconsistent in the wild (`.HG2` and `.hg2`, `.MAT` and `.mat`, `.TRN` and `.trn`
all occur within the corpus). **Always match case-insensitively on read; emit lowercase.**

Complete file set, using `uexmap10` as reference:

```
uexmap10.trn     terrain + environment config   (INI text)
uexmap10.HG2     heightmap                      (binary)
uexmap10.MAT     material/texture grid          (binary)
uexmap10.lgt     baked lightmap                 (binary — see docs/09)
uexmap10.vxt     observer vehicle list          (text)
uexmap10.bzn     deathmatch objects             (ASCII)
uexmap10_S.bzn   strategy objects               (ASCII)
uexmap10_SW.bzn  wingman-teams objects          (ASCII)
uexmap10.ini     workshop + multiplayer metadata(INI text)
uexmap10.des     human-readable map description (text)
uexmap10.odf     per-map settings               (INI text)
uexmap10.lua     mission script                 (Lua — boilerplate)
uexmap10.png     thumbnail
uexmap10.BMP     minimap / loading image
```

---

## 1. `.HG2` — heightmap **[VERIFIED]**

The single most important format. Get this wrong and nothing else matters.

### Header — 12 bytes, little-endian

```
offset  type    field        observed
0x00    uint16  version      1
0x02    uint16  depth        8       -> zone_size = 2**depth = 256
0x04    uint16  zonesX       width_m  / 1280
0x06    uint16  zonesZ       depth_m  / 1280
0x08    uint16  unknownA     varies: 10, 11, 12, 24
0x0A    uint16  unknownB     0
```

`unknownA` varies per map with no pattern we could tie to size. Copy it from a stock
map of the same dimensions; do not invent a value. (Tracked in `docs/09`.)

### Data — `zonesX * zonesZ * 256 * 256` uint16 values

**The data is ZONE-MAJOR, not row-major.** This is the trap. The array is a sequence of
256×256 zone blocks in row-major *zone* order; within each zone, cells are row-major.

```python
def sample(a, zonesX, zone_size, x, z):
    zx, ix = divmod(x, zone_size)
    zz, iz = divmod(z, zone_size)
    return a[(zz * zonesX + zx) * zone_size * zone_size + iz * zone_size + ix]
```

Verified by rendering: naive row-major decoding produces visibly tiled garbage;
zone-major produces a coherent map. Independently confirmed against WorldBuilder's
`convert_hg2_to_png`, which uses identical zone logic.

### Scale — **`height_metres = raw * 0.1`, offset 0**

Grid spacing is **5 metres**. Grid dimensions are `width_m / 5` by `depth_m / 5`.

Solved by least-squares fitting object Y-positions against sampled terrain, over three
maps of different sizes (n≈250 ground-anchored objects each):

```
uexmap10 (512²):   y = 0.099994*raw + 0.003    max error 0.46 m
umoonwar (256²):   y = 0.099966*raw + 0.007    max error 0.63 m
bltop04  (1024²):  y = 0.099808*raw + 0.207    max error 1.04 m
```

Raw range is **0–4095** (12-bit), i.e. 0–409.5 m. `MakeTRN`'s `/e=EmptyElevation
(0-4095)` switch corroborates the 12-bit range.

### Value 0 means "undefined", not "sea level"

2–11% of cells in stock maps are exactly 0. These are undefined/out-of-play regions, not
low ground. Real playable terrain sits on a **plateau well above zero** — modal heights
are `uexmap10`: 988 (98.8 m), `uhecave`: 1371 (137.1 m), `umoonwar`: 153 (15.3 m). This
leaves headroom to carve downward as well as build upward.

Generated terrain must follow the same convention: put the play surface at a nonzero
base elevation, do not start at 0 and only go up.

### Size table (all verified)

| width×depth (m) | zonesX×zonesZ | grid | HG2 bytes | MAT bytes | LGT bytes |
|---|---|---|---|---|---|
| 1280×1280 | 1×1 | 256² | 131,084 | 8,192 | 131,072 |
| 2560×2560 | 2×2 | 512² | 524,300 | 32,768 | 327,680 |
| 3840×3840 | 3×3 | 768² | 1,179,660 | 73,728 | 655,360 |
| 5120×3840 | 4×3 | 1024×768 | 1,572,876 | 98,304 | 851,968 |
| 5120×5120 | 4×4 | 1024² | 2,097,164 | 131,072 | 1,114,112 |

Dimensions **must be multiples of 1280** (`MakeTRN` enforces this). Non-square is legal
(`uultst25` is 5120×3840).

---

## 2. `.MAT` — material grid **[MOSTLY INFERRED]**

`(width_m / 20) × (depth_m / 20)` uint16 values — one per 20 m tile, i.e. one material
tile per 4×4 heightmap cells. Byte counts verified against all five sizes above.

Encoding, inferred from value distributions on `uexmap10`:

```
bits 15-12  material A index   (0-4, indexes [TextureTypeN] in the .trn)
bits 11-8   material B index   (blend target)
bits  7-4   tile variant/rotation (observed 0-7)
bits  3-0   always 0
```

Evidence: high bytes cluster on `0x11, 0x33, 0x22, 0x12, 0x23, 0x00, 0x13, 0x01` —
consistent with two 4-bit material indices. Low bytes are always multiples of 16.
This matches the `.trn` layer naming (`SolidA0..A3`, `DiagonalTo1_A0..A3`,
`CapTo2_A0..A3`) where the `A0..A3` suffix is rotation.

**You probably do not need to author this by hand.** Both `MakeTRN.exe` (`ext = TRN`
mode, auto-assigns materials by slope and elevation) and WorldBuilder's Auto-Painter
generate `.MAT` from an existing `.HG2` plus rules. Prefer generating it. Only decode
this fully if auto-painting proves inadequate.

---

## 3. `.LGT` — baked lightmap **[RESOLVED 2026-08-11]**

Size formula (verified across all five dimensions):

```
bytes = (zonesX * zonesZ + 1) * 65536
```

**Plane structure, measured against the pinned corpus snapshot:**

- **Plane 0 is a constant ambient plane.** In every corpus map checked it is a
  single repeated byte, value `56` (`0x38` — the "map-specific modal value"
  previously noted was this plane). That explains the `+1`.
- **Planes 1..N are per-zone shading**, one byte per heightmap cell, 256×256
  per zone, zones in **row-major order matching the HG2 zone layout**.
- Values span 56..255; 56 is the corpus-wide floor (the ambient level).
- Shading correlates with a **north light** over the map's own heightmap
  (corr −0.33 against `dh/dz` under row-major assembly on `uexmap10`; every
  other assembly order and light direction scores materially worse). The
  remaining variance is cast shadows and sun elevation from the original offline
  bake, which a slope shade does not reproduce.

**What it is for, observed in game:** the engine builds the in-game map radar
underlay from the baked lightmap. An all-zero `.LGT` produces a **black radar
minimap** while the 3D terrain still renders normally (Redux lights the world
dynamically) and the lobby image still shows (that comes from the `.BMP`). This
is exactly how the defect presented in testing.

Neither `MakeTRN.exe` nor WorldBuilder generates `.LGT`; 35 of 36
corpus terrains ship one (`bane` is a broken stub).

---

## 4. `.trn` — terrain config **[VERIFIED]**

Plain INI, CRLF line endings. Full example: `uexmap10.trn`. Sections:

| Section | Purpose |
|---|---|
| `[Size]` | `MinX`, `MinZ`, `Width`, `Depth`, `Height`. **Must match the HG2 header.** |
| `[NormalView]` | Fog, visibility, ambient, shadow luma. Time-of-day feel. |
| `[Atlases]` | `MaterialName` — the terrain texture atlas (e.g. `el_detail_atlas`). |
| `[World]` | `MusicTrack`. |
| `[Sky]` | Sun texture, sky type/height/texture, backdrop. |
| `[Clouds]` | Count, type, tile size, per-layer texture/size/height. |
| `[Color]` | Palette/luma/translucency/alpha tables (`.act`, `.lum`, `.tbl`, `.alb`). |
| `[TextureType0..N]` | Per-material tile sets. `FlatColor` plus `Solid*`/`Diagonal*`/`Cap*` map references. |

**Do not author `[TextureType*]` blocks from scratch.** Copy a stock world template from
`Edit/trn/` (achilles, elysium, europa, ganymede, io, mars, moon, titan, venus) and
override only `[Size]`, `[NormalView]`, `[World]` and `[Sky]`. The texture-type blocks
are long, world-specific, and reference asset names that must exist.

---

## 5. `.ini` — workshop + multiplayer metadata **[VERIFIED]**

```ini
[DESCRIPTION]
missionName = "Silver Pools"

[WORKSHOP]
;mapType = "instant_action"
mapType = "multiplayer"
customtags = "strat, 1v1, sxxy, rexy"

[MULTIPLAYER]
minPlayers = "1"
maxPlayers = "14"
gameType = "K"
```

`gameType` is one of `{D, S, A, M, K}`. **Every one of the 36 corpus maps uses `K`.**
`maxPlayers` is 14 on 35 of 36 (one outlier at 15). Match the corpus.

A fuller annotated template, including campaign fields we do not need, ships as
`Edit/sample.ini`.

---

## 6. `.des` — description **[VERIFIED, format is loose]**

Free text shown in the map browser. There is no enforced schema — the corpus is
inconsistent. Common shape:

```
WORLD: Elysium	SIZE: Small
GEYSERS: 16	SCRAP: 280
PLAYERS: 2
Map by SxxyRexy
```

**The stated GEYSERS and SCRAP counts match the actual object counts in the `_S` BZN**
(`uexmap10`: 16 geysers, 280 scrap objects = 95 `npscr1` + 102 `npscr2` + 83 `npscr3`).
Generate this text from the real counts — do not template it and let it drift. The
validator checks this (`docs/06`).

---

## 7. `.odf` — per-map settings **[VERIFIED]**

Read at runtime via `OpenODF(GetMapTRNFilename())`. Small INI:

```ini
[SBPMapSettings]

// Control point locations
CP1Name = ancrCP06_ancrCP11
CP1X = 849
CP1Z = 2096
CP2Name = ancrCP02_ancrCP11
CP2X = 1885
CP2Z = 456
```

Control points are optional (used by `GAMEMODESub_ControlPoints.lua`). The game-mode
scripts also read a `[ScrapImpactZone]` section here (`SIZ_IncludeSpawnPoints`, default
true). Note the section name is `SBPMapSettings` — legacy naming.

---

## 8. `.vxt` — observer vehicle list **[VERIFIED]**

Tab-separated text, one entry per line, blank-line separated:

```
avobserv avobserv.des	x	NSDF

svobserv svobserv.des	x	CCA

bvobserv bvobserv.des	x	BDOG
```

Copy verbatim from a stock map. There is no reason to vary it.

---

## 9. `.bzn` — mission objects

The big one. Specified separately in **[`docs/02-bzn-spec.md`](02-bzn-spec.md)**.

---

## 10. Thumbnails

`.png` (workshop/browser thumbnail) and `.BMP` (loading/minimap image). Generate the
`.png` from a top-down shaded render of the heightmap with object overlays — this is
also useful as a debugging artifact. Match the pixel dimensions of stock corpus thumbnails
rather than picking your own.

---

## Shipped tools worth knowing about

`Edit/` in the game directory contains Windows CLI tools:

- **`MakeTRN.exe`** v2.1.2 — the useful one. Two relevant modes:
  - `MAKETRN <name> /c /w=nnnn /h=nnnn` — create blank `TRN`+`HG2`+`MAT` at given
    dimensions (must be multiples of 1280).
  - `MAKETRN <name>.trn [/p=params] [/e=empty]` — re-derive `.MAT` from `.HG2` by
    slope and elevation rules.
- `MakeMAP.exe`, `MakeObj.exe`, `MakeZFS.exe` — asset packing, not needed for maps.
- `Edit/trn/*.trn` and `Edit/ini/*.ini` — **stock world templates. Use these.**
- `Edit/sample.ini`, `Edit/sample.des` — annotated metadata templates.

These are Windows binaries and there is no `wine` on this machine. Prefer reimplementing
their output in Python; fall back to Proton only if needed.
