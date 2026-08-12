"""Tests for the metadata writers ``.des`` / ``.ini`` / ``.odf`` / ``.vxt`` (docs/01 §5-§8).

These are the small per-map metadata files. The key requirements:

- ``.des`` renders the **real** geyser/scrap object counts (docs/01 §6, docs/06
  Tier-1 cross-file consistency) — never fabricated.
- ``.ini`` matches the pack: ``gameType = K``, ``maxPlayers = 14`` (docs/01 §5).
- ``.odf`` uses the literal ``[SBPMapSettings]`` section name (corpus convention) with
  optional control points.
- ``.vxt`` is copied verbatim (docs/01 §8).
"""

from bzmap.formats.des import write_des, write_des_text
from bzmap.formats.ini import write_ini
from bzmap.formats.odf import write_odf
from bzmap.formats.vxt import write_vxt

# -- .des ---------------------------------------------------------------------


def test_des_renders_real_counts(tmp_path):
    """The description states the geyser and scrap counts passed in."""
    path = tmp_path / "map.des"
    write_des(
        path,
        mission_name="Silver Pools",
        world="Elysium",
        size="Small",
        geysers=16,
        scrap=280,
        players=2,
    )
    text = path.read_text(encoding="utf-8")
    assert "WORLD: Elysium\tSIZE: Small" in text
    assert "GEYSERS: 16\tSCRAP: 280" in text
    assert "PLAYERS: 2" in text


def test_des_counts_not_fabricated(tmp_path):
    """Different real counts produce different text — no hardcoded values."""
    path = tmp_path / "map.des"
    write_des(
        path,
        mission_name="m",
        world="Mars",
        size="Large",
        geysers=42,
        scrap=425,
        players=4,
    )
    text = path.read_text(encoding="utf-8")
    assert "GEYSERS: 42" in text
    assert "SCRAP: 425" in text


def test_des_default_author_credits_ai(tmp_path):
    """Without an explicit author, the credit is honest AI attribution."""
    path = tmp_path / "map.des"
    write_des(
        path,
        mission_name="m",
        world="Moon",
        size="Medium",
        geysers=6,
        scrap=63,
        players=2,
    )
    assert "Made by Skippy" in path.read_text(encoding="utf-8")


def test_des_crlf_line_endings(tmp_path):
    """The .des uses CRLF line endings like the rest of the pack."""
    path = tmp_path / "map.des"
    write_des(
        path,
        mission_name="m",
        world="Europa",
        size="Small",
        geysers=16,
        scrap=270,
        players=2,
    )
    data = path.read_bytes()
    assert b"\r\n" in data
    assert b"\n" not in data.replace(b"\r\n", b"")


def test_des_text_matches_disk(tmp_path):
    """write_des_text and write_des produce identical CRLF text."""
    kwargs = {
        "mission_name": "m",
        "world": "Io",
        "size": "Small",
        "geysers": 10,
        "scrap": 200,
        "players": 2,
    }
    path = tmp_path / "map.des"
    write_des(path, **kwargs)
    assert path.read_text(encoding="utf-8", newline="") == write_des_text(**kwargs)


# -- .ini ---------------------------------------------------------------------


def test_ini_pack_defaults(tmp_path):
    """Default output matches the pack: gameType K, maxPlayers 14."""
    path = tmp_path / "map.ini"
    write_ini(path, "Silver Pools")
    text = path.read_text(encoding="utf-8")
    assert 'missionName = "Silver Pools"' in text
    assert 'gameType = "K"' in text
    assert 'maxPlayers = "14"' in text
    assert 'mapType = "multiplayer"' in text


def test_ini_custom_values(tmp_path):
    """Explicit values override the pack defaults."""
    path = tmp_path / "map.ini"
    write_ini(
        path,
        "Pack Test",
        map_type="instant_action",
        customtags="strat, 1v1",
        min_players=2,
        max_players=8,
        game_type="S",
    )
    text = path.read_text(encoding="utf-8")
    assert 'mapType = "instant_action"' in text
    assert 'customtags = "strat, 1v1"' in text
    assert 'minPlayers = "2"' in text
    assert 'maxPlayers = "8"' in text
    assert 'gameType = "S"' in text


def test_ini_has_all_three_sections(tmp_path):
    """The .ini carries DESCRIPTION, WORKSHOP and MULTIPLAYER sections."""
    path = tmp_path / "map.ini"
    write_ini(path, "Silver Pools")
    text = path.read_text(encoding="utf-8")
    assert "[DESCRIPTION]" in text
    assert "[WORKSHOP]" in text
    assert "[MULTIPLAYER]" in text


# -- .odf ---------------------------------------------------------------------


def test_odf_sbpmapsettings_section_name(tmp_path):
    """The section is the literal legacy SBPMapSettings name — never renamed."""
    path = tmp_path / "map.odf"
    write_odf(path)
    assert "[SBPMapSettings]" in path.read_text(encoding="utf-8")


def test_odf_control_points(tmp_path):
    """Control points are rendered as CP<n>Name / CP<n>X / CP<n>Z."""
    path = tmp_path / "map.odf"
    write_odf(path, control_points=[("ancrCP06_ancrCP11", 849, 2096)])
    text = path.read_text(encoding="utf-8")
    assert "CP1Name = ancrCP06_ancrCP11" in text
    assert "CP1X = 849" in text
    assert "CP1Z = 2096" in text


def test_odf_no_control_points_when_omitted(tmp_path):
    """With no control points the file has no CP entries."""
    path = tmp_path / "map.odf"
    write_odf(path)
    assert "CP1Name" not in path.read_text(encoding="utf-8")


def test_odf_scrap_impact_zone(tmp_path):
    """The optional ScrapImpactZone section is written (default true)."""
    path = tmp_path / "map.odf"
    write_odf(path)
    text = path.read_text(encoding="utf-8")
    assert "[ScrapImpactZone]" in text
    assert "SIZ_IncludeSpawnPoints = 1" in text


# -- .vxt ---------------------------------------------------------------------


def test_vxt_verbatim(tmp_path):
    """The .vxt is written byte-for-byte as supplied."""
    stock = "avobserv avobserv.des\tx\tNSDF\r\n\r\nsvobserv svobserv.des\tx\tCCA\r\n"
    path = tmp_path / "map.vxt"
    write_vxt(path, stock)
    assert path.read_bytes() == stock.encode("utf-8")


def test_vxt_tab_separated_entries(tmp_path):
    """Observer entries are tab-separated, blank-line separated."""
    stock = "avobserv avobserv.des\tx\tNSDF\r\n\r\nbvobserv bvobserv.des\tx\tBDOG\r\n"
    path = tmp_path / "map.vxt"
    write_vxt(path, stock)
    text = path.read_text(encoding="utf-8", newline="")
    assert "avobserv avobserv.des\tx\tNSDF" in text
    assert "bvobserv bvobserv.des\tx\tBDOG" in text
    assert "\r\n\r\n" in text