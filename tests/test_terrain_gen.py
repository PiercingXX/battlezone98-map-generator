"""Tests for terrain synthesis (docs/05 ``generate/terrain_gen.py``).

Verifies the plateau → carve → erode → flatten-pads pipeline produces a
:class:`HeightMap` that satisfies the terrain rules that are checkable without
the game pack:

- **T2** — the play surface sits on a plateau at a nonzero raw height, modal
  raw 500–1500 (never built up from 0).
- **T3** — never saturate: 99th percentile stays below raw 3900.
- **T1** — at least 18% of the map is under 5° slope, connected and
  distributed (not one corner blob).
- **B1 / E3** — base sites and geyser pads are flattened to buildable ground.
- Determinism — the same layout always yields the same heightmap.
"""

import numpy as np
import pytest

from bzmap.formats.hg2 import ZONE_SIZE, HeightMap, slope
from bzmap.generate.terrain_gen import (
    TerrainGenerator,
    generate_terrain,
)
from bzmap.model.layout import BASE, GEYSER, LayoutGraph

#: 5° slope in metres-per-metre (tan 5°).
SLOPE_5_DEG = np.tan(np.radians(5.0))


def _graph() -> LayoutGraph:
    """A 2560 m two-base ring with economy, mirroring test_layout's valid graph."""
    g = LayoutGraph(2560, 2560, n_teams=2)
    g.add_node("A", 640, 1280, BASE, team=0)
    g.add_node("B", 1920, 1280, BASE, team=1)
    g.add_node("T", 1280, 640, "waypoint")
    g.add_node("U", 1280, 1920, "waypoint")
    g.add_route("A", "T")
    g.add_route("T", "B")
    g.add_route("A", "U")
    g.add_route("U", "B")
    for nid, x, z in (("g1", 700, 1100), ("g2", 600, 1400),
                      ("g3", 1900, 1100), ("g4", 2000, 1400)):
        g.add_node(nid, x, z, GEYSER)
    return g


# -- output shape and elevation ----------------------------------------------


def test_returns_heightmap_with_whole_zone_grid():
    hm = generate_terrain(_graph())
    assert isinstance(hm, HeightMap)
    assert hm.zonesX == 2 and hm.zonesZ == 2  # 2560 m / 1280 m per zone
    assert hm.data.shape == (2 * ZONE_SIZE, 2 * ZONE_SIZE)


def test_base_elevation_is_nonzero():
    hm = generate_terrain(_graph())
    # Raw 0 means undefined; a nonzero plateau means we never build up from 0.
    assert hm.data.min() > 0


def test_modal_height_in_t2_range():
    hm = generate_terrain(_graph())
    counts = np.bincount(hm.data.ravel())
    modal = int(np.argmax(counts))
    assert 500 <= modal <= 1500, f"modal raw {modal} outside T2 range"


def test_p99_below_saturation():
    hm = generate_terrain(_graph())
    p99 = float(np.percentile(hm.data, 99))
    assert p99 < 3900, f"p99 {p99} exceeds T3 saturation warning line"


# -- T1 flat ground ----------------------------------------------------------


def test_at_least_18_percent_under_5_deg():
    hm = generate_terrain(_graph())
    flat = slope(hm) <= SLOPE_5_DEG
    frac = float(flat.mean())
    assert frac >= 0.18, f"only {frac:.1%} of map under 5° slope"


def test_flat_ground_is_distributed():
    """Flat cells appear in every quadrant, not one corner blob."""
    hm = generate_terrain(_graph())
    flat = slope(hm) <= SLOPE_5_DEG
    gz, gx = flat.shape
    mid_z, mid_x = gz // 2, gx // 2
    quads = [
        flat[:mid_z, :mid_x],
        flat[:mid_z, mid_x:],
        flat[mid_z:, :mid_x],
        flat[mid_z:, mid_x:],
    ]
    for i, q in enumerate(quads):
        assert q.any(), f"flat ground absent from quadrant {i}"


# -- flatten pads (B1 / E3) --------------------------------------------------


def test_base_site_is_flat_and_buildable():
    hm = generate_terrain(_graph())
    g = _graph()
    base = g.nodes["A"]
    s = slope(hm)
    # The pad radius is 60 m; sample a small disc well inside it and off the
    # carved corridor, so the pad interior must be flat.
    for dz in (-30, 0, 30):
        for dx in (-30, 0, 30):
            cz = round(base.z / 5.0) + dz // 5
            cx = round(base.x / 5.0) + dx // 5
            assert s[cz, cx] <= SLOPE_5_DEG, f"base pad not flat at ({dx},{dz}) m"


def test_geyser_pad_is_flat():
    hm = generate_terrain(_graph())
    g = _graph()
    geyser = g.nodes["g1"]
    s = slope(hm)
    cz = round(geyser.z / 5.0)
    cx = round(geyser.x / 5.0)
    assert s[cz, cx] <= SLOPE_5_DEG, "geyser pad not flat"


# -- determinism -------------------------------------------------------------


def test_same_layout_is_deterministic():
    a = generate_terrain(_graph(), seed=42)
    b = generate_terrain(_graph(), seed=7)
    assert np.array_equal(a.data, b.data)


def test_seed_does_not_change_output():
    # The synthesis is layout-determined; seed is accepted for symmetry only.
    a = generate_terrain(_graph(), seed=1)
    b = generate_terrain(_graph(), seed=999)
    assert np.array_equal(a.data, b.data)


# -- generator class ---------------------------------------------------------


def test_generator_class_matches_function():
    g = _graph()
    hm = TerrainGenerator().generate(g)
    assert np.array_equal(hm.data, generate_terrain(g).data)


def test_plateau_raw_is_tunable():
    g = _graph()
    hm = TerrainGenerator(plateau_raw=800).generate(g)
    counts = np.bincount(hm.data.ravel())
    assert int(np.argmax(counts)) == pytest.approx(800, abs=1)