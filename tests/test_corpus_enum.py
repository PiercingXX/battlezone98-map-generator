"""Corpus enumeration tests.

The ``bzmap corpus`` subcommand reads a snapshot of a map corpus (a flat
directory of map files sharing basenames) and reproduces
a corpus-stats CSV. These tests build a small fixture snapshot and
verify the enumeration produces the expected rows — size, variants and object
counts — matching the Phase 0 gate in docs/08.
"""

import csv

import pytest

from bzmap import cli

# --- fixture builders ---------------------------------------------------------


def _game_object_block(prj_id, label):
    """A minimal but structurally valid ``[GameObject]`` block.

    Only the fields the enumerator reads (``PrjID``) plus ``label`` for realism
    are emitted; the enumerator counts objects purely by ``PrjID`` class.
    """
    return (
        "[GameObject]\n"
        f"PrjID [1] =\n{prj_id}\n"
        f"label = {label}\n"
        "seqno [1] =\n1\n"
        "obj_addr = 00000001\n"
        "name = \n"
    )


def _write_bzn(path, objects):
    """Write an ASCII .bzn with the given list of (prj_id, label) pairs."""
    body = "".join(_game_object_block(pid, lbl) for pid, lbl in objects)
    path.write_text(
        "version [1] =\n2016\n"
        "binarySave [1] =\nfalse\n"
        "msn_filename = test.bzn\n"
        "seq_count [1] =\n1\n"
        "missionSave [1] =\ntrue\n"
        "TerrainName = test\n"
        "size [1] =\n1\n" + body +
        "[AiMission]\n[AOIs]\nsize [1] =\n0\n[AiPaths]\ncount [1] =\n0\n"
    )


def _write_trn(path, width, depth, atlas, sky):
    path.write_text(
        "[Size]\n"
        f"Width = {width}\n"
        f"Depth = {depth}\n"
        "[Atlases]\n"
        f"MaterialName = {atlas}\n"
        "[Sky]\n"
        f"BackdropTexture = {sky}\n"
    )


def _write_ini(path, mission_name, max_players, game_type):
    path.write_text(
        "[DESCRIPTION]\n"
        f"missionName = \"{mission_name}\"\n"
        "[MULTIPLAYER]\n"
        f"maxPlayers = \"{max_players}\"\n"
        f"gameType = \"{game_type}\"\n"
    )


@pytest.fixture
def snapshot(tmp_path):
    """A small corpus snapshot with two terrains, one carrying variants."""
    # alpha: 2560x2560, all three variants, geysers+scrap+dm spawns.
    _write_trn(tmp_path / "alpha.trn", 2560, 2560, "el_detail_atlas", "mars.map")
    _write_ini(
        tmp_path / "alpha.ini", "Corpus Alpha", "14", "K"
    )
    _write_bzn(
        tmp_path / "alpha.bzn",
        [("eggeizr1", "eggeizr10_geyser")] * 16
        + [("npscr1", "npscr10_scrap")] * 200
        + [("pspwn_1", "pspwn_10_spawnpnt")] * 14,
    )
    # _S: full economy + player-count spawns; _SW: 14 spawns.
    _write_bzn(tmp_path / "alpha_S.bzn", [("pspwn_1", "pspwn_10_spawnpnt")] * 4)
    _write_bzn(tmp_path / "alpha_SW.bzn", [("pspwn_1", "pspwn_10_spawnpnt")] * 14)

    # beta: 5120x3840, no variants, fewer geysers.
    _write_trn(tmp_path / "beta.trn", 5120, 3840, "ma_detail_atlas", "venus.map")
    _write_ini(tmp_path / "beta.ini", "Corpus Beta", "15", "K")
    _write_bzn(
        tmp_path / "beta.bzn",
        [("eggeizr1", "eggeizr10_geyser")] * 6
        + [("npscr2", "npscr20_scrap")] * 90
        + [("pspwn_1", "pspwn_10_spawnpnt")] * 14,
    )
    return tmp_path


# --- tests --------------------------------------------------------------------


def test_parse_ini_handles_quotes_and_comments(tmp_path):
    ini = tmp_path / "x.ini"
    ini.write_text(
        "[DESCRIPTION]\n"
        "; a comment\n"
        "missionName = \"Silver Pools\"\n"
        "[MULTIPLAYER]\n"
        "maxPlayers = \"14\"\n"
        "gameType = \"K\"\n"
    )
    cfg = cli.parse_ini(ini)
    assert cfg["DESCRIPTION"]["missionName"] == "Silver Pools"
    assert cfg["MULTIPLAYER"]["maxPlayers"] == "14"
    assert cfg["MULTIPLAYER"]["gameType"] == "K"


def test_count_bzn_objects_by_class(tmp_path):
    bzn = tmp_path / "m.bzn"
    _write_bzn(
        bzn,
        [("eggeizr1", "g"), ("npscr1", "s1"), ("npscr3", "s3"),
         ("pspwn_1", "p"), ("player", "player0_wingman")],
    )
    assert cli.count_bzn_objects(bzn) == (1, 2, 1)


def test_enumerate_terrain_full_row(snapshot):
    row = cli.enumerate_terrain(snapshot, "alpha")
    assert row["terrain"] == "alpha"
    assert row["mission_name"] == "Corpus Alpha"
    assert row["width_m"] == "2560"
    assert row["depth_m"] == "2560"
    assert row["atlas"] == "el_detail_atlas"
    assert row["sky"] == "mars.map"
    assert row["max_players"] == "14"
    assert row["game_type"] == "K"
    assert row["geysers"] == 16
    assert row["scrap"] == 200
    assert row["spawns_dm"] == 14
    assert row["spawns_S"] == 4
    assert row["spawns_SW"] == 14
    assert row["has_S"] is True
    assert row["has_ST"] is False
    assert row["has_SW"] is True
    assert row["area_km2"] == "6.554"
    assert row["geysers_per_km2"] == "2.441"


def test_enumerate_corpus_reproduces_snapshot(snapshot):
    rows = {r["terrain"]: r for r in cli.enumerate_corpus(snapshot)}
    assert set(rows) == {"alpha", "beta"}

    beta = rows["beta"]
    assert beta["width_m"] == "5120"
    assert beta["depth_m"] == "3840"
    assert beta["area_km2"] == "19.661"
    assert beta["geysers_per_km2"] == "0.305"
    assert beta["has_S"] is False
    assert beta["has_ST"] is False
    assert beta["has_SW"] is False


def test_write_corpus_csv_roundtrips(snapshot, tmp_path):
    rows = cli.enumerate_corpus(snapshot)
    out = tmp_path / "out.csv"
    cli.write_corpus_csv(rows, out)

    with open(out, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        written = list(reader)

    assert reader.fieldnames == cli.CSV_FIELDS
    assert len(written) == 2
    by_name = {r["terrain"]: r for r in written}
    assert by_name["alpha"]["geysers"] == "16"
    assert by_name["alpha"]["spawns_SW"] == "14"
    assert by_name["alpha"]["has_SW"] == "True"
    assert by_name["beta"]["geysers_per_km2"] == "0.305"


def test_cli_corpus_command(snapshot, tmp_path, capsys):
    out = tmp_path / "cli.csv"
    rc = cli.main(["corpus", str(snapshot), "-o", str(out)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "2 rows" in captured.out
    assert out.exists()


def test_cli_corpus_missing_snapshot(capsys):
    rc = cli.main(["corpus", "/nonexistent/definitely-missing"])
    assert rc == 1
    assert "not found" in capsys.readouterr().err