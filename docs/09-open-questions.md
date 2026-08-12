# 09 — Open questions and risks

Things that are genuinely unknown. Each has an experiment that resolves it. **Do not
guess and proceed** — record findings here as they land.

---

## E1 — `.LGT` lightmap format ✅ **RESOLVED 2026-08-11**

**Status: resolved — see docs/01 §3 for the full format.** The experiment played
out close to the predicted path 4, with a twist on path 2: an all-**zero** `.LGT`
*loads fine* and renders 3D terrain normally, but the **in-game map radar
underlay renders black** — that is what the file is for. Reversing the format
against the pinned snapshot: the unexplained extra plane is a **constant ambient
plane** (value 56, and it is plane 0, not the tail); the remaining planes are
per-zone shading, row-major zones matching HG2, best correlated with a north
light over the map's own heightmap. The packer bakes it. The original text
follows for the record:

**Original (superseded):** unresolved. **Blocks:** Phase 3.

Known: size is `(zonesX * zonesZ + 1) * 65536` bytes, verified across all five map
dimensions. Contents are real baked lighting — ~200 distinct byte values, map-specific
distributions. The base term is one byte per heightmap cell; the extra 65536-byte plane
is unexplained.

Neither `MakeTRN.exe` nor WorldBuilder generates `.LGT`. 35 of 36 terrains in the
reference corpus of community Workshop maps ship one (the exception, `bane`, is a
broken stub missing `Width`/`Depth` too).

**Experiment, in order — stop at the first that works:**
1. Ship a map with **no** `.LGT`. Does it load? Does the game generate one?
2. Ship a **flat-filled** `.LGT` (e.g. all `0x80`) of the correct size. Loads? Looks flat
   but acceptable?
3. Copy a stock `.LGT` from a same-dimensioned map. Loads? Lighting obviously wrong?
4. Only if 1–3 all fail: reverse the format. Start by correlating byte values against
   terrain normals and a sun direction from the `.trn` `[NormalView]` block, and work
   out what the extra plane holds.

Outcome 1 or 2 makes this a non-issue. Do this **early in Phase 3** — it is the last
unknown that can prevent a map from loading at all.

---

## E2 — HG2 header `unknownA`

**Status:** unresolved. **Blocks:** nothing (workaround available).

Header offset `0x08`, uint16. Observed: `10`, `11`, `12`, `24` — no correlation found
with map dimensions (both `bltop04` 5120×5120 and `ulllowar` 3840×3840 differ from
same-sized peers).

**Workaround:** copy the value from a stock map of the same dimensions.

**Experiment:** vary it in a test map and observe. Candidates: a terrain LOD level, a
water/sea-level index, or a legacy field the engine ignores. Low priority — the
workaround is fine.

---

## E3 — `.MAT` bit layout

**Status:** inferred, not verified. **Blocks:** nothing.

Hypothesis (`docs/01` §2): `[matA:4][matB:4][variant:4][0:4]`.

**Workaround:** generate `.MAT` with `MakeTRN.exe` (`ext = TRN` mode) or WorldBuilder's
Auto-Painter rather than authoring it. Only verify the bit layout if auto-painting
produces visibly wrong texture transitions.

---

## E4 — Minimum corridor width for vehicle pathing

**Status:** inferred (30 m, `docs/04` rule C4). **Blocks:** nothing; affects quality.

Derived from vehicle scale, not measured. Too tight and units jam at chokepoints; too
loose and maps lose definition.

**Experiment:** in the Phase 3 test map, build a series of corridors at 15/20/25/30/40 m
and drive a tank and a walker through each. Record the real threshold and update rule C4.

---

## E5 — Transform `up` vector and terrain normals

**Status:** inferred. **Blocks:** nothing; cosmetic.

Stock props sometimes carry a slight tilt in `up` matching the terrain normal (a geyser
at `up = (0.019992, 0.9996, -0.019992)`). We plan to emit clean `up = (0,1,0)`.

**Experiment:** place identical objects on a slope with both conventions in the Phase 3
map and compare visually. If flat-up looks wrong on slopes, compute the normal from the
heightmap.

---

## E6 — Does the engine tolerate contiguous `seqno`?

**Status:** inferred. **Blocks:** nothing.

Stock files carry sparse editor-assigned sequence numbers (`uexmap10_S`: 299 objects,
seqno range 1–329). We plan dense `1..N`.

Nothing in the corpus maps' Lua appears to depend on specific values, and `seq_count` is
consistently `max+1`. Confirm in Phase 3 — cheap to check, and if wrong it would be
confusing to debug later.

---

## Standing risks

### R2 — Terrain name collisions
Terrain names are global across all loaded mods. A collision with another subscribed
pack breaks both. Mitigation: distinctive prefix + a Tier 1 collision check against
installed Workshop names and the base game's.

### R3 — Generated maps are recognisably generated
The real reputational risk. Procedural terrain tends toward uniform noise with no
landmarks and no intent. Mitigations: layout-graph-first generation (`docs/04` §7),
the diversity requirement, and a human curation gate. **Accept a low yield.** Shipping
ten mediocre maps is worse than shipping ten generated maps that are actually good.

### R4 — Validators that pass everything
A suite that never fails feels like success and provides nothing. Phase 4's broken-fixture
tests exist specifically to catch this. Take them seriously.

### R5 — Testing friction on Linux
Game runs under Proton; no `wine` on PATH; no CLI map loading; `UploaderApp.exe` is a
Windows GUI. In-game iteration will be slower than it would be on Windows. This is why
Tiers 1–2 carry as much weight as they do — minimise the number of times you need to
launch the game.

---

## Resolved

### ✅ `msn_filename` and `TerrainName` are vestigial (resolved 2026-08-10)

**Question:** do these header fields need to agree with the file's own name, and does
`TerrainName` control which terrain loads?

**Answer: no to both.** Measured across all 128 corpus BZN files:
- 0 of 90 variant files include the suffix in `msn_filename`
- 93 of 128 have an `msn_filename` disagreeing with their own filename
- `uarracda_S.bzn` declares `uarracda.trn`; `ubltstg2*` declares `ubltstG2.BZN`
- **`ulltst26_*.bzn` declares `TerrainName = SBPUI`; no `SBPUI.*` file exists anywhere
  in the corpus** — and `ulltst26` ships and works

The engine resolves terrain from the BZN's filename and ignores both fields.

**Consequence:** the emitter must round-trip them verbatim, and the validator must not
enforce agreement. Baked into `docs/02` §2 and `docs/06`. This was originally specified
*incorrectly* and caught by cross-checking the extracted reference template against the
spec — worth remembering as an argument for Rule 1 in `AGENTS.md`.

### ✅ Round-trip gate quarantine mechanism (resolved 2026-08-11)

**Question:** where do non-round-tripping stock files go, and how is the operator told?

**Answer:** `tests/test_roundtrip.py` round-trips every corpus `.bzn` (128) and `.HG2`
(36) byte-identically. It resolves the corpus from an environment variable or the default
Steam workshop path, and skips when the corpus is absent so the ordinary CI suite passes without
it. Any file that fails to round-trip is **quarantined**: a written explanation (filename +
reason) is recorded under `build/quarantine/{kind}-quarantine.txt` and the gate fails — a
non-empty quarantine is a hard error (Rule 4 / docs/06 §Tier 1). When the operator runs the
gate against the installed corpus and a file lands in quarantine, the reason it records is a
genuine format unknown to investigate here before proceeding.

### ✅ Tier 2 calibration + broken-fixture gate (resolved 2026-08-11)

**Question:** how do we stop the Tier 2 validators from being confidently, invisibly
miscalibrated (R4)?

**Answer:** `tests/test_rules.py` holds both halves:
- **Calibration** — every stock corpus map must pass every *error*-severity Tier 2 check (C1–C3,
  T1/T3/T4, B1). A stock map failing an error check means the validator is wrong, not the map.
  It resolves the corpus from an environment variable or the default Steam workshop path and skips
  when absent, so the ordinary CI suite passes without it — the operator runs it against the
  installed corpus. Bases are the centroids of each `pspwn_1` team cluster; economy comes from the
  `_S` variant. E4/E5/B2/B3 are **not** calibrated because they need a route graph and a
  generated spawn set that stock maps do not carry.
- **Broken fixtures** — assert each error validator actually catches its defect: a disconnected
  geyser (C1), an unbuildable base (B1), a trap pocket (C2) and a flat map with no impassable
  ring (T4). If any of these ever passes, that validator is broken and must be fixed, not the
  test deleted. These run in normal CI.
- **Anti-silent-skip guard** — the calibration also asserts it actually exercised at least half
  the pack (`calibrated >= EXPECTED_STOCK_MAPS // 2`), so a broken spawn/base discovery routine
  cannot make the gate pass by silently skipping every map.

### ⚠️ Terrain generator isolates base pads (found 2026-08-11, connectivity task)

**Status:** confirmed defect in `generate/terrain_gen.py`; **blocks** the connectivity
validator's "generated map passes C1" expectation and any playable output.

**Observation (verified by direct measurement, not hypothesis):** `generate_terrain`
carves route corridors down to raw 700 but flattens base pads back up to raw 1000
(`PLATEAU_RAW`) *after* erosion. The 300-raw (30 m) step between the pad and the corridor
floor survives as a near-vertical cliff — measured slope 3.0 m/m (~71°, far above the C1
30° traversable threshold) at the pad edge. Result: each base pad is its own disconnected
traversable component (component sizes 377 cells ≈ 9,425 m² for bases A/B vs. the main
plateau component of ~4,041,425 m²), so **no base is reachable from the economy by a ≤30°
ground path**. The new `validate/connectivity.py` C1 rule correctly flags every geyser as
unreachable on a generated map.

**Fix direction (terrain task, not the validator):** leave a gentle ramp from each base pad
down to the corridor floor (e.g. carve the corridor *through* the pad region before
re-flattening, or taper the pad edge over >30 m so the slope stays under 30°), instead of
re-flattening the pad to a hard 300-raw step. Until fixed, the connectivity validator
correctly rejects generated terrain, so the "generated map passes C1" test must use a
hand-built connected fixture.

---

## E6 — C1 findings on stock maps are mostly a layout-construction artifact

**Status:** open (2026-08-11, updated same day). The full capture showed C1
firing on ~10 stock maps, and on several the unreachable set includes `base0`
itself — the calibration derives each "base" as a spawn-cluster centroid, which
often lands on untraversable ground, poisoning every reachability verdict. So
stock-C1 is predominantly *our approximation*, not map breakage; C1 is in the
tolerated-class set for stock input. A better stock-base derivation (snap the
centroid to the nearest traversable cell) would let C1 re-enter the gate.
Original narrower observation: Most likely the model under-approximates hover traversal —
over water surfaces and down/into pits with momentum. They are whitelisted in
the calibration gate (`tests/test_rules.py::STOCK_C1_WHITELIST`) pending a
look at where exactly the flagged nodes sit. If the model is wrong, C1 needs a
hover-traversal term; if the nodes are genuinely decorative/unreachable scrap,
the corpus tolerates unreachable scrap and C1 should downgrade those to
warnings for scrap (never for geysers or bases).

## E7 — HG2 raw heights above 4095 on ulltst96

**Status:** open (2026-08-11). docs/01 assumes a 12-bit height ceiling (4095);
`ulltst96` (Hill Surge) measures p99 raw height **7630**. Either the field is
wider than 12 bits or that map exploits undefined range. Re-measure the HG2
format's true height depth before relying on the 4095 ceiling (T3) anywhere
outside our own generated maps. Also `uexmap15` sits exactly at 4095 (p99),
i.e. deliberately saturated.
