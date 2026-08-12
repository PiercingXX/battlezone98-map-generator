"""Tests for Tier 1 structural validation (docs/06, ``validate/formats.py``).

Builds synthetic candidate map directories with the real format writers and
asserts that a structurally valid map passes with no problems, and that each
Tier 1 check catches its specific violation:

- round-trip (BZN / HG2)
- per-map invariants (trn size vs HG2, BZN size/seq_count/obj_addr/player/tail)
- cross-file consistency (terrain files exist, des counts, ini maxPlayers)
- ground snapping within 1.5 m
- ``msn_filename``/``TerrainName`` are **never** validated
"""

from pathlib import Path

import numpy as np

from bzmap.formats.bzn import BznFile, GameObject
from bzmap.formats.des import write_des
from bzmap.formats.hg2 import HeightMap, write_hg2
from bzmap.formats.lgt import LightMap
from bzmap.formats.mat import MaterialGrid, write_mat
from bzmap.validate.formats import (
    GROUND_SNAP_TOLERANCE_M,
    MapValidator,
    validate_map,
)

# Flat terrain height (raw) used by the synthetic maps -> 100.0 m.
_RAW_H = 1000
_H_M = _RAW_H * 0.1

# Reference template paths (repo root / reference).
_REF = Path(__file__).resolve().parent.parent / "reference"


def _object(prjid, x, y, z, team=0, seqno=1, addr=1, label="obj"):
    """Clone the reference geyser block and mutate it into ``prjid``."""
    text = (_REF / "bzn-object-template.txt").read_text(encoding="utf-8")
    obj = GameObject.from_template(text)
    # Rewrite the PrjID value line (first field, value on the next line).
    for i, line in enumerate(obj.lines):
        if line.strip().startswith("PrjID"):
            obj.lines[i + 1] = prjid
            break
    obj.set_position(x, y, z)
    obj.set_identity(seqno, addr, label)
    # team [1] = value on next line.
    for i, line in enumerate(obj.lines):
        if line.strip() == "team [1] =":
            obj.lines[i + 1] = str(team)
            break
    return obj


def _bzn(objects, name):
    """Build a valid BZN file from a list of (prjid, x, y, z, team) tuples."""
    text = (_REF / "bzn-header-tail-template.txt").read_text(encoding="utf-8")
    # Split the reference file into header and tail blocks at the markers.
    _, _, header = text.partition("### HEADER")
    header, _, tail = header.partition("### TAIL")
    objs = []
    for i, (prjid, x, y, z, team) in enumerate(objects, start=1):
        objs.append(_object(prjid, x, y, z, team=team, seqno=i, addr=i,
                            label=f"{prjid}{i - 1}_x"))
    bzn = BznFile.build(header, objs, tail)
    # size == object count; seq_count == max(seqno)+1.
    bzn.set_header("size [1]", str(len(objs)))
    bzn.set_header("seq_count [1]", str(len(objs) + 1))
    bzn.write(name)
    return name


def _trn(path, width=1280.0, depth=1280.0):
    """Write a minimal ``.trn`` with a matching ``[Size]`` section."""
    text = (
        "[Size]\r\n"
        f"MinX = 0\r\nMinZ = 0\r\nWidth = {width}\r\nDepth = {depth}\r\n"
        "Height = 100\r\n"
    )
    path.write_text(text, encoding="utf-8", newline="")


def _make_map(tmp_path, name="testmap"):
    """Build a structurally valid candidate map directory; return its path."""
    d = tmp_path / name
    d.mkdir()

    # Flat 1x1-zone (1280 m) heightmap at 100 m.
    hm = HeightMap(1, 1, np.full((256, 256), _RAW_H, dtype=np.uint16))
    write_hg2(d / "testmap.HG2", hm)

    # Material grid of the right size (64x64 tiles).
    write_mat(d / "testmap.MAT", MaterialGrid(np.zeros((64, 64), dtype=np.uint16)))

    # Lightmap (copy-only) of the right size.
    LightMap(b"\x00" * ((1 * 1 + 1) * 65536), 1, 1).write(d / "testmap.lgt")

    # Terrain config.
    _trn(d / "testmap.trn")

    # Base (deathmatch): player + 14 spawns.
    base_objs = [("player", 640, _H_M, 640, 1)]
    base_objs += [("pspwn_1", 600 + i, _H_M, 600, 0) for i in range(14)]
    _bzn(base_objs, d / "testmap.bzn")

    # _S (strategy): player + 2 geysers + 3 scrap.
    s_objs = [("player", 640, _H_M, 640, 1)]
    s_objs += [("eggeizr1", 500 + i * 20, _H_M, 500, 0) for i in range(2)]
    s_objs += [("npscr1", 700 + i * 20, _H_M, 700, 0) for i in range(3)]
    _bzn(s_objs, d / "testmap_S.bzn")

    # Description matching the _S counts (2 geysers, 3 scrap).
    write_des(
        d / "testmap.des",
        mission_name="Test Map",
        world="Elysium",
        size="Small",
        geysers=2,
        scrap=3,
        players=2,
    )

    # Workshop/multiplayer metadata consistent with 14 deathmatch spawns.
    (d / "testmap.ini").write_text(
        "[DESCRIPTION]\r\n"
        'missionName = "Test Map"\r\n'
        "\r\n"
        "[MULTIPLAYER]\r\n"
        'minPlayers = "1"\r\n'
        'maxPlayers = "14"\r\n'
        'gameType = "K"\r\n',
        encoding="utf-8",
        newline="",
    )
    return d


# -- valid map ----------------------------------------------------------------


def test_valid_map_has_no_problems(tmp_path):
    d = _make_map(tmp_path)
    assert validate_map(d) == []


def test_validator_class_matches_function(tmp_path):
    d = _make_map(tmp_path)
    assert MapValidator(d).validate() == validate_map(d)


# -- round-trip ---------------------------------------------------------------


def test_corrupted_bzn_fails_roundtrip(tmp_path):
    d = _make_map(tmp_path)
    p = d / "testmap.bzn"
    data = bytearray(p.read_bytes())
    data[0] ^= 0xFF  # corrupt the first byte
    p.write_bytes(bytes(data))
    problems = validate_map(d)
    assert any("BZN" in pr and "round-trip" in pr for pr in problems)


def test_corrupted_hg2_fails_roundtrip(tmp_path):
    d = _make_map(tmp_path)
    p = d / "testmap.HG2"
    data = bytearray(p.read_bytes())
    # Corrupt the header's zonesX field (offset 4-5) so the expected sample
    # count no longer matches the file size and read_hg2 raises.
    data[4:6] = (255).to_bytes(2, "little")
    p.write_bytes(bytes(data))
    problems = validate_map(d)
    assert any("HG2" in pr and "round-trip" in pr for pr in problems)


# -- per-map invariants -------------------------------------------------------


def test_trn_size_mismatch_is_reported(tmp_path):
    d = _make_map(tmp_path)
    _trn(d / "testmap.trn", width=2560.0, depth=1280.0)  # wrong: HG2 is 1280
    problems = validate_map(d)
    assert any("does not match HG2 header" in pr for pr in problems)


def test_bzn_size_field_mismatch_is_reported(tmp_path):
    d = _make_map(tmp_path)
    p = d / "testmap.bzn"
    bzn = BznFile.read(p)
    bzn.set_header("size [1]", "999")  # wrong object count
    bzn.write(p)
    problems = validate_map(d)
    assert any("size 999 != object count" in pr for pr in problems)


def test_missing_player_is_reported(tmp_path):
    d = _make_map(tmp_path)
    p = d / "testmap.bzn"
    bzn = BznFile.read(p)
    # Drop every player object.
    bzn.objects = [o for o in bzn.objects if o.prjid != "player"]
    bzn.set_header("size [1]", str(len(bzn.objects)))
    bzn.write(p)
    problems = validate_map(d)
    assert any("player" in pr for pr in problems)


def test_noncontiguous_obj_addr_is_reported(tmp_path):
    d = _make_map(tmp_path)
    p = d / "testmap_S.bzn"
    bzn = BznFile.read(p)
    # Duplicate an obj_addr so the sequence is no longer contiguous from 1.
    bzn.objects[1].set_identity(2, 1, "dup")
    bzn.write(p)
    problems = validate_map(d)
    assert any("obj_addr" in pr for pr in problems)


# -- cross-file consistency ---------------------------------------------------


def test_missing_terrain_file_is_reported(tmp_path):
    d = _make_map(tmp_path)
    (d / "testmap.MAT").unlink()
    problems = validate_map(d)
    assert any("terrain file" in pr and ".mat" in pr.lower() for pr in problems)


def test_des_count_mismatch_is_reported(tmp_path):
    d = _make_map(tmp_path)
    write_des(
        d / "testmap.des",
        mission_name="Test Map",
        world="Elysium",
        size="Small",
        geysers=99,  # wrong: _S has 2
        scrap=3,
        players=2,
    )
    problems = validate_map(d)
    assert any("GEYSERS" in pr for pr in problems)


def test_ini_max_players_too_low_is_reported(tmp_path):
    d = _make_map(tmp_path)
    (d / "testmap.ini").write_text(
        "[MULTIPLAYER]\r\n"
        'maxPlayers = "2"\r\n',  # wrong: base has 14 deathmatch spawns
        encoding="utf-8",
        newline="",
    )
    problems = validate_map(d)
    assert any("maxPlayers" in pr for pr in problems)


# -- ground snapping ----------------------------------------------------------


def test_object_not_ground_snapped_is_reported(tmp_path):
    d = _make_map(tmp_path)
    p = d / "testmap_S.bzn"
    bzn = BznFile.read(p)
    # Lift the first geyser 20 m off the 100 m terrain.
    for o in bzn.objects:
        if o.prjid == "eggeizr1":
            # set_position updates all three position copies.
            o.set_position(500, _H_M + 20.0, 500)
            break
    bzn.write(p)
    problems = validate_map(d)
    assert any("m from terrain height" in pr for pr in problems)


def test_ground_snap_tolerance_is_1_5m():
    assert GROUND_SNAP_TOLERANCE_M == 1.5


# -- msn_filename / TerrainName are NOT validated ------------------------------


def test_vestigial_name_fields_are_not_validated(tmp_path):
    d = _make_map(tmp_path)
    # Rewrite msn_filename / TerrainName to disagree with the actual filename.
    p = d / "testmap_S.bzn"
    bzn = BznFile.read(p)
    bzn.set_header("msn_filename", "completely_wrong.bzn")
    bzn.set_header("TerrainName", "SBPUI")
    bzn.write(p)
    # The map must still pass: these fields are vestigial (docs/02 §2).
    assert validate_map(d) == []