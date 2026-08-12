"""Tests for Tier 2 balance validation — rules E4-E5, B1-B3 (docs/04 §2-§3, docs/06).

Builds heightmaps + layouts (+ placed spawns) and asserts that a balanced map
passes with no problems, and that each balance rule catches its specific
violation:

- **E4** (error) — per-base economy within 5% across bases.
- **E5** (warning) — 30-50% of geysers contested.
- **B1** (error) — each base has a contiguous buildable pocket ≥ 4,000 m².
- **B2** (warning) — nearest-base separation is 35-60% of the diagonal.
- **B3** (error) — 14 spawns in n_teams clusters, 12-70 m apart.

The fixtures are 1-zone (1280 m, 256x256 cells) maps so the heightmap and the
layout share the same grid. ``_graph`` places two bases, a connected route ring,
and economy nodes routed to their bases; on a flat heightmap with a balanced
economy and a generated spawn set every balance rule passes.
"""

import numpy as np

from bzmap.formats.hg2 import ZONE_SIZE, HeightMap
from bzmap.generate.spawns import generate_spawns
from bzmap.model.layout import (
    B2_MIN_FRAC,
    BASE,
    E4_MAX_SPREAD,
    E5_MIN_FRAC,
    GEYSER,
    SW_SPAWN_COUNT,
    LayoutGraph,
)
from bzmap.validate.balance import (
    B1_MIN_POCKET_M2,
    ERROR,
    WARNING,
    BalanceValidator,
    validate_balance,
)


def _graph() -> LayoutGraph:
    """A 1280 m two-base ring with economy routed to its base, all on flat ground.

    Six geysers: two near each base and two contested at the midpoint (one
    leaning to each base), so per-base economy is balanced (3/3) and the
    contested share is 2/6 = 33%.
    """
    g = LayoutGraph(1280, 1280, n_teams=2)
    g.add_node("A", 320, 400, BASE, team=0)
    g.add_node("B", 960, 880, BASE, team=1)
    g.add_node("T", 640, 320, "waypoint")
    g.add_node("U", 640, 960, "waypoint")
    g.add_route("A", "T")
    g.add_route("T", "B")
    g.add_route("A", "U")
    g.add_route("U", "B")
    # Two geysers per base, each routed to its own base.
    for nid, x, z, base in (("g1", 430, 520, "A"), ("g2", 300, 700, "A"),
                            ("g3", 900, 500, "B"), ("g4", 1000, 700, "B")):
        g.add_node(nid, x, z, GEYSER)
        g.add_route(nid, base)
    # Two contested geysers at the midpoint, one leaning to each base.
    g.add_node("g5", 639, 639, GEYSER)
    g.add_route("g5", "A")
    g.add_route("g5", "B")
    g.add_node("g6", 641, 641, GEYSER)
    g.add_route("g6", "A")
    g.add_route("g6", "B")
    return g


def _flat_hm(raw=1000):
    """A perfectly flat heightmap (everything buildable, no walls)."""
    return HeightMap(1, 1, np.full(
        (ZONE_SIZE, ZONE_SIZE), raw, dtype=np.uint16))


def _island_hm():
    """A steep ramp with a small flat island (buildable pocket < 4,000 m²).

    The island is 10x10 cells = 50x50 m = 2,500 m², below the 4,000 m² B1
    threshold. A base placed on it fails B1.
    """
    data = ((np.mgrid[0:ZONE_SIZE, 0:ZONE_SIZE][0]
             + np.mgrid[0:ZONE_SIZE, 0:ZONE_SIZE][1]) * 5).astype(np.uint16)
    z0, x0 = 120, 120
    data[z0:z0 + 10, x0:x0 + 10] = 1000
    return HeightMap(1, 1, data)


def _spawns(layout, hm):
    """The 14-spawn _SW set for ``layout`` on ``hm`` (valid B3 geometry)."""
    return generate_spawns(layout, hm, mode="sw").objects


# -- valid balance ------------------------------------------------------------


def test_flat_map_passes_all_balance_rules():
    g = _graph()
    assert validate_balance(_flat_hm(), g, _spawns(g, _flat_hm())) == []


def test_validator_class_matches_function():
    g = _graph()
    hm = _flat_hm()
    spawns = _spawns(g, hm)
    assert BalanceValidator(hm, g, spawns).validate() == validate_balance(
        hm, g, spawns)


def test_accepts_hg2_path(tmp_path):
    g = _graph()
    hm = _flat_hm()
    p = tmp_path / "map.HG2"
    hm.write(p)
    assert validate_balance(p, g, _spawns(g, hm)) == []


# -- measured values ----------------------------------------------------------


def test_measure_reports_measured_values():
    g = _graph()
    hm = _flat_hm()
    m = BalanceValidator(hm, g, _spawns(g, hm)).measure()
    assert m["per_base_economy"] == {"A": 3, "B": 3}
    assert m["e4_spread"] == 0.0
    assert m["e5_contested_frac"] == 2 / 6
    # A flat map is one giant buildable pocket at every base.
    assert m["base_pocket_m2"]["A"] >= 4000.0
    assert m["b2_separation_frac"] > 0.0
    assert m["spawn_count"] == 14
    assert m["spawn_cluster_count"] == 2


# -- E4: per-base economy ------------------------------------------------------


def test_e4_reports_unbalanced_economy():
    # Give base A three extra geysers so its economy far exceeds base B's.
    g = _graph()
    for nid, x, z in (("x1", 200, 300), ("x2", 200, 320), ("x3", 200, 340)):
        g.add_node(nid, x, z, GEYSER)
        g.add_route(nid, "A")
    hm = _flat_hm()
    m = BalanceValidator(hm, g, _spawns(g, hm)).measure()
    # A now has 6 economy nodes vs B's 3: a 100% spread, far above 5%.
    assert m["per_base_economy"]["A"] == 6
    assert m["per_base_economy"]["B"] == 3
    assert m["e4_spread"] > E4_MAX_SPREAD
    problems = validate_balance(hm, g, _spawns(g, hm))
    assert any(ERROR in p and "E4" in p for p in problems)


def test_e4_passes_when_balanced():
    g = _graph()
    problems = validate_balance(_flat_hm(), g, _spawns(g, _flat_hm()))
    assert not any("E4" in p for p in problems)


# -- E5: contested geysers -----------------------------------------------------


def test_e5_warns_when_no_geysers_contested():
    # All geysers near base A, none contested (0% < the 30% E5 floor).
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
                      ("g3", 350, 600), ("g4", 420, 650)):
        g.add_node(nid, x, z, GEYSER)
        g.add_route(nid, "A")
    hm = _flat_hm()
    m = BalanceValidator(hm, g, _spawns(g, hm)).measure()
    # Every geyser is routed only to A, so none is contested: 0% < 30%.
    assert m["e5_contested_frac"] == 0.0
    assert m["e5_contested_frac"] < E5_MIN_FRAC
    problems = validate_balance(hm, g, _spawns(g, hm))
    assert any(WARNING in p and "E5" in p for p in problems)


def test_e5_passes_with_contested_share():
    g = _graph()
    problems = validate_balance(_flat_hm(), g, _spawns(g, _flat_hm()))
    assert not any("E5" in p for p in problems)


# -- B1: buildable pocket ------------------------------------------------------


def test_b1_reports_small_pocket():
    # Base A sits on a 2,500 m² island; base B on the ramp (no pocket at all).
    g = _graph()
    g.add_node("A", 122 * 5, 122 * 5, BASE, team=0)
    hm = _island_hm()
    m = BalanceValidator(hm, g, _spawns(g, hm)).measure()
    # The island is 10x10 cells = 50x50 m = 2,500 m²; the buildable pocket is
    # at most that (gradient edge effects shrink it), far below the 4,000 m²
    # B1 floor.
    assert m["base_pocket_m2"]["A"] < B1_MIN_POCKET_M2
    assert m["base_pocket_m2"]["A"] <= 10 * 10 * 5 * 5
    problems = validate_balance(hm, g, _spawns(g, hm))
    assert any(ERROR in p and "B1" in p and "A" in p for p in problems)


def test_b1_passes_with_large_pocket():
    g = _graph()
    problems = validate_balance(_flat_hm(), g, _spawns(g, _flat_hm()))
    assert not any("B1" in p for p in problems)


# -- B2: base separation -------------------------------------------------------


def test_b2_warns_when_bases_too_close():
    # Move base B next to base A and route them directly so separation is a
    # tiny fraction of the diagonal (far below the 35% B2 floor).
    g = _graph()
    g.add_node("B", 360, 440, BASE, team=1)
    g.add_route("A", "B")
    hm = _flat_hm()
    m = BalanceValidator(hm, g, _spawns(g, hm)).measure()
    assert m["b2_separation_frac"] < B2_MIN_FRAC
    problems = validate_balance(hm, g, _spawns(g, hm))
    assert any(WARNING in p and "B2" in p for p in problems)


def test_b2_passes_with_correct_separation():
    g = _graph()
    problems = validate_balance(_flat_hm(), g, _spawns(g, _flat_hm()))
    assert not any("B2" in p for p in problems)


# -- B3: spawn geometry --------------------------------------------------------


def test_b3_reports_wrong_spawn_count():
    g = _graph()
    spawns = _spawns(g, _flat_hm())[:7]  # only 7 of 14
    hm = _flat_hm()
    m = BalanceValidator(hm, g, spawns).measure()
    assert m["spawn_count"] == 7
    assert m["spawn_count"] != SW_SPAWN_COUNT
    problems = validate_balance(hm, g, spawns)
    # The count-specific message names the mismatch, not a spacing failure.
    assert any(ERROR in p and "B3" in p and "7" in p for p in problems)


def test_b3_passes_with_correct_geometry():
    g = _graph()
    problems = validate_balance(_flat_hm(), g, _spawns(g, _flat_hm()))
    assert not any("B3" in p for p in problems)