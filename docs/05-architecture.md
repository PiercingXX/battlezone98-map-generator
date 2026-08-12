# 05 — Architecture

## Principles

- **Formats layer knows nothing about design; design layer knows nothing about bytes.**
  Every format module round-trips losslessly and does no interpretation.
- **Everything is inspectable.** Every stage can dump a PNG or a JSON summary. Debugging
  a map you cannot see is miserable.
- **Determinism.** A `(seed, config)` pair reproduces a map exactly. Non-reproducible
  generation makes bug reports worthless.

## Layout

```
bzmap/
├── formats/              # pure I/O — no design logic
│   ├── hg2.py            # HeightMap: read/write, zone-major, bilinear sample
│   ├── mat.py            # MaterialGrid
│   ├── lgt.py            # LightMap  (see docs/09 — may be copy-only)
│   ├── trn.py            # TerrainConfig (INI, ordered, comment-preserving)
│   ├── bzn.py            # BZN parse/emit  <-- THE CORE. see docs/02
│   ├── des.py  ini.py  odf.py  vxt.py
│   └── templates.py      # loads verbatim blocks from reference/ and stock worlds
│
├── model/                # the in-memory map, format-agnostic
│   ├── mapdef.py         # MapDefinition: terrain + variants + metadata
│   ├── objects.py        # GameObject, ObjectClass registry
│   └── layout.py         # LayoutGraph: base sites, economy nodes, routes
│
├── generate/
│   ├── layout_gen.py     # layout graph first (docs/04 §7)
│   ├── terrain_gen.py    # plateau -> carve -> erode -> flatten pads
│   ├── economy.py        # geyser + scrap placement (rules E1-E5)
│   ├── spawns.py         # spawn clusters (rules B1-B3)
│   └── variants.py       # base / _S / _ST / _SW object sets from one layout
│
├── validate/
│   ├── formats.py        # structural: round-trip, invariants, cross-file consistency
│   ├── terrain.py        # rules T1-T4
│   ├── connectivity.py   # rules C1-C4  <-- flood fill + A* over the 5m grid
│   ├── balance.py        # rules E4-E5, B1-B2
│   └── report.py         # one JSON + one PNG per map
│
├── render/
│   ├── preview.py        # top-down shaded heightmap + object overlay
│   └── thumbnail.py      # workshop .png and .BMP
│
├── package/
│   ├── assemble.py       # build/ -> pack layout (docs/07)
│   └── install.py        # copy into a test mod dir — NEVER touches Workshop content
│
└── cli.py                # bzmap generate|validate|render|package|roundtrip
```

## Data flow

```
config + seed
     │
     ▼
layout_gen ──> LayoutGraph ──────────┐   (validate graph BEFORE building terrain)
     │                               │
     ▼                               ▼
terrain_gen ──> HeightMap ──> validate/terrain + connectivity
     │                               │
     ├──> MaterialGrid (auto-paint)  │  fail -> discard candidate, next seed
     ├──> LightMap                   │
     ▼                               ▼
economy + spawns ──> objects ──> validate/balance
     │
     ▼
variants ──> {base, _S, _ST, _SW} BZN
     │
     ▼
metadata (.trn .ini .des .odf .vxt .lua) + render
     │
     ▼
validate/formats  (round-trip + cross-file invariants)
     │
     ▼
package ──> build/Expansion-Pack/
```

The important structural choice: **validate the layout graph before generating terrain.**
Terrain synthesis is the expensive step; rejecting a bad layout costs milliseconds,
rejecting it after erosion costs seconds. With a 3:1 expected cull ratio that matters.

## Key interfaces

```python
class HeightMap:
    width_m: int; depth_m: int          # multiples of 1280
    grid: np.ndarray                    # (depth_m//5, width_m//5) uint16, raw 0-4095

    @classmethod
    def read(cls, path) -> "HeightMap"
    def write(self, path) -> None       # zone-major; preserves header unknownA
    def sample_m(self, x: float, z: float) -> float   # bilinear, metres
    def slope_deg(self) -> np.ndarray
    def buildable_mask(self, max_slope=5.0) -> np.ndarray

class BznFile:
    header: BznHeader
    objects: list[GameObject]

    @classmethod
    def parse(cls, path) -> "BznFile"
    def emit(self) -> bytes             # MUST byte-match on round-trip
    def add(self, cls_name, x, z, yaw=0.0, team=0, role=None) -> GameObject
                                        # snaps y from the heightmap, assigns
                                        # obj_addr/seqno/label per docs/02 §5
```

`BznFile.emit()` recomputes `size`, `seq_count`, and `obj_addr` on write, so callers
cannot desynchronise them.

## Reuse rather than rebuild

**WorldBuilder** (`GrizzlyOne95/Battlezone98Redux_WorldBuilder`, MIT, Python) already
implements HG2 zone packing, MAT auto-painting, TRN parsing, atlas generation and skybox
tooling. Vendor it under `third_party/` or import it; do not reimplement.

Its HG2 zone logic was independently confirmed against our own decode — it is correct.
Its gap is that it has **no BZN writer**, which is exactly what `formats/bzn.py` is for.

## Testing

- `tests/test_roundtrip.py` — all 128 corpus BZNs parse and re-emit byte-identically.
  **This is the gate for everything else.**
- `tests/test_hg2.py` — round-trip all 36 terrains; verify `sample_m` against known
  object positions (should agree within ~1 m, per `docs/01`).
- `tests/test_rules.py` — the validators must **pass every stock corpus map**. If a
  validator rejects `uexmap10`, the validator is wrong, not the map. This is the single
  best defence against over-tuned rules.
- `tests/test_generate.py` — fixed seed produces byte-identical output twice.
