"""Tests for the per-candidate validation report (docs/06 §Reporting,
``validate/report.py``).

Verifies that ``report.json`` records **measured values, not just verdicts**
and that ``preview.png`` is written. Builds a small heightmap + layout directly
(no game pack needed), mirrors the other validator tests.

The passing fixture is a 1-zone (1280 m) ringed-flat heightmap with the balance
test's routed-economy graph and a ``generate_spawns`` _SW spawn set — the same
combination the connectivity and balance tests prove passes every C-/E-/B-rule,
plus the impassable boundary ring that satisfies T4. A plain flat map (no ring)
fails only T4, which lets us assert the report records a real validator error.
"""

import json

import numpy as np
from PIL import Image

from bzmap.formats.hg2 import ZONE_SIZE, HeightMap
from bzmap.generate.spawns import generate_spawns
from bzmap.model.layout import BASE, GEYSER, LayoutGraph
from bzmap.validate.report import CandidateReport, write_report


def _graph() -> LayoutGraph:
    """A 1280 m two-base ring with economy routed to its bases (docs/04 §2-§3).

    Six geysers: two per base plus two contested at the midpoint, so per-base
    economy is balanced (3/3) and the contested share is 2/6 = 33%. Mirrors the
    balance validator test fixture.
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
    for nid, x, z, base in (("g1", 430, 520, "A"), ("g2", 300, 700, "A"),
                            ("g3", 900, 500, "B"), ("g4", 1000, 700, "B")):
        g.add_node(nid, x, z, GEYSER)
        g.add_route(nid, base)
    g.add_node("g5", 639, 639, GEYSER)
    g.add_route("g5", "A")
    g.add_route("g5", "B")
    g.add_node("g6", 641, 641, GEYSER)
    g.add_route("g6", "A")
    g.add_route("g6", "B")
    return g


def _spawns(graph, hm):
    """The 14-spawn _SW set for ``graph`` on ``hm`` (valid B3 geometry)."""
    return generate_spawns(graph, hm, mode="sw").objects


def _flat_hm(raw=1000):
    """A perfectly flat 1-zone heightmap (fails only T4)."""
    return HeightMap(1, 1, np.full((ZONE_SIZE, ZONE_SIZE), raw, dtype=np.uint16))


def _ringed_flat_hm(raw=1000):
    """A flat map with a steep (impassable) boundary ring — passes every rule.

    The interior is flat at ``raw``; the outer boundary band ramps up by 60 raw
    per cell (1.2 m/m slope, well above 45°), so the edge is impassable without
    saturating the 12-bit range. Mirrors the terrain validator test fixture.
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


def _passing_report(**kwargs):
    """A CandidateReport whose heightmap+layout+spawns pass every rule."""
    hm = _ringed_flat_hm()
    g = _graph()
    return CandidateReport(hm, g, spawns=_spawns(g, hm), **kwargs)


# -- report dict -------------------------------------------------------------


def test_to_dict_records_measured_values_not_just_verdicts():
    report = _passing_report(seed="abc123")
    d = report.to_dict()
    # Measured values, not verdicts: flat_pct is a number, not "T1: pass".
    assert "measured" in d
    assert isinstance(d["measured"]["terrain"]["flat_pct"], float)
    assert isinstance(d["measured"]["connectivity"]["traversable_pct"], float)
    assert isinstance(d["measured"]["balance"]["e4_spread"], float)


def test_to_dict_records_seed_and_dimensions():
    hm = _flat_hm()
    report = CandidateReport(hm, _graph(), seed="seed-42")
    d = report.to_dict()
    assert d["seed"] == "seed-42"
    assert d["width_m"] == hm.width_m
    assert d["depth_m"] == hm.depth_m
    assert d["grid"] == [hm.grid_x, hm.grid_z]


def test_verdict_fail_when_structural_error():
    report = _passing_report(
        structural_problems=["[error] map.bzn: BZN round-trip failed"]
    )
    assert report.to_dict()["verdict"] == "fail"


def test_verdict_pass_with_no_errors():
    report = _passing_report()
    d = report.to_dict()
    assert d["verdict"] == "pass"
    assert d["problems"]["error"] == []


def test_problems_grouped_by_severity():
    # A plain flat map fails T4 (error); its modal height 1000 is in range so
    # T2 does not warn — use a low plateau to force a T2 warning too.
    hm = _flat_hm(raw=100)
    report = CandidateReport(hm, _graph())
    d = report.to_dict()
    assert any("T4" in p for p in d["problems"]["error"])
    assert any("T2" in p for p in d["problems"]["warning"])


# -- writing -----------------------------------------------------------------


def test_write_report_creates_json_and_png(tmp_path):
    hm = _ringed_flat_hm()
    g = _graph()
    out = tmp_path / "candidates" / "seed-1"
    json_path = write_report(
        out, hm, g, spawns=_spawns(g, hm), seed="seed-1"
    )
    assert json_path == out / "report.json"
    assert json_path.is_file()
    assert (out / "preview.png").is_file()

    with json_path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["seed"] == "seed-1"
    assert data["verdict"] == "pass"

    with Image.open(out / "preview.png") as im:
        assert im.format == "PNG"
        assert im.mode == "RGB"


def test_write_report_records_structural_problems(tmp_path):
    hm = _ringed_flat_hm()
    g = _graph()
    out = tmp_path / "cand"
    write_report(
        out,
        hm,
        g,
        spawns=_spawns(g, hm),
        structural_problems=["[error] map.bzn: size mismatch"],
        seed="s",
    )
    with (out / "report.json").open(encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["verdict"] == "fail"
    assert data["problems"]["error"][0] == "[error] map.bzn: size mismatch"


def test_report_is_deterministic(tmp_path):
    """Same inputs produce byte-identical JSON (fixed-seed determinism)."""
    hm = _ringed_flat_hm()
    g = _graph()
    a = tmp_path / "a"
    b = tmp_path / "b"
    write_report(a, hm, g, spawns=_spawns(g, hm), seed="fixed")
    write_report(b, hm, g, spawns=_spawns(g, hm), seed="fixed")
    assert (a / "report.json").read_bytes() == (b / "report.json").read_bytes()


def test_candidate_report_accepts_hg2_path(tmp_path):
    hm = _ringed_flat_hm()
    g = _graph()
    p = tmp_path / "map.HG2"
    hm.write(p)
    report = CandidateReport(p, g, spawns=_spawns(g, hm))
    assert report.to_dict()["verdict"] == "pass"


def test_report_with_spawns(tmp_path):
    """Spawns are passed through to the balance validator's B3 check."""
    hm = _ringed_flat_hm()
    g = _graph()
    report = CandidateReport(hm, g, spawns=_spawns(g, hm))
    assert report.to_dict()["measured"]["balance"]["spawn_count"] == 14