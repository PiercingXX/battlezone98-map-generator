"""Tests for spawn cluster placement (docs/05 ``generate/spawns.py``).

Verifies the spawn generator turns the layout's base sites into concrete spawn
objects satisfying the spawn rules that are checkable without the game pack:

- **B3 (_SW)** — 14 spawns in ``n_teams`` clusters (one per base), each spawn
  on buildable ground and facing outward toward the map centre.
- **B3 (_S)** — one spawn per base, at the base site.
- **B1** — every spawn sits on buildable ground (slope under 5° across a
  20 m radius); a spawn placed on unbuildable ground is snapped to the nearest
  buildable cell.
- **B3 spacing** — within-cluster spawn spacing lands in the corpus 12–70 m
  range.
- Determinism — the same layout and heightmap always yield the same spawns.
"""

import numpy as np
import pytest

from bzmap.formats.hg2 import GRID_M, slope
from bzmap.generate.spawns import (
    SPAWN_MAX_SPACING_M,
    SPAWN_MIN_SPACING_M,
    SpawnGenerator,
    SpawnObject,
    SpawnResult,
    generate_spawns,
)
from bzmap.generate.terrain_gen import generate_terrain
from bzmap.model.layout import SPAWN, SW_SPAWN_COUNT, LayoutGraph

#: 5° slope in metres-per-metre (tan 5°).
SLOPE_5_DEG = np.tan(np.radians(5.0))


def _graph() -> LayoutGraph:
    """A 2560 m two-base ring with balanced, partly-contested economy."""
    g = LayoutGraph(2560, 2560, n_teams=2)
    g.add_node("A", 640, 1280, "base", team=0)
    g.add_node("B", 1920, 1280, "base", team=1)
    g.add_node("T", 1280, 640, "waypoint")
    g.add_node("U", 1280, 1920, "waypoint")
    g.add_route("A", "T")
    g.add_route("T", "B")
    g.add_route("A", "U")
    g.add_route("U", "B")
    return g


def _result(mode: str = "sw") -> SpawnResult:
    """Spawn result for the standard graph on its generated terrain."""
    g = _graph()
    hm = generate_terrain(g)
    return generate_spawns(g, hm, mode=mode)


# -- B3 (_SW) cluster count and teams ------------------------------------------


def test_sw_returns_14_spawns_in_two_clusters():
    res = _result("sw")
    assert isinstance(res, SpawnResult)
    assert len(res.spawns) == SW_SPAWN_COUNT == 14
    assert all(o.kind == SPAWN for o in res.spawns)
    teams = {o.team for o in res.spawns}
    assert teams == {0, 1}
    # 14 spawns split evenly across the two team clusters.
    assert sum(1 for o in res.spawns if o.team == 0) == 7
    assert sum(1 for o in res.spawns if o.team == 1) == 7


def test_sw_cluster_metrics_measured():
    res = _result("sw")
    m = res.metrics()
    assert m["spawn_count"] == 14
    assert m["cluster_count"] == 2


# -- B3 (_S) one per base -------------------------------------------------------


def test_s_returns_one_spawn_per_base():
    res = _result("s")
    g = _graph()
    assert len(res.spawns) == len(g.base_ids) == 2
    # Each _S spawn sits at its base site.
    for o in res.spawns:
        base = g.nodes[o.id.replace("_spawn", "")]
        assert o.x == pytest.approx(base.x)
        assert o.z == pytest.approx(base.z)


# -- B1 buildable ground --------------------------------------------------------


def test_every_spawn_is_on_buildable_ground():
    res = _result("sw")
    g = _graph()
    hm = generate_terrain(g)
    s = slope(hm)
    for o in res.spawns:
        cz = round(o.z / GRID_M)
        cx = round(o.x / GRID_M)
        # The 20 m pad radius must be under 5° slope.
        r = 4  # 20 m / 5 m grid
        zz, xx = np.ogrid[0:s.shape[0], 0:s.shape[1]]
        mask = (zz - cz) ** 2 + (xx - cx) ** 2 <= r * r
        assert np.all(s[mask] <= SLOPE_5_DEG), f"spawn {o.id} not buildable"


def test_spawn_on_unbuildable_ground_is_snapped():
    """A spawn on a cliff face is snapped to the nearest buildable cell."""
    from bzmap.formats.hg2 import HeightMap

    # A 1280 m single-zone heightmap: flat plateau at raw 1000 with a steep
    # cliff band across the middle (raw drops to 100 over 4 cells).
    n = 256  # one zone
    data = np.full((n, n), 1000, dtype=np.uint16)
    data[96:100, :] = np.linspace(1000, 100, 4, dtype=np.uint16)[:, None]
    data[100:, :] = 100
    hm = HeightMap(1, 1, data)

    g = LayoutGraph(1280, 1280, n_teams=2)
    g.add_node("A", 640, 640, "base", team=0)
    g.add_node("B", 640, 490, "base", team=1)
    g.add_route("A", "B")

    # _S mode places a spawn exactly at the base site; put base B on the cliff
    # face so its spawn must be snapped to buildable ground.
    res = generate_spawns(g, hm, mode="s")
    b_spawn = next(o for o in res.spawns if o.id == "B_spawn")
    s = slope(hm)
    cz = round(b_spawn.z / GRID_M)
    cx = round(b_spawn.x / GRID_M)
    assert s[cz, cx] <= SLOPE_5_DEG
    assert (b_spawn.x, b_spawn.z) != (640.0, 490.0)


# -- B3 spacing -----------------------------------------------------------------


def test_within_cluster_spacing_in_corpus_range():
    res = _result("sw")
    m = res.metrics()
    # Corpus range: spawns within a cluster sit 12–70 m apart.
    assert m["min_cluster_spacing_m"] >= SPAWN_MIN_SPACING_M - 1e-9
    assert m["max_cluster_spacing_m"] <= SPAWN_MAX_SPACING_M + 1e-9


# -- B3 facing ------------------------------------------------------------------


def test_spawns_face_outward_toward_map_centre():
    res = _result("sw")
    g = _graph()
    cx = g.width_m / 2.0
    cz = g.depth_m / 2.0
    for o in res.spawns:
        # The yaw should point from the spawn toward the map centre.
        expected = np.degrees(np.arctan2(cx - o.x, cz - o.z))
        assert o.yaw == pytest.approx(expected, abs=1e-6)


# -- determinism ----------------------------------------------------------------


def test_same_inputs_are_deterministic():
    # Determinism is tied to the layout and heightmap, not the seed: the same
    # inputs must yield the same spawns regardless of seed (docs/08).
    g = _graph()
    hm = generate_terrain(g)
    a = generate_spawns(g, hm, mode="sw", seed=42)
    b = generate_spawns(g, hm, mode="sw", seed=7)
    assert [(o.id, o.x, o.z, o.team, o.yaw) for o in a.spawns] == \
           [(o.id, o.x, o.z, o.team, o.yaw) for o in b.spawns]


# -- generator class ------------------------------------------------------------


def test_generator_class_matches_function():
    g = _graph()
    hm = generate_terrain(g)
    a = SpawnGenerator().generate(g, hm, mode="sw")
    b = generate_spawns(g, hm, mode="sw")
    assert [(o.id, o.x, o.z) for o in a.spawns] == \
           [(o.id, o.x, o.z) for o in b.spawns]


def test_spawn_object_is_frozen():
    with pytest.raises(AttributeError):
        SpawnObject(id="x", x=0, z=0).team = 5