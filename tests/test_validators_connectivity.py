"""Tests for Tier 2 connectivity validation — rules C1-C4 (docs/04 §4, docs/06).

Builds heightmaps + layouts and asserts that a valid connected map passes with
no problems, and that each C-rule catches its specific violation:

- **C1** (error) — every base/geyser/scrap reachable from *every* base by a
  ≤30° ground path.
- **C2** (error) — no enclosed traversable pocket > 200 m² with no exit.
- **C3** (error) — ≥2 topologically distinct routes between every base pair.
- **C4** (warning) — no main-route corridor narrower than 30 m.

The fixtures are 1-zone (1280 m, 256×256 cells) maps so the heightmap and the
layout share the same grid. ``_graph`` places two bases and four geysers on
flat ground, so on a flat heightmap every C-rule passes.
"""

import numpy as np

from bzmap.formats.hg2 import ZONE_SIZE, HeightMap
from bzmap.model.layout import BASE, GEYSER, LayoutGraph
from bzmap.validate.connectivity import (
    ERROR,
    WARNING,
    ConnectivityValidator,
    validate_connectivity,
)


def _graph() -> LayoutGraph:
    """A 1280 m two-base ring with economy, all on flat ground."""
    g = LayoutGraph(1280, 1280, n_teams=2)
    g.add_node("A", 320, 400, BASE, team=0)
    g.add_node("B", 960, 880, BASE, team=1)
    g.add_node("T", 640, 320, "waypoint")
    g.add_node("U", 640, 960, "waypoint")
    g.add_route("A", "T")
    g.add_route("T", "B")
    g.add_route("A", "U")
    g.add_route("U", "B")
    for nid, x, z in (("g1", 400, 500), ("g2", 300, 700),
                      ("g3", 900, 500), ("g4", 1000, 700)):
        g.add_node(nid, x, z, GEYSER)
    return g


def _flat_hm(raw=1000):
    """A perfectly flat heightmap (everything traversable, no walls)."""
    return HeightMap(1, 1, np.full(
        (ZONE_SIZE, ZONE_SIZE), raw, dtype=np.uint16))


def _wall_hm():
    """Flat everywhere except a full-height wall splitting the map in two.

    The wall runs across row ``ZONE_SIZE // 2``, separating base A (above) from
    base B and the far-side geyser (below).
    """
    data = np.full((ZONE_SIZE, ZONE_SIZE), 1000, dtype=np.uint16)
    data[ZONE_SIZE // 2, :] = 4095
    return HeightMap(1, 1, data)


def _gap_wall_hm():
    """A full-height wall with a single 1-cell gap.

    Base A (above the wall) and base B (below) connect only through the gap at
    the map centre, forcing a single narrow corridor between them.
    """
    data = np.full((ZONE_SIZE, ZONE_SIZE), 1000, dtype=np.uint16)
    data[ZONE_SIZE // 2, :] = 4095
    data[ZONE_SIZE // 2, ZONE_SIZE // 2] = 1000
    return HeightMap(1, 1, data)


# -- valid connectivity --------------------------------------------------------


def test_flat_map_passes_all_c_rules():
    assert validate_connectivity(_flat_hm(), _graph()) == []


def test_validator_class_matches_function():
    hm = _flat_hm()
    g = _graph()
    assert ConnectivityValidator(hm, g).validate() == validate_connectivity(hm, g)


def test_accepts_hg2_path(tmp_path):
    hm = _flat_hm()
    p = tmp_path / "map.HG2"
    hm.write(p)
    assert validate_connectivity(p, _graph()) == []


# -- measured values -----------------------------------------------------------


def test_measure_reports_measured_values():
    hm = _flat_hm()
    m = ConnectivityValidator(hm, _graph()).measure()
    assert m["unreachable_economy"] == []
    assert m["trap_areas_m2"] == []
    assert m["single_corridor_pairs"] == []
    # A fully flat map has no impassable cells, so no corridor is bounded and
    # the minimum width is unbounded (None).
    assert m["min_corridor_width_m"] is None
    assert m["traversable_pct"] == 100.0


# -- C1: full connectivity -----------------------------------------------------


def test_c1_reports_unreachable_economy():
    # The wall splits the map; the far-side geyser sits with base B, so it is
    # reachable from B but not from A — a C1 violation.
    g = _graph()
    g.add_node("gfar", 320, 880, GEYSER)
    problems = validate_connectivity(_wall_hm(), g)
    assert any(ERROR in p and "C1" in p and "gfar" in p for p in problems)


def test_c1_passes_when_all_economy_reachable():
    problems = validate_connectivity(_flat_hm(), _graph())
    assert not any("C1" in p for p in problems)


# -- C2: no traps --------------------------------------------------------------


def test_c2_reports_enclosed_pocket():
    # A large flat pocket walled off on all four sides. Reported as a WARNING
    # since the 2026-08-11 recalibration: the stock corpus carries thousands of
    # such pockets (max 7.7 km²), so C2 warns above the corpus p99 (5,000 m²)
    # and never errors — disconnected *economy* is C1's error.
    from bzmap.validate.connectivity import WARNING

    data = np.full((ZONE_SIZE, ZONE_SIZE), 1000, dtype=np.uint16)
    z0, z1 = 100, 140
    x0, x1 = 100, 140
    data[z0 - 1, x0:x1] = 4095
    data[z1, x0:x1] = 4095
    data[z0:z1, x0 - 1] = 4095
    data[z0:z1, x1] = 4095
    hm = HeightMap(1, 1, data)
    problems = validate_connectivity(hm, _graph())
    assert any(WARNING in p and "C2" in p for p in problems)
    assert not any(ERROR in p and "C2" in p for p in problems)


def test_c2_passes_when_no_trap():
    problems = validate_connectivity(_flat_hm(), _graph())
    assert not any("C2" in p for p in problems)


# -- C3: multiple routes -------------------------------------------------------


def test_c3_reports_single_corridor():
    # A wall with a single narrow gap forces one corridor between the bases.
    problems = validate_connectivity(_gap_wall_hm(), _graph())
    assert any(ERROR in p and "C3" in p for p in problems)


def test_c3_passes_with_two_routes():
    problems = validate_connectivity(_flat_hm(), _graph())
    assert not any("C3" in p for p in problems)


# -- C4: corridor width --------------------------------------------------------


def test_c4_warns_on_narrow_corridor():
    # The only route between the bases is a 1-cell-wide gap — far narrower than
    # the 30 m minimum.
    problems = validate_connectivity(_gap_wall_hm(), _graph())
    assert any(WARNING in p and "C4" in p for p in problems)


def test_c4_passes_on_wide_corridor():
    problems = validate_connectivity(_flat_hm(), _graph())
    assert not any("C4" in p for p in problems)