"""Tests for economy placement (docs/05 ``generate/economy.py``).

Verifies the economy generator turns the layout's geyser/scrap nodes into
concrete object placements satisfying the economy rules that are checkable
without the game pack:

- **E1** — geyser density lands in the corpus range 0.5–6.4/km².
- **E2** — scrap objects are assigned the ``npscr1/2/3`` classes.
- **E3** — every geyser sits on buildable ground (slope under 5° across a
  20 m radius); a geyser placed on unbuildable ground is snapped to the
  nearest buildable cell.
- **E4** — per-base economy is within 5% across bases.
- **E5** — contested geysers are flagged when roughly equidistant from two
  bases.
- Determinism — the same layout and heightmap always yield the same objects.
"""

import numpy as np
import pytest

from bzmap.formats.hg2 import GRID_M, slope
from bzmap.generate.economy import (
    E1_MAX_PER_KM2,
    E1_MIN_PER_KM2,
    EconomyGenerator,
    EconomyObject,
    EconomyResult,
    generate_economy,
)
from bzmap.generate.terrain_gen import generate_terrain
from bzmap.model.layout import GEYSER, SCRAP, LayoutGraph

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
    # Home economy: two geysers + one scrap per base, routed to their base.
    for nid, x, z in (("g1", 700, 1100), ("g2", 600, 1400),
                      ("g3", 1900, 1100), ("g4", 2000, 1400)):
        g.add_node(nid, x, z, GEYSER)
    g.add_node("s1", 750, 1200, SCRAP)
    g.add_node("s2", 1850, 1200, SCRAP)
    for nid in ("g1", "g2", "s1"):
        g.add_route(nid, "A")
    for nid in ("g3", "g4", "s2"):
        g.add_route(nid, "B")
    # Contested geysers near the midline, tied to both bases.
    g.add_node("g5", 1300, 1700, GEYSER)
    g.add_node("g6", 1260, 1700, GEYSER)
    g.add_route("g5", "A")
    g.add_route("g5", "B")
    g.add_route("g6", "A")
    g.add_route("g6", "B")
    return g


def _result() -> EconomyResult:
    """Economy result for the standard graph on its generated terrain."""
    g = _graph()
    hm = generate_terrain(g)
    return generate_economy(g, hm)


# -- object set --------------------------------------------------------------


def test_returns_economy_result_with_all_nodes():
    res = _result()
    assert isinstance(res, EconomyResult)
    assert len(res.objects) == 8  # 6 geysers + 2 scrap
    assert len(res.geysers) == 6
    assert len(res.scrap) == 2


def test_scrap_objects_get_npscr_classes():
    res = _result()
    classes = {o.scrap_type for o in res.scrap}
    assert classes <= {"npscr1", "npscr2", "npscr3"}
    assert all(o.kind == SCRAP for o in res.scrap)


def test_geyser_positions_preserved_on_flat_terrain():
    res = _result()
    g = _graph()
    for o in res.geysers:
        node = g.nodes[o.id]
        assert o.x == pytest.approx(node.x)
        assert o.z == pytest.approx(node.z)


# -- E3 buildable ground -----------------------------------------------------


def test_every_geyser_is_on_buildable_ground():
    res = _result()
    g = _graph()
    hm = generate_terrain(g)
    s = slope(hm)
    for o in res.geysers:
        cz = round(o.z / GRID_M)
        cx = round(o.x / GRID_M)
        # The 20 m pad radius must be under 5° slope.
        r = 4  # 20 m / 5 m grid
        zz, xx = np.ogrid[0:s.shape[0], 0:s.shape[1]]
        mask = (zz - cz) ** 2 + (xx - cx) ** 2 <= r * r
        assert np.all(s[mask] <= SLOPE_5_DEG), f"geyser {o.id} not buildable"


def test_geyser_on_unbuildable_ground_is_snapped():
    """A geyser on a cliff face is snapped to the nearest buildable cell."""
    import numpy as np

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
    g.add_node("B", 640, 200, "base", team=1)
    g.add_route("A", "B")
    # A geyser sitting right on the cliff face (steep, unbuildable).
    g.add_node("g_bad", 640, 490, GEYSER)
    g.add_route("g_bad", "A")

    res = generate_economy(g, hm)
    snapped = next(o for o in res.geysers if o.id == "g_bad")
    # Snapped position must be buildable and away from the cliff.
    s = slope(hm)
    cz = round(snapped.z / GRID_M)
    cx = round(snapped.x / GRID_M)
    assert s[cz, cx] <= SLOPE_5_DEG
    assert (snapped.x, snapped.z) != (640.0, 490.0)


# -- E4 per-base economy -----------------------------------------------------


def test_every_object_assigned_to_a_base():
    res = _result()
    assert all(o.team in (0, 1) for o in res.objects)


def test_e4_spread_within_five_percent():
    res = _result()
    m = res.metrics()
    assert m["e4_spread"] <= 0.05


# -- E5 contested geysers ----------------------------------------------------


def test_contested_geysers_flagged():
    res = _result()
    contested = [o for o in res.geysers if o.contested]
    # g5/g6 are tied to both bases -> contested; the home geysers are not.
    assert {o.id for o in contested} == {"g5", "g6"}


def test_e5_contested_fraction_measured():
    res = _result()
    m = res.metrics()
    assert m["e5_contested_frac"] == pytest.approx(2 / 6)


# -- E1 density and E2 count -------------------------------------------------


def test_e1_density_in_corpus_range():
    res = _result()
    m = res.metrics()
    density = m["geyser_density_per_km2"]
    # E1 acceptance: density lands in the corpus range 0.5–6.4/km².
    assert E1_MIN_PER_KM2 <= density <= E1_MAX_PER_KM2


def test_e2_scrap_count_measured():
    res = _result()
    # The metric must equal the number of scrap objects actually placed.
    assert res.metrics()["scrap_count"] == len(res.scrap)


# -- determinism -------------------------------------------------------------


def test_same_inputs_are_deterministic():
    # Determinism is tied to the layout and heightmap, not the seed: the same
    # inputs must yield the same objects regardless of seed (docs/08).
    g = _graph()
    hm = generate_terrain(g)
    a = generate_economy(g, hm, seed=42)
    b = generate_economy(g, hm, seed=7)
    assert [(o.id, o.x, o.z, o.team, o.contested, o.scrap_type)
            for o in a.objects] == \
           [(o.id, o.x, o.z, o.team, o.contested, o.scrap_type)
            for o in b.objects]


# -- generator class ---------------------------------------------------------


def test_generator_class_matches_function():
    g = _graph()
    hm = generate_terrain(g)
    a = EconomyGenerator().generate(g, hm)
    b = generate_economy(g, hm)
    assert [(o.id, o.x, o.z) for o in a.objects] == \
           [(o.id, o.x, o.z) for o in b.objects]


def test_economy_object_is_frozen():
    with pytest.raises(AttributeError):
        EconomyObject(id="x", x=0, z=0, kind=GEYSER).team = 5