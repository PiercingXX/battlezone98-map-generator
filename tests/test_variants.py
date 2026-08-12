"""Tests for variant object sets (docs/05 ``generate/variants.py``).

Verifies the variant generator derives the four BZN object sets from one layout
per the corpus variant system:

- **base** (deathmatch) — only the player and the 14-spawn _SW cluster set.
  No economy at all.
- **_S** (strategy) — the full economy plus one spawn per base plus the player.
- **_ST** (strategy teams) — the full economy plus the full 14-spawn set plus
  the player.
- **_SW** (wingman teams) — the full economy, the full 14-spawn set, the
  player, and a repair/supply depot pair for each team.

Also verifies ground-snapping (R3), per-class labels (docs/02 §5), exactly one
player per variant, and determinism.
"""

import numpy as np
import pytest

from bzmap.formats.hg2 import sample_m
from bzmap.generate.economy import generate_economy
from bzmap.generate.spawns import generate_spawns
from bzmap.generate.terrain_gen import generate_terrain
from bzmap.generate.variants import (
    PLAYER,
    REPAIR_DEPOT,
    SCRAP_CLASSES,
    SUPPLY_DEPOT,
    VariantGenerator,
    VariantObject,
    VariantsResult,
    generate_variants,
)
from bzmap.model.layout import SW_SPAWN_COUNT, LayoutGraph


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
    for nid, x, z in (("g1", 700, 1100), ("g2", 600, 1400),
                      ("g3", 1900, 1100), ("g4", 2000, 1400)):
        g.add_node(nid, x, z, "geyser")
    g.add_node("s1", 750, 1200, "scrap")
    g.add_node("s2", 1850, 1200, "scrap")
    for nid in ("g1", "g2", "s1"):
        g.add_route(nid, "A")
    for nid in ("g3", "g4", "s2"):
        g.add_route(nid, "B")
    g.add_node("g5", 1300, 1700, "geyser")
    g.add_node("g6", 1260, 1700, "geyser")
    g.add_route("g5", "A")
    g.add_route("g5", "B")
    g.add_route("g6", "A")
    g.add_route("g6", "B")
    return g


def _result() -> VariantsResult:
    """Variants result for the standard graph on its generated terrain."""
    g = _graph()
    hm = generate_terrain(g)
    economy = generate_economy(g, hm)
    sw = generate_spawns(g, hm, mode="sw")
    s = generate_spawns(g, hm, mode="s")
    return generate_variants(g, hm, economy, sw, s)


# -- structure -----------------------------------------------------------------


def test_returns_variants_result_with_four_sets():
    res = _result()
    assert isinstance(res, VariantsResult)
    assert {k: v.name for k, v in res.variants().items()} == {
        "": "base", "_S": "_S", "_ST": "_ST", "_SW": "_SW",
    }


# -- base (deathmatch): player + 14 spawns, no economy -------------------------


def test_base_has_player_and_14_spawns_only():
    res = _result()
    base = res.base
    assert len(base.player) == 1
    assert len(base.spawns) == SW_SPAWN_COUNT == 14
    # No economy at all in the base deathmatch set (corpus convention).
    assert base.geysers == []
    assert base.scrap == []
    assert base.depots == []


def test_base_spawns_split_across_two_team_clusters():
    res = _result()
    teams = {o.team for o in res.base.spawns}
    assert teams == {0, 1}
    assert sum(1 for o in res.base.spawns if o.team == 0) == 7
    assert sum(1 for o in res.base.spawns if o.team == 1) == 7


# -- _S: full economy + one spawn per base -------------------------------------


def test_s_has_full_economy_and_one_spawn_per_base():
    res = _result()
    g = _graph()
    s = res.s
    assert len(s.player) == 1
    assert len(s.spawns) == len(g.base_ids) == 2
    # Full economy carried into the strategy set.
    assert len(s.geysers) == 6
    assert len(s.scrap) == 2


def test_s_spawns_sit_at_base_sites():
    res = _result()
    g = _graph()
    base_sites = {(b.x, b.z) for b in (g.nodes[i] for i in g.base_ids)}
    for o in res.s.spawns:
        # The strategy spawn is placed exactly at a base site (one per base).
        assert (o.x, o.z) in base_sites


# -- _ST: full economy + full 14-spawn set -------------------------------------


def test_st_has_full_economy_and_14_spawns():
    res = _result()
    st = res.st
    assert len(st.player) == 1
    assert len(st.spawns) == SW_SPAWN_COUNT
    assert len(st.geysers) == 6
    assert len(st.scrap) == 2
    assert st.depots == []


# -- _SW: full economy + 14 spawns + team depots -------------------------------


def test_sw_has_full_economy_and_14_spawns():
    res = _result()
    sw = res.sw
    assert len(sw.player) == 1
    assert len(sw.spawns) == SW_SPAWN_COUNT
    assert len(sw.geysers) == 6
    assert len(sw.scrap) == 2


def test_sw_has_repair_and_supply_depot_per_team():
    res = _result()
    sw = res.sw
    repairs = [o for o in sw.depots if o.prjid == REPAIR_DEPOT]
    supplies = [o for o in sw.depots if o.prjid == SUPPLY_DEPOT]
    assert len(repairs) == 2
    assert len(supplies) == 2
    # Depots sit on teams 1 and 8 (corpus convention).
    assert {o.team for o in repairs} == {1, 8}
    assert {o.team for o in supplies} == {1, 8}


# -- player ---------------------------------------------------------------------


def test_every_variant_has_exactly_one_player_team_1():
    res = _result()
    for vs in res.variants().values():
        assert len(vs.player) == 1
        assert vs.player[0].prjid == PLAYER
        assert vs.player[0].team == 1


def test_player_sits_at_first_base_and_faces_centre():
    res = _result()
    g = _graph()
    p = res.base.player[0]
    base = g.nodes[g.base_ids[0]]
    assert p.x == pytest.approx(base.x)
    assert p.z == pytest.approx(base.z)
    expected = np.degrees(np.arctan2(g.width_m / 2 - p.x, g.depth_m / 2 - p.z))
    assert p.yaw == pytest.approx(expected, abs=1e-6)


# -- ground snapping (R3) -------------------------------------------------------


def test_every_object_y_is_ground_snapped():
    res = _result()
    g = _graph()
    hm = generate_terrain(g)
    for vs in res.variants().values():
        for o in vs.objects:
            assert o.y == pytest.approx(sample_m(hm, o.x, o.z))


# -- labels (docs/02 §5) --------------------------------------------------------


def test_scrap_objects_carry_npscr_classes():
    res = _result()
    classes = {o.prjid for o in res.sw.scrap}
    assert classes <= set(SCRAP_CLASSES)


def test_labels_are_per_class_with_role_suffix():
    res = _result()
    for o in res.sw.objects:
        assert o.label.endswith(
            ("_geyser", "_scrap", "_spawnpnt", "_wingman", "_repairdepot",
             "_supplydepot")
        )
        assert o.label.startswith(o.prjid)


# -- determinism ----------------------------------------------------------------


def test_same_inputs_are_deterministic():
    # Determinism is tied to the inputs, not the seed: the same layout,
    # heightmap, economy and spawns must yield the same sets regardless of seed.
    g = _graph()
    hm = generate_terrain(g)
    economy = generate_economy(g, hm)
    sw = generate_spawns(g, hm, mode="sw")
    s = generate_spawns(g, hm, mode="s")
    a = generate_variants(g, hm, economy, sw, s, seed=42)
    b = generate_variants(g, hm, economy, sw, s, seed=7)
    for name in ("", "_S", "_ST", "_SW"):
        va, vb = a.variants()[name], b.variants()[name]
        assert [(o.prjid, o.x, o.z, o.y, o.team, o.label)
                for o in va.objects] == \
               [(o.prjid, o.x, o.z, o.y, o.team, o.label)
                for o in vb.objects]


# -- generator class ------------------------------------------------------------


def test_generator_class_matches_function():
    g = _graph()
    hm = generate_terrain(g)
    economy = generate_economy(g, hm)
    sw = generate_spawns(g, hm, mode="sw")
    s = generate_spawns(g, hm, mode="s")
    a = VariantGenerator().generate(g, hm, economy, sw, s)
    b = generate_variants(g, hm, economy, sw, s)
    for name in ("", "_S", "_ST", "_SW"):
        assert [(o.prjid, o.x, o.z) for o in a.variants()[name].objects] == \
               [(o.prjid, o.x, o.z) for o in b.variants()[name].objects]


def test_variant_object_is_frozen():
    with pytest.raises(AttributeError):
        VariantObject(prjid="player", x=0, z=0, y=0, yaw=0, team=1,
                      label="player0_wingman").team = 5

def test_depots_are_never_colocated():
    """The repair and supply depots previously both landed at
    base + (offset, offset) — two interpenetrating solids, a
    pathological collision-churn class (task #7)."""
    from math import hypot

    from bzmap import cli

    result = cli.generate_map(seed=42)
    layout = cli.build_layout(result.width_m, result.depth_m,
                              result.n_teams, result.seed)
    from bzmap.generate.economy import generate_economy
    from bzmap.generate.spawns import generate_spawns
    from bzmap.generate.terrain_gen import generate_terrain
    from bzmap.generate.variants import generate_variants

    hm = generate_terrain(layout, result.seed)
    eco = generate_economy(layout, hm, result.seed)
    sw = generate_spawns(layout, hm, mode="sw", seed=result.seed)
    s = generate_spawns(layout, hm, mode="s", seed=result.seed)
    variants = generate_variants(layout, hm, eco, sw, s, result.seed)

    objs = variants.variants()["_SW"].objects
    hangars = [(o.x, o.z) for o in objs if o.prjid == "abhang"]
    depots = [(o.x, o.z) for o in objs if o.prjid == "absupp"]
    assert hangars and depots
    for hx, hz in hangars:
        for dx, dz in depots:
            assert hypot(hx - dx, hz - dz) >= 40.0, (
                f"buildings interpenetrate: abhang({hx},{hz}) absupp({dx},{dz})"
            )
