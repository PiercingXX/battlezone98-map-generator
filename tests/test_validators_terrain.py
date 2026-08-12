"""Tests for Tier 2 terrain validation — rules T1-T4 (docs/06, ``validate/terrain.py``).

Builds heightmaps directly (and with the terrain generator) and asserts that a
valid terrain passes with no problems, and that each T-rule catches its specific
violation:

- **T1** (error) — at least 18% of the map under 5° slope, connected and
  distributed, not one corner blob.
- **T2** (warning) — modal raw height in 500-1500.
- **T3** (error) — 99th percentile raw height below 3900.
- **T4** (error) — the map edge is ringed by impassable (>45°) terrain.
"""

import numpy as np

from bzmap.formats.hg2 import ZONE_SIZE, HeightMap
from bzmap.generate.terrain_gen import generate_terrain
from bzmap.model.layout import BASE, GEYSER, LayoutGraph
from bzmap.validate.terrain import (
    ERROR,
    T1_MIN_FLAT_FRACTION,
    T2_MODAL_MAX,
    T2_MODAL_MIN,
    T3_P99_MAX,
    WARNING,
    TerrainValidator,
    validate_terrain,
)


def _graph() -> LayoutGraph:
    """A 2560 m two-base ring with economy (mirrors test_terrain_gen)."""
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


def _flat_hm(raw=1000):
    """A perfectly flat heightmap at ``raw`` (fails only T4)."""
    return HeightMap(1, 1, np.full(
        (ZONE_SIZE, ZONE_SIZE), raw, dtype=np.uint16))


def _ramp_hm():
    """A steep linear ramp: 0.1 m/m slope everywhere, so almost no cell is flat."""
    zz, xx = np.mgrid[0:ZONE_SIZE, 0:ZONE_SIZE]
    data = ((zz + xx) * 5).astype(np.uint16)  # max 2560, no saturation clip
    return HeightMap(1, 1, data)


def _wall_hm():
    """Flat everywhere except a full-height wall splitting the map in two."""
    data = np.full((ZONE_SIZE, ZONE_SIZE), 1000, dtype=np.uint16)
    data[ZONE_SIZE // 2, :] = 4095
    return HeightMap(1, 1, data)


def _ringed_flat_hm(raw=1000):
    """A flat map with a steep (impassable) boundary ramp — a valid T4 ring.

    The interior is flat at ``raw``; the outer boundary band ramps up by 60 raw
    per cell (1.2 m/m slope, well above 45°), so the edge is impassable without
    saturating the 12-bit range (T3 stays satisfied).
    """
    data = np.full((ZONE_SIZE, ZONE_SIZE), raw, dtype=np.uint16)
    b = max(1, round(0.05 * ZONE_SIZE))
    for i in range(b):
        data[i, :] = raw + (b - i) * 60
        data[ZONE_SIZE - 1 - i, :] = raw + (b - i) * 60
    for i in range(b):
        data[:, i] = np.maximum(data[:, i], raw + (b - i) * 60)
        data[:, ZONE_SIZE - 1 - i] = np.maximum(
            data[:, ZONE_SIZE - 1 - i], raw + (b - i) * 60)
    return HeightMap(1, 1, data)


# -- valid terrain ------------------------------------------------------------


def test_generated_terrain_passes_all_t_rules():
    hm = generate_terrain(_graph())
    assert validate_terrain(hm) == []


def test_validator_class_matches_function():
    hm = generate_terrain(_graph())
    assert TerrainValidator(hm).validate() == validate_terrain(hm)


def test_accepts_hg2_path(tmp_path):
    hm = generate_terrain(_graph())
    p = tmp_path / "map.HG2"
    hm.write(p)
    assert validate_terrain(p) == []


# -- measured values ----------------------------------------------------------


def test_measure_reports_flat_pct():
    hm = generate_terrain(_graph())
    m = TerrainValidator(hm).measure()
    assert m["flat_pct"] >= T1_MIN_FLAT_FRACTION * 100.0
    assert m["flat_distributed"] is True
    assert T2_MODAL_MIN <= m["modal_raw"] <= T2_MODAL_MAX
    assert m["p99_raw"] < T3_P99_MAX
    assert m["boundary_impassable"] is True


def test_measure_on_flat_ringed_map():
    m = TerrainValidator(_ringed_flat_hm()).measure()
    assert m["flat_pct"] > T1_MIN_FLAT_FRACTION * 100.0
    assert m["flat_distributed"] is True
    assert m["modal_raw"] == 1000
    assert m["boundary_impassable"] is True


# -- T1: flat ground ----------------------------------------------------------


def test_t1_reports_when_flat_pct_too_low():
    problems = validate_terrain(_ramp_hm())
    assert any(ERROR in p and "T1" in p and "5° slope" in p for p in problems)


def test_t1_reports_when_flat_ground_not_distributed():
    # Flat everywhere except a wall splitting the map so the flat ground does
    # not reach all quadrants as one connected component.
    problems = validate_terrain(_wall_hm())
    assert any(ERROR in p and "T1" in p and "connected" in p for p in problems)


# -- T2: modal height ---------------------------------------------------------


def test_t2_warns_when_modal_height_too_low():
    problems = validate_terrain(_flat_hm(raw=100))
    assert any(WARNING in p and "T2" in p for p in problems)


def test_t2_warns_when_modal_height_too_high():
    problems = validate_terrain(_flat_hm(raw=2000))
    assert any(WARNING in p and "T2" in p for p in problems)


def test_t2_passes_for_mid_range_modal():
    problems = validate_terrain(_flat_hm(raw=1000))
    assert not any("T2" in p for p in problems)


# -- T3: saturation -----------------------------------------------------------


def test_t3_reports_when_p99_at_ceiling():
    problems = validate_terrain(_flat_hm(raw=4000))
    assert any(ERROR in p and "T3" in p for p in problems)


def test_t3_passes_below_ceiling():
    problems = validate_terrain(_flat_hm(raw=1000))
    assert not any("T3" in p for p in problems)


# -- T4: impassable boundary --------------------------------------------------


def test_t4_reports_when_boundary_not_impassable():
    # A flat map with no boundary ring — the edge is as flat as the interior.
    problems = validate_terrain(_flat_hm())
    assert any(ERROR in p and "T4" in p for p in problems)


def test_t4_passes_with_impassable_ring():
    # The generator rings the boundary with impassable terrain (docs/04 §1 T4).
    problems = validate_terrain(generate_terrain(_graph()))
    assert not any("T4" in p for p in problems)