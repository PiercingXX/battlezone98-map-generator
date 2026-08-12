"""Tests for the layout graph and its pre-terrain validation (docs/04 §7).

The layout graph is validated *before* terrain synthesis, so every rule it
checks must be computable from graph structure alone (positions, routes,
path distances) — no heightmap.  These tests build small graphs directly
and assert the graph-level rules C1, C3, B2, E4, E5 and B3 from docs/04.
"""

import pytest

from bzmap.model.layout import (
    BASE,
    GEYSER,
    SCRAP,
    SPAWN,
    WAYPOINT,
    LayoutGraph,
    LayoutReport,
    Node,
    RuleResult,
)


def _valid_graph() -> LayoutGraph:
    """A 2560 m two-base ring with balanced, partly-contested economy.

    Bases A(640,1280) and B(1920,1280) are 1280 m apart (≈35–60% of the
    3620 m diagonal when routed through the ring).  The top/bottom ring
    gives two distinct A↔B routes (C3).  Economy splits 4/4 (E4) with 2 of
    6 geysers contested (E5).
    """
    g = LayoutGraph(2560, 2560, n_teams=2)
    g.add_node("A", 640, 1280, BASE, team=0)
    g.add_node("B", 1920, 1280, BASE, team=1)
    # Ring nodes give a second route between the bases.
    g.add_node("T", 1280, 640, WAYPOINT)  # top ring waypoint
    g.add_node("U", 1280, 1920, WAYPOINT)  # bottom ring waypoint
    g.add_route("A", "T")
    g.add_route("T", "B")
    g.add_route("A", "U")
    g.add_route("U", "B")

    # Home economy: two geysers + one scrap per base.
    g.add_node("g1", 700, 1100, GEYSER)
    g.add_node("g2", 600, 1400, GEYSER)
    g.add_node("s1", 750, 1200, SCRAP)
    g.add_node("g3", 1900, 1100, GEYSER)
    g.add_node("g4", 2000, 1400, GEYSER)
    g.add_node("s2", 1850, 1200, SCRAP)
    for nid in ("g1", "g2", "s1"):
        g.add_route(nid, "A")
    for nid in ("g3", "g4", "s2"):
        g.add_route(nid, "B")

    # Contested geysers near the midline, each tied to both bases.
    g.add_node("g5", 1300, 1700, GEYSER)
    g.add_node("g6", 1260, 1700, GEYSER)
    g.add_route("g5", "A")
    g.add_route("g5", "B")
    g.add_route("g6", "A")
    g.add_route("g6", "B")
    return g


# -- construction and accessors -------------------------------------------


def test_add_node_and_replace():
    g = LayoutGraph(100, 100)
    g.add_node("a", 1, 2, BASE)
    assert g.nodes["a"] == Node("a", 1, 2, BASE, -1)
    g.add_node("a", 9, 9, GEYSER)
    assert g.nodes["a"].kind == GEYSER  # replaced


def test_add_route_defaults_to_euclidean():
    g = LayoutGraph(100, 100)
    g.add_node("a", 0, 0, BASE)
    g.add_node("b", 3, 4, BASE)
    assert g.add_route("a", "b") == pytest.approx(5.0)


def test_add_route_unknown_node_raises():
    g = LayoutGraph(100, 100)
    g.add_node("a", 0, 0, BASE)
    with pytest.raises(KeyError):
        g.add_route("a", "ghost")


def test_path_distance_and_shortest_path():
    g = LayoutGraph(100, 100)
    g.add_node("a", 0, 0, BASE)
    g.add_node("m", 50, 0, SCRAP)
    g.add_node("b", 100, 0, BASE)
    g.add_route("a", "m")
    g.add_route("m", "b")
    assert g.path_distance("a", "b") == pytest.approx(100.0)
    assert g.shortest_path("a", "b") == ["a", "m", "b"]
    assert g.path_distance("a", "a") == 0.0


def test_path_distance_none_when_disconnected():
    g = LayoutGraph(100, 100)
    g.add_node("a", 0, 0, BASE)
    g.add_node("b", 50, 0, BASE)
    assert g.path_distance("a", "b") is None


def test_nearest_base_by_path():
    g = LayoutGraph(100, 100)
    g.add_node("A", 0, 0, BASE)
    g.add_node("B", 100, 0, BASE)
    g.add_node("e", 60, 0, GEYSER)
    g.add_route("e", "A", length=70)
    g.add_route("e", "B", length=40)
    assert g.nearest_base("e") == ("B", 40.0)


def test_kind_properties():
    g = _valid_graph()
    assert set(g.base_ids) == {"A", "B"}
    assert set(g.geyser_ids) == {"g1", "g2", "g3", "g4", "g5", "g6"}
    assert len(g.economy_ids) == 8
    assert g.diagonal_m() == pytest.approx(2560 * 2 ** 0.5)


# -- a valid layout passes every rule -------------------------------------


def test_valid_layout_passes():
    report = _valid_graph().validate()
    assert isinstance(report, LayoutReport)
    assert report.ok, [r.message for r in report.rules if not r.passed]


def test_report_by_name():
    report = _valid_graph().validate()
    assert report.by_name("C1").passed
    assert report.by_name("C3").passed
    assert report.by_name("B2").passed
    assert report.by_name("E4").passed
    assert report.by_name("E5").passed
    assert report.by_name("B3").passed  # no spawns yet -> skipped


# -- C1 connectivity ------------------------------------------------------


def test_disconnected_node_fails_c1():
    g = _valid_graph()
    g.add_node("lost", 100, 100, GEYSER)  # no routes
    report = g.validate()
    assert not report.by_name("C1").passed
    assert not report.ok


def test_no_bases_fails_c1():
    g = LayoutGraph(100, 100)
    g.add_node("e", 10, 10, GEYSER)
    assert not g.validate().by_name("C1").passed


# -- C3 multiple routes ---------------------------------------------------


def test_single_corridor_fails_c3():
    g = LayoutGraph(1000, 1000)
    g.add_node("A", 0, 0, BASE)
    g.add_node("X", 500, 0, SCRAP)
    g.add_node("B", 1000, 0, BASE)
    g.add_route("A", "X")
    g.add_route("X", "B")  # only one A<->B route
    assert not g.validate().by_name("C3").passed


def test_multiple_routes_passes_c3():
    g = _valid_graph()
    assert g.validate().by_name("C3").passed


# -- B2 base separation ---------------------------------------------------


def test_bases_too_close_fails_b2():
    g = LayoutGraph(2560, 2560)
    g.add_node("A", 1280, 1280, BASE)
    g.add_node("B", 1330, 1280, BASE)  # 50 m apart
    g.add_route("A", "B")
    assert not g.validate().by_name("B2").passed


# -- E4 economy balance ---------------------------------------------------


def test_unbalanced_economy_fails_e4():
    g = LayoutGraph(2560, 2560)
    g.add_node("A", 640, 1280, BASE)
    g.add_node("B", 1920, 1280, BASE)
    g.add_route("A", "B")
    # 5 geysers all near A, 0 near B.
    for i in range(5):
        g.add_node(f"g{i}", 660 + i * 10, 1300, GEYSER)
        g.add_route(f"g{i}", "A")
    assert not g.validate().by_name("E4").passed


def test_balanced_economy_passes_e4():
    g = _valid_graph()
    assert g.validate().by_name("E4").passed


# -- E5 contested geysers -------------------------------------------------


def test_no_contested_geysers_fails_e5():
    g = LayoutGraph(2560, 2560)
    g.add_node("A", 640, 1280, BASE)
    g.add_node("B", 1920, 1280, BASE)
    g.add_route("A", "B")
    # Geysers all hugging their own base -> nothing contested.
    for i in range(2):
        g.add_node(f"ga{i}", 700 + i * 10, 1300, GEYSER)
        g.add_route(f"ga{i}", "A")
        g.add_node(f"gb{i}", 1880 + i * 10, 1300, GEYSER)
        g.add_route(f"gb{i}", "B")
    assert not g.validate().by_name("E5").passed


def test_contested_share_in_range_passes_e5():
    g = _valid_graph()
    assert g.validate().by_name("E5").passed


# -- B3 spawns ------------------------------------------------------------


def test_spawns_skipped_when_absent():
    g = _valid_graph()
    assert g.validate().by_name("B3").passed


def test_wrong_spawn_count_fails_b3():
    g = _valid_graph()
    for i in range(13):  # needs 14
        g.add_node(f"sp{i}", 100 + i * 10, 100, SPAWN, team=i % 2)
    assert not g.validate().by_name("B3").passed


def test_correct_spawn_count_passes_b3():
    g = _valid_graph()
    for i in range(14):
        g.add_node(f"sp{i}", 100 + i * 10, 100, SPAWN, team=i % 2)
    assert g.validate().by_name("B3").passed


# -- RuleResult plumbing --------------------------------------------------


def test_rule_result_bool():
    assert RuleResult("X", True)
    assert not RuleResult("X", False)