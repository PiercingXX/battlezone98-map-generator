"""Tests for :mod:`bzmap.package.build_map` (docs/07).

The contract under test: a :class:`bzmap.cli.GenerateResult` (from
``generate_map``) is turned into the full validated map file set in
``out_dir/<name>/`` — terrain files, the four variant BZNs, and the metadata
files — and the set passes Tier 1 structural validation (docs/06).
"""

import pytest

from bzmap import cli
from bzmap.formats.bzn import BznFile
from bzmap.package.build_map import BuildError, build_map
from bzmap.validate.formats import MapValidator

# Object classes the variants emit that reference/ does not carry (docs/02 §6 R2).
# Scrap is emitted as npscr1/2/3 (bzmap/generate/variants.py SCRAP_CLASSES), so the
# stock source must carry all three or the template-and-mutate clone raises KeyError.
_STOCK_CLASSES = ("player", "pspwn_1", "npscr1", "npscr2", "npscr3", "abhang", "absupp")


def _write_stock_bzn(tmp_path, prjids=_STOCK_CLASSES):
    """Write a minimal stock-like .bzn carrying one object per ``prjid``."""
    header = (
        "version [1] =\r\n2016\r\nbinarySave [1] =\r\nfalse\r\n"
        "msn_filename = stock.bzn\r\nseq_count [1] =\r\n1\r\n"
        "missionSave [1] =\r\ntrue\r\nTerrainName = stock\r\n"
        "size [1] =\r\n1\r\n"
    )
    tail = (
        "[AiMission]\r\n[AOIs]\r\nsize [1] =\r\n0\r\n"
        "[AiPaths]\r\ncount [1] =\r\n0\r\n"
    )
    parts = [header]
    for i, prjid in enumerate(prjids):
        parts.append(
            "[GameObject]\r\n"
            "PrjID [1] =\r\n"
            f"{prjid}\r\n"
            "seqno [1] =\r\n"
            f"{i}\r\n"
            "pos [1] =\r\n"
            "  x [1] =\r\n10\r\n  y [1] =\r\n20\r\n  z [1] =\r\n30\r\n"
            "team [1] =\r\n1\r\n"
            "label = stockobj\r\n"
            "isUser [1] =\r\n0\r\n"
            "obj_addr = 00000001\r\n"
            "transform [1] =\r\n"
            "  right_x [1] =\r\n1\r\n  right_y [1] =\r\n0\r\n  right_z [1] =\r\n0\r\n"
            "  up_x [1] =\r\n0\r\n  up_y [1] =\r\n1\r\n  up_z [1] =\r\n0\r\n"
            "  front_x [1] =\r\n0\r\n  front_y [1] =\r\n0\r\n  front_z [1] =\r\n1\r\n"
            "  posit_x [1] =\r\n10\r\n  posit_y [1] =\r\n20\r\n  posit_z [1] =\r\n30\r\n"
            "illumination [1] =\r\n0\r\n"
            "pos [1] =\r\n"
            "  x [1] =\r\n10\r\n  y [1] =\r\n20\r\n  z [1] =\r\n30\r\n"
            "euler =\r\n mass [1] =\r\n0\r\n mass_inv [1] =\r\n1e+030\r\n"
            " v_mag [1] =\r\n0\r\n v_mag_inv [1] =\r\n1e+030\r\n"
            " I [1] =\r\n1\r\n k_i [1] =\r\n0\r\n"
            " v [1] =\r\n  x [1] =\r\n0\r\n  y [1] =\r\n0\r\n  z [1] =\r\n0\r\n"
            " omega [1] =\r\n  x [1] =\r\n0\r\n  y [1] =\r\n0\r\n  z [1] =\r\n0\r\n"
            " Accel [1] =\r\n  x [1] =\r\n0\r\n  y [1] =\r\n0\r\n  z [1] =\r\n0\r\n"
            "seqNo [1] =\r\n"
            f"{i}\r\n"
            "name = \r\nisCritical [1] =\r\nfalse\r\n"
            "isObjective [1] =\r\nfalse\r\nisSelected [1] =\r\nfalse\r\n"
            "isVisible [1] =\r\n0\r\nseen [1] =\r\n0\r\n"
            "healthRatio [1] =\r\n1\r\ncurHealth [1] =\r\n0\r\nmaxHealth [1] =\r\n0\r\n"
            "ammoRatio [1] =\r\n0\r\ncurAmmo [1] =\r\n0\r\nmaxAmmo [1] =\r\n0\r\n"
            "priority [1] =\r\n0\r\nwhat = 00000000\r\nwho [1] =\r\n0\r\n"
            "where = 00000000\r\nparam [1] =\r\n\r\n"
            "aiProcess [1] =\r\nfalse\r\nisCargo [1] =\r\nfalse\r\n"
            "independence [1] =\r\n1\r\ncurPilot [1] =\r\n\r\n"
            "perceivedTeam [1] =\r\n0\r\n"
        )
    parts.append(tail)
    path = tmp_path / "stock.bzn"
    path.write_bytes("".join(parts).encode("utf-8"))
    return path


def _make_source_dir(tmp_path, name="xx01ridg"):
    """A stock map source dir with the copy-only trn/LGT/vxt files."""
    src = tmp_path / "stockmap"
    src.mkdir(exist_ok=True)
    # .trn with a [Size] matching the 2560 m generated map (zonesX=zonesZ=2).
    (src / f"{name}.trn").write_text(
        "[Size]\r\nWidth = 2560\r\nDepth = 2560\r\n", encoding="utf-8"
    )
    # .LGT must be exactly (zonesX*zonesZ + 1) * 65536 bytes for 2x2 zones.
    (src / f"{name}.LGT").write_bytes(b"\x00" * ((2 * 2 + 1) * 65536))
    (src / f"{name}.vxt").write_text(
        "avobserv avobserv.des\tx\tNSDF\r\n\r\n", encoding="utf-8"
    )
    return src


def test_build_map_writes_full_validated_file_set(tmp_path):
    result = cli.generate_map(seed=42)
    stock = _write_stock_bzn(tmp_path)
    src = _make_source_dir(tmp_path)
    map_dir = build_map(
        result, "xx01ridg", tmp_path / "build",
        bzn_path=stock, source_dir=src, mission_name="Ridge Run",
    )

    # The full flat file set for one map is present — including the per-map
    # thumbnails (the generator-fixes audit, task 5).
    names = sorted(p.name for p in map_dir.iterdir())
    expected = {
        "xx01ridg.HG2", "xx01ridg.MAT", "xx01ridg.trn", "xx01ridg.LGT",
        "xx01ridg.vxt", "xx01ridg.ini", "xx01ridg.des", "xx01ridg.odf",
        "xx01ridg.bzn", "xx01ridg_S.bzn", "xx01ridg_ST.bzn", "xx01ridg_SW.bzn",
        "xx01ridg.BMP", "xx01ridg.png",
    }
    assert set(names) == expected

    # The set passes Tier 1 structural validation (docs/06).
    assert MapValidator(map_dir).validate() == []


def test_build_map_bzns_roundtrip_and_validate(tmp_path):
    result = cli.generate_map(seed=7)
    stock = _write_stock_bzn(tmp_path)
    src = _make_source_dir(tmp_path)
    map_dir = build_map(
        result, "xx02cany", tmp_path / "build",
        bzn_path=stock, source_dir=src, mission_name="Canyon Run",
    )
    for fname in ("xx02cany.bzn", "xx02cany_S.bzn",
                  "xx02cany_ST.bzn", "xx02cany_SW.bzn"):
        bzn = BznFile.read(map_dir / fname)
        assert bzn.validate() == []
        # Round-trip: re-emit and compare bytes.
        out = map_dir / (fname + ".rt")
        bzn.write(out)
        assert out.read_bytes() == (map_dir / fname).read_bytes()


def test_build_map_des_counts_match_s_bzn(tmp_path):
    result = cli.generate_map(seed=42)
    stock = _write_stock_bzn(tmp_path)
    src = _make_source_dir(tmp_path)
    map_dir = build_map(
        result, "xx01ridg", tmp_path / "build",
        bzn_path=stock, source_dir=src, mission_name="Ridge Run",
    )
    des = (map_dir / "xx01ridg.des").read_text(encoding="utf-8")
    s_bzn = BznFile.read(map_dir / "xx01ridg_S.bzn")
    geysers = sum(1 for o in s_bzn.objects if o.prjid == "eggeizr1")
    scrap = sum(1 for o in s_bzn.objects if o.prjid and o.prjid.startswith("npscr"))
    assert f"GEYSERS: {geysers}" in des
    assert f"SCRAP: {scrap}" in des


def test_build_map_missing_stock_classes_raises(tmp_path):
    """Without a stock bzn_path the reference/ templates cannot clone all classes."""
    result = cli.generate_map(seed=42)
    src = _make_source_dir(tmp_path)
    with pytest.raises(KeyError):
        build_map(result, "xx01ridg", tmp_path / "build", source_dir=src,
                  mission_name="Ridge Run")

def test_build_map_without_source_dir_writes_complete_files(tmp_path):
    """The contract's core scenario: no stock source at all, and the writers
    still emit a COMPLETE .trn (sufficiency-clean), the five-observer .vxt and
    a structurally-valid .LGT — where the old behavior shipped [Size]-only
    stubs (generator-fixes audit)."""
    from bzmap.validate.terrain import check_trn_sufficiency, check_vxt_players

    result = cli.generate_map(seed=42)
    stock = _write_stock_bzn(tmp_path)

    map_dir = build_map(
        result, "xx01ridg", tmp_path / "build",
        bzn_path=stock, mission_name="Ridge Run",
    )

    assert check_trn_sufficiency(
        map_dir / "xx01ridg.trn", map_dir / "xx01ridg.MAT"
    ) == []
    assert check_vxt_players((map_dir / "xx01ridg.vxt").read_text()) == []
    lgt = (map_dir / "xx01ridg.LGT").stat().st_size
    hm_zones = 2 * 2  # 2560 m generated map
    assert lgt == (hm_zones + 1) * 65536
    assert MapValidator(map_dir).validate() == []


def test_build_map_rejects_slug_mission_name(tmp_path):
    """Players saw 'xx01open' in the lobby; the builder now refuses it."""
    result = cli.generate_map(seed=42)
    stock = _write_stock_bzn(tmp_path)

    with pytest.raises(BuildError, match="display name"):
        build_map(result, "xx01ridg", tmp_path / "build",
                  bzn_path=stock, mission_name="xx01ridg")
    with pytest.raises(BuildError, match="display name"):
        build_map(result, "xx01ridg", tmp_path / "build", bzn_path=stock)
