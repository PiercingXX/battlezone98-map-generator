"""Tests for the Tier 1 terrain-name collision check (docs/07, ``formats.py``).

Generated terrain names are globally flat across all loaded mods (docs/07
"Terrain naming"): ``xx<nn><slug>`` must not collide with any terrain in the
installed game or workshop directories, or both maps break. The installed
reference data is not in the repo, so the check runs only when the caller
supplies ``reference_dir`` — mirroring the round-trip gate's skip-when-absent
behaviour (docs/06 §Tier 1).

The check is exercised with a synthetic reference directory of ``.trn`` files:

- a collision (same terrain name, including case-insensitively) is reported;
- a distinct name passes;
- the check is skipped when ``reference_dir`` is not supplied.
"""

from pathlib import Path

import numpy as np

from bzmap.formats.bzn import BznFile, GameObject
from bzmap.formats.des import write_des
from bzmap.formats.hg2 import HeightMap, write_hg2
from bzmap.formats.lgt import LightMap
from bzmap.formats.mat import MaterialGrid, write_mat
from bzmap.validate.formats import MapValidator, validate_map

# Flat terrain height (raw) used by the synthetic maps -> 100.0 m.
_RAW_H = 1000
_H_M = _RAW_H * 0.1

# Reference template paths (repo root / reference).
_REF = Path(__file__).resolve().parent.parent / "reference"


def _object(prjid, x, y, z, team=0, seqno=1, addr=1, label="obj"):
    """Clone the reference geyser block and mutate it into ``prjid``."""
    text = (_REF / "bzn-object-template.txt").read_text(encoding="utf-8")
    obj = GameObject.from_template(text)
    for i, line in enumerate(obj.lines):
        if line.strip().startswith("PrjID"):
            obj.lines[i + 1] = prjid
            break
    obj.set_position(x, y, z)
    obj.set_identity(seqno, addr, label)
    for i, line in enumerate(obj.lines):
        if line.strip() == "team [1] =":
            obj.lines[i + 1] = str(team)
            break
    return obj


def _bzn(objects, name):
    """Build a valid BZN file from a list of (prjid, x, y, z, team) tuples."""
    text = (_REF / "bzn-header-tail-template.txt").read_text(encoding="utf-8")
    _, _, header = text.partition("### HEADER")
    header, _, tail = header.partition("### TAIL")
    objs = []
    for i, (prjid, x, y, z, team) in enumerate(objects, start=1):
        objs.append(_object(prjid, x, y, z, team=team, seqno=i, addr=i,
                            label=f"{prjid}{i - 1}_x"))
    bzn = BznFile.build(header, objs, tail)
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

    hm = HeightMap(1, 1, np.full((256, 256), _RAW_H, dtype=np.uint16))
    write_hg2(d / "testmap.HG2", hm)
    write_mat(d / "testmap.MAT", MaterialGrid(np.zeros((64, 64), dtype=np.uint16)))
    LightMap(b"\x00" * ((1 * 1 + 1) * 65536), 1, 1).write(d / "testmap.lgt")
    _trn(d / "testmap.trn")

    base_objs = [("player", 640, _H_M, 640, 1)]
    base_objs += [("pspwn_1", 600 + i, _H_M, 600, 0) for i in range(14)]
    _bzn(base_objs, d / "testmap.bzn")

    s_objs = [("player", 640, _H_M, 640, 1)]
    s_objs += [("eggeizr1", 500 + i * 20, _H_M, 500, 0) for i in range(2)]
    s_objs += [("npscr1", 700 + i * 20, _H_M, 700, 0) for i in range(3)]
    _bzn(s_objs, d / "testmap_S.bzn")

    write_des(
        d / "testmap.des",
        mission_name="Test Map",
        world="Elysium",
        size="Small",
        geysers=2,
        scrap=3,
        players=2,
    )
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


def _reference_dir(tmp_path, *terrain_names):
    """A synthetic installed reference directory holding ``.trn`` files."""
    ref = tmp_path / "reference"
    ref.mkdir()
    for name in terrain_names:
        _trn(ref / f"{name}.trn")
    return ref


# -- collision check ----------------------------------------------------------


def test_no_collision_passes(tmp_path):
    d = _make_map(tmp_path)
    ref = _reference_dir(tmp_path, "xx02cany", "xx03basn")
    assert validate_map(d, reference_dir=ref) == []


def test_collision_is_reported(tmp_path):
    d = _make_map(tmp_path)
    ref = _reference_dir(tmp_path, "testmap")
    problems = validate_map(d, reference_dir=ref)
    assert any("collides with an installed terrain" in pr for pr in problems)


def test_collision_is_case_insensitive(tmp_path):
    d = _make_map(tmp_path)
    # The installed name differs only in case; the engine resolves terrain
    # names case-insensitively, so this is still a collision.
    ref = _reference_dir(tmp_path, "TESTMAP")
    problems = validate_map(d, reference_dir=ref)
    assert any("collides with an installed terrain" in pr for pr in problems)


def test_skipped_when_reference_dir_absent(tmp_path):
    d = _make_map(tmp_path)
    # Without a reference directory the check is skipped, exactly as the
    # round-trip gate skips when the pack is absent.
    assert validate_map(d) == []


def test_collision_reported_by_class_matches_function(tmp_path):
    d = _make_map(tmp_path)
    ref = _reference_dir(tmp_path, "testmap")
    assert MapValidator(d, reference_dir=ref).validate() == validate_map(
        d, reference_dir=ref
    )