"""Tests for the template loader (docs/02 §6 R2, Rule 3).

Covers loading verbatim object/header/tail blocks from ``reference/`` and from
a stock ``.bzn`` (the "stock worlds" source), comment stripping, the
``template()`` convenience idiom, and error handling for unavailable objects.
"""

import pytest

from bzmap.formats.bzn import BznFile, GameObject
from bzmap.formats.templates import DEFAULT_REFERENCE_DIR, TemplateLoader, template


def _make_stock(tmp_path, prjid="player"):
    """Write a minimal stock-like .bzn with one object of ``prjid``."""
    header = (
        "version [1] =\r\n"
        "2016\r\n"
        "binarySave [1] =\r\n"
        "false\r\n"
        "msn_filename = stock.bzn\r\n"
        "seq_count [1] =\r\n"
        "1\r\n"
        "missionSave [1] =\r\n"
        "true\r\n"
        "TerrainName = stock\r\n"
        "size [1] =\r\n"
        "1\r\n"
    )
    obj = (
        "[GameObject]\r\n"
        "PrjID [1] =\r\n"
        f"{prjid}\r\n"
        "seqno [1] =\r\n"
        "0\r\n"
        "pos [1] =\r\n"
        "  x [1] =\r\n"
        "10\r\n"
        "  y [1] =\r\n"
        "20\r\n"
        "  z [1] =\r\n"
        "30\r\n"
        "team [1] =\r\n"
        "1\r\n"
        "label = stockobj\r\n"
        "isUser [1] =\r\n"
        "0\r\n"
        "obj_addr = 00000001\r\n"
        "transform [1] =\r\n"
        "  right_x [1] =\r\n"
        "1\r\n"
        "  right_y [1] =\r\n"
        "0\r\n"
        "  right_z [1] =\r\n"
        "0\r\n"
        "  up_x [1] =\r\n"
        "0\r\n"
        "  up_y [1] =\r\n"
        "1\r\n"
        "  up_z [1] =\r\n"
        "0\r\n"
        "  front_x [1] =\r\n"
        "0\r\n"
        "  front_y [1] =\r\n"
        "0\r\n"
        "  front_z [1] =\r\n"
        "1\r\n"
        "  posit_x [1] =\r\n"
        "10\r\n"
        "  posit_y [1] =\r\n"
        "20\r\n"
        "  posit_z [1] =\r\n"
        "30\r\n"
        "illumination [1] =\r\n"
        "0\r\n"
        "pos [1] =\r\n"
        "  x [1] =\r\n"
        "10\r\n"
        "  y [1] =\r\n"
        "20\r\n"
        "  z [1] =\r\n"
        "30\r\n"
        "euler =\r\n"
        " mass [1] =\r\n"
        "0\r\n"
        " mass_inv [1] =\r\n"
        "1e+030\r\n"
        " v_mag [1] =\r\n"
        "0\r\n"
        " v_mag_inv [1] =\r\n"
        "1e+030\r\n"
        " I [1] =\r\n"
        "1\r\n"
        " k_i [1] =\r\n"
        "0\r\n"
        " v [1] =\r\n"
        "  x [1] =\r\n"
        "0\r\n"
        "  y [1] =\r\n"
        "0\r\n"
        "  z [1] =\r\n"
        "0\r\n"
        " omega [1] =\r\n"
        "  x [1] =\r\n"
        "0\r\n"
        "  y [1] =\r\n"
        "0\r\n"
        "  z [1] =\r\n"
        "0\r\n"
        " Accel [1] =\r\n"
        "  x [1] =\r\n"
        "0\r\n"
        "  y [1] =\r\n"
        "0\r\n"
        "  z [1] =\r\n"
        "0\r\n"
        "seqNo [1] =\r\n"
        "0\r\n"
        "name = \r\n"
        "isCritical [1] =\r\n"
        "false\r\n"
        "isObjective [1] =\r\n"
        "false\r\n"
        "isSelected [1] =\r\n"
        "false\r\n"
        "isVisible [1] =\r\n"
        "0\r\n"
        "seen [1] =\r\n"
        "0\r\n"
        "healthRatio [1] =\r\n"
        "1\r\n"
        "curHealth [1] =\r\n"
        "0\r\n"
        "maxHealth [1] =\r\n"
        "0\r\n"
        "ammoRatio [1] =\r\n"
        "0\r\n"
        "curAmmo [1] =\r\n"
        "0\r\n"
        "maxAmmo [1] =\r\n"
        "0\r\n"
        "priority [1] =\r\n"
        "0\r\n"
        "what = 00000000\r\n"
        "who [1] =\r\n"
        "0\r\n"
        "where = 00000000\r\n"
        "param [1] =\r\n"
        "\r\n"
        "aiProcess [1] =\r\n"
        "false\r\n"
        "isCargo [1] =\r\n"
        "false\r\n"
        "independence [1] =\r\n"
        "1\r\n"
        "curPilot [1] =\r\n"
        "\r\n"
        "perceivedTeam [1] =\r\n"
        "0\r\n"
    )
    tail = (
        "[AiMission]\r\n"
        "[AOIs]\r\n"
        "size [1] =\r\n"
        "0\r\n"
        "[AiPaths]\r\n"
        "count [1] =\r\n"
        "0\r\n"
    )
    path = tmp_path / "stock.bzn"
    path.write_bytes((header + obj + tail).encode("utf-8"))
    return path


# -- reference/ source ---------------------------------------------------------


def test_default_reference_dir_points_at_repo_reference():
    """DEFAULT_REFERENCE_DIR resolves to the repo's reference/ directory."""
    assert DEFAULT_REFERENCE_DIR.is_dir()
    assert (DEFAULT_REFERENCE_DIR / "bzn-object-template.txt").is_file()
    assert (DEFAULT_REFERENCE_DIR / "bzn-header-tail-template.txt").is_file()


def test_reference_object_returns_verbatim_geyser():
    """object() returns the reference geyser block with comments stripped."""
    loader = TemplateLoader()
    text = loader.object("eggeizr1")
    obj = GameObject.from_template(text)
    assert obj.prjid == "eggeizr1"
    assert obj.label == "eggeizr10_geyser"
    # No template annotation lines survive.
    assert not any(l.lstrip().startswith("#") for l in text.splitlines())
    # The block starts with the [GameObject] header.
    assert text.splitlines()[0] == "[GameObject]"


def test_reference_object_missing_prjid_raises():
    """An unknown PrjID in reference/ raises KeyError."""
    loader = TemplateLoader()
    with pytest.raises(KeyError):
        loader.object("no_such_object")


def test_reference_header_and_tail():
    """header() and tail() return the verbatim reference blocks (comments stripped)."""
    loader = TemplateLoader()
    header = loader.header()
    tail = loader.tail()
    assert "version [1] =" in header
    assert "TerrainName" in header
    assert "[AiMission]" in tail
    assert "[AiPaths]" in tail
    assert not any(l.lstrip().startswith("#") for l in header.splitlines())
    assert not any(l.lstrip().startswith("#") for l in tail.splitlines())


def test_reference_header_tail_feed_build():
    """header()/tail() and object() assemble into a valid BznFile via build()."""
    loader = TemplateLoader()
    obj = GameObject.from_template(loader.object("eggeizr1"))
    obj.set_identity(seqno=0, addr=1, label="eggeizr10_geyser")
    bzn = BznFile.build(loader.header(), [obj], loader.tail())
    # Only the player invariant is unmet (no player object) — the block structure
    # must be intact enough to parse and re-emit. The header and tail are kept
    # verbatim, so their defining markers must survive the round-trip.
    header = "\r\n".join(bzn.header)
    tail = "\r\n".join(bzn.tail)
    assert "version [1] =" in header
    assert "TerrainName" in header
    assert "[AiMission]" in tail
    assert "[AOIs]" in tail
    assert "[AiPaths]" in tail
    assert len(bzn.objects) == 1
    assert bzn.objects[0].prjid == "eggeizr1"


# -- stock worlds source -------------------------------------------------------


def test_stock_object_returns_verbatim_block(tmp_path):
    """object() sources a block from a stock .bzn when bzn_path is set."""
    stock = _make_stock(tmp_path, prjid="player")
    loader = TemplateLoader(bzn_path=stock)
    text = loader.object("player")
    obj = GameObject.from_template(text)
    assert obj.prjid == "player"
    assert obj.label == "stockobj"
    assert obj.team == 1


def test_stock_object_takes_precedence_over_reference(tmp_path):
    """A stock bzn_path supplies blocks even when the reference has one."""
    stock = _make_stock(tmp_path, prjid="eggeizr1")
    loader = TemplateLoader(bzn_path=stock)
    text = loader.object("eggeizr1")
    obj = GameObject.from_template(text)
    # The stock block's label differs from the reference geyser's.
    assert obj.label == "stockobj"


def test_stock_missing_prjid_falls_back_to_reference(tmp_path):
    """A PrjID absent from the stock file falls back to reference/."""
    stock = _make_stock(tmp_path, prjid="player")
    loader = TemplateLoader(bzn_path=stock)
    text = loader.object("eggeizr1")
    obj = GameObject.from_template(text)
    assert obj.prjid == "eggeizr1"


def test_stock_header_tail(tmp_path):
    """header()/tail() come from the stock file when bzn_path is set."""
    stock = _make_stock(tmp_path, prjid="player")
    loader = TemplateLoader(bzn_path=stock)
    assert "msn_filename = stock.bzn" in loader.header()
    assert "TerrainName = stock" in loader.header()
    assert "[AiMission]" in loader.tail()


def test_available_prjids_includes_reference_and_stock(tmp_path):
    """available_prjids() reports both the reference and stock objects."""
    stock = _make_stock(tmp_path, prjid="player")
    loader = TemplateLoader(bzn_path=stock)
    prjids = loader.available_prjids()
    assert "eggeizr1" in prjids  # from reference/
    assert "player" in prjids    # from stock


# -- module-level convenience --------------------------------------------------


def test_template_convenience():
    """template() returns a verbatim block for the reference geyser."""
    obj = GameObject.from_template(template("eggeizr1"))
    assert obj.prjid == "eggeizr1"


def test_template_convenience_with_stock(tmp_path):
    """template() accepts a bzn_path to source a stock object."""
    stock = _make_stock(tmp_path, prjid="player")
    obj = GameObject.from_template(template("player", bzn_path=stock))
    assert obj.prjid == "player"


def test_template_missing_prjid_raises():
    """template() raises KeyError for an unavailable PrjID."""
    with pytest.raises(KeyError):
        template("no_such_object")