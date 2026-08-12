"""Ten-map generation test (docs/08 Phase 6, GOAL-10maps).

Generates 10 two-team maps of varied character and size across the corpus
envelope (open / canyon / mid; sizes 1280 / 2560 / 5120), asserts each passes
the Tier 2 connectivity and balance validators (no error-severity problems,
docs/06), writes the full validated map file set under ``build/<name>/`` via
:func:`bzmap.package.build_map.build_map`.

Character is realised by varying the terrain synthesis parameters in
:class:`~bzmap.generate.terrain_gen.TerrainGenerator`:

- **open** — shallow carve, wide corridors, gentle ramps (low slope, open).
- **mid** — the default carve (docs/05).
- **canyon** — deep carve, narrow corridors (walls dominant).

Economy density follows the inverse-size rule automatically: ``build_layout``
places a fixed economy per base regardless of size, so smaller maps are denser
(1280 m ≈ 3.7 geysers/km² vs 5120 m ≈ 0.23 geysers/km²).
"""

from pathlib import Path

import numpy as np

from bzmap import cli
from bzmap.generate.spawns import generate_spawns
from bzmap.generate.terrain_gen import TerrainGenerator
from bzmap.package.build_map import build_map
from bzmap.validate.balance import validate_balance
from bzmap.validate.connectivity import ERROR as CONN_ERROR
from bzmap.validate.connectivity import validate_connectivity

#: Character → TerrainGenerator tuning (open / mid / canyon).
CHARACTER = {
    "open": {"carve_depth_raw": 200, "corridor_half_width_m": 110, "carve_ramp_m": 90},
    "mid": {"carve_depth_raw": 300, "corridor_half_width_m": 90, "carve_ramp_m": 75},
    "canyon": {"carve_depth_raw": 400, "corridor_half_width_m": 70, "carve_ramp_m": 60},
}

#: The ten maps: (name, size_m, character, seed, one-sentence design note).
MAPS = [
    ("xx01open", 1280, "open", 1, "Small open arena; shallow carve keeps the whole map drivable."),
    ("xx02mid", 1280, "mid", 7, "Small mid map; ring corridors with a flat central plateau."),
    ("xx03cany", 2560, "canyon", 13, "Medium canyon; deep narrow corridors wall off approach lanes."),
    ("xx04open", 2560, "open", 21, "Medium open map; wide gentle ramps between base camps."),
    ("xx05mid", 2560, "mid", 34, "Medium mid map; balanced carve for mixed terrain play."),
    ("xx06cany", 5120, "canyon", 55, "Large canyon; long walled corridors dominate the flanks."),
    ("xx07open", 5120, "open", 89, "Large open map; low-slope plateau with wide drive lanes."),
    ("xx08mid", 5120, "mid", 144, "Large mid map; a few deep canyons amid open ground."),
    ("xx09cany", 1280, "canyon", 13, "Small canyon; tight walled corridors around a central basin."),
    ("xx10open", 2560, "open", 377, "Medium open map; gentle terrain favours vehicle mobility."),
]


def _stock_bzn(tmp_path):
    """A minimal stock .bzn carrying every class the variants emit."""
    header = (
        "version [1] =\r\n2016\r\nbinarySave [1] =\r\nfalse\r\n"
        "msn_filename = stock.bzn\r\nseq_count [1] =\r\n1\r\n"
        "missionSave [1] =\r\ntrue\r\nTerrainName = stock\r\n"
        "size [1] =\r\n1\r\n"
    )
    tail = "[AiMission]\r\n[AOIs]\r\nsize [1] =\r\n0\r\n" \
        "[AiPaths]\r\ncount [1] =\r\n0\r\n"
    classes = ("player", "pspwn_1", "npscr1", "npscr2", "npscr3", "abhang", "absupp")
    parts = [header]
    for i, prjid in enumerate(classes):
        parts.append(
            "[GameObject]\r\nPrjID [1] =\r\n" + prjid + "\r\nseqno [1] =\r\n"
            + str(i) + "\r\npos [1] =\r\n  x [1] =\r\n10\r\n  y [1] =\r\n20\r\n"
            "  z [1] =\r\n30\r\nteam [1] =\r\n1\r\nlabel = stockobj\r\n"
            "isUser [1] =\r\n0\r\nobj_addr = 00000001\r\ntransform [1] =\r\n"
            "  right_x [1] =\r\n1\r\n  right_y [1] =\r\n0\r\n  right_z [1] =\r\n0\r\n"
            "  up_x [1] =\r\n0\r\n  up_y [1] =\r\n1\r\n  up_z [1] =\r\n0\r\n"
            "  front_x [1] =\r\n0\r\n  front_y [1] =\r\n0\r\n  front_z [1] =\r\n1\r\n"
            "  posit_x [1] =\r\n10\r\n  posit_y [1] =\r\n20\r\n  posit_z [1] =\r\n30\r\n"
            "illumination [1] =\r\n0\r\npos [1] =\r\n  x [1] =\r\n10\r\n"
            "  y [1] =\r\n20\r\n  z [1] =\r\n30\r\neuler =\r\n mass [1] =\r\n0\r\n"
            " mass_inv [1] =\r\n1e+030\r\n v_mag [1] =\r\n0\r\n"
            " v_mag_inv [1] =\r\n1e+030\r\n I [1] =\r\n1\r\n k_i [1] =\r\n0\r\n"
            " v [1] =\r\n  x [1] =\r\n0\r\n  y [1] =\r\n0\r\n  z [1] =\r\n0\r\n"
            " omega [1] =\r\n  x [1] =\r\n0\r\n  y [1] =\r\n0\r\n  z [1] =\r\n0\r\n"
            " Accel [1] =\r\n  x [1] =\r\n0\r\n  y [1] =\r\n0\r\n  z [1] =\r\n0\r\n"
            "seqNo [1] =\r\n" + str(i) + "\r\nname = \r\nisCritical [1] =\r\nfalse\r\n"
            "isObjective [1] =\r\nfalse\r\nisSelected [1] =\r\nfalse\r\n"
            "isVisible [1] =\r\n0\r\nseen [1] =\r\n0\r\nhealthRatio [1] =\r\n1\r\n"
            "curHealth [1] =\r\n0\r\nmaxHealth [1] =\r\n0\r\nammoRatio [1] =\r\n0\r\n"
            "curAmmo [1] =\r\n0\r\nmaxAmmo [1] =\r\n0\r\npriority [1] =\r\n0\r\n"
            "what = 00000000\r\nwho [1] =\r\n0\r\nwhere = 00000000\r\n"
            "param [1] =\r\n\r\naiProcess [1] =\r\nfalse\r\nisCargo [1] =\r\nfalse\r\n"
            "independence [1] =\r\n1\r\ncurPilot [1] =\r\n\r\n"
            "perceivedTeam [1] =\r\n0\r\n"
        )
    parts.append(tail)
    path = tmp_path / "stock.bzn"
    path.write_bytes("".join(parts).encode("utf-8"))
    return path


def _source_dir(tmp_path, name, size):
    """A stock source dir with the copy-only trn/LGT/vxt files for ``size``."""
    src = tmp_path / "stockmap"
    src.mkdir(exist_ok=True)
    zones = max(1, round(size / 1280.0))
    (src / f"{name}.trn").write_text(
        f"[Size]\r\nWidth = {size}\r\nDepth = {size}\r\n", encoding="utf-8"
    )
    (src / f"{name}.LGT").write_bytes(b"\x00" * ((zones * zones + 1) * 65536))
    (src / f"{name}.vxt").write_text(
        "avobserv avobserv.des\tx\tNSDF\r\n\r\n", encoding="utf-8"
    )
    return src


def _run_map(spec):
    """Generate + validate one map; return (layout, heightmap, balance_metrics)."""
    name, size, character, seed, _note = spec
    layout = cli.build_layout(size, size, 2, seed)
    heightmap = TerrainGenerator(**CHARACTER[character]).generate(layout)

    conn = validate_connectivity(heightmap, layout)
    errors = [p for p in conn if p.startswith(CONN_ERROR)]
    assert not errors, f"{name}: connectivity errors: {errors}"

    spawns = generate_spawns(layout, heightmap, mode="sw", seed=seed)
    bal = validate_balance(heightmap, layout, spawns.objects)
    errors = [p for p in bal if p.startswith("[error]")]
    assert not errors, f"{name}: balance errors: {errors}"

    return layout, heightmap


def test_ten_maps_generate_and_validate(tmp_path):
    """All 10 maps pass Tier 2 connectivity + balance (no errors)."""
    for spec in MAPS:
        _run_map(spec)


def test_ten_maps_write_validated_file_sets(tmp_path):
    """The 10 configs each write a full validated file set — into tmp_path.

    HYGIENE (learned the hard way): this test previously wrote into the repo's
    ``build/`` dir, silently REGENERATING map dirs the operator had deleted —
    a full-suite run resurrected nine culled maps and looked like a mystery
    restore. Tests never write outside tmp_path (AGENTS.md rule 2 spirit).
    Display names are required now: build_map rejects slug missionNames.
    """
    stock = _stock_bzn(tmp_path)
    for spec in MAPS:
        name, size, _c, _s, _n = spec
        src = _source_dir(tmp_path, name, size)
        map_dir = build_map(
            cli.generate_map(spec[3], spec[1], spec[1], 2),
            name, tmp_path / "build", bzn_path=stock, source_dir=src,
            mission_name=f"Pack Test {name[2:]}",
        )
        assert map_dir.is_dir()


def test_ten_maps_have_varied_character_and_size():
    """The set spans all three characters and all three corpus sizes."""
    chars = {m[2] for m in MAPS}
    sizes = {m[1] for m in MAPS}
    assert chars == {"open", "mid", "canyon"}
    assert sizes == {1280, 2560, 5120}


def test_ten_maps_balance_is_measurably_symmetric():
    """Per-base economy is equal within tolerance for every map (E4)."""
    from bzmap.validate.balance import BalanceValidator

    for spec in MAPS:
        name, size, character, seed, _n = spec
        layout = cli.build_layout(size, size, 2, seed)
        heightmap = TerrainGenerator(**CHARACTER[character]).generate(layout)
        spawns = generate_spawns(layout, heightmap, mode="sw", seed=seed)
        m = BalanceValidator(heightmap, layout, spawns.objects).measure()
        totals = list(m["per_base_economy"].values())
        assert len(totals) == 2, f"{name}: expected 2 bases"
        assert abs(totals[0] - totals[1]) <= 1, f"{name}: unbalanced {totals}"


def test_ten_maps_are_deterministic():
    """The same spec always yields the same heightmap."""
    for spec in MAPS:
        name, size, character, seed, _n = spec
        layout = cli.build_layout(size, size, 2, seed)
        a = TerrainGenerator(**CHARACTER[character]).generate(layout)
        b = TerrainGenerator(**CHARACTER[character]).generate(layout)
        assert np.array_equal(a.data, b.data), f"{name}: not deterministic"