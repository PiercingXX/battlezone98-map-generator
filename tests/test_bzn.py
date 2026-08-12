"""Tests for the ``.bzn`` mission object reader/writer (docs/02).

Covers the two key/value forms, byte-identical round-trip (Rule 4 / R1),
template-and-mutate position/yaw/identity substitution (R2), and the R4
invariants enforced by :meth:`BznFile.validate`.
"""

import math

import pytest

from bzmap.formats.bzn import BznFile, GameObject, read_bzn, write_bzn

# A realistic ASCII .bzn: header, one geyser object, one player object, and the
# trailing AiMission/AOIs/AiPaths block. CRLF line endings, value-on-next-line
# and value-on-same-line forms both present.
HEADER = (
    "version [1] =\r\n"
    "2016\r\n"
    "binarySave [1] =\r\n"
    "false\r\n"
    "msn_filename = uexmap10.bzn\r\n"
    "seq_count [1] =\r\n"
    "3\r\n"
    "missionSave [1] =\r\n"
    "true\r\n"
    "TerrainName = uexmap10\r\n"
    "size [1] =\r\n"
    "2\r\n"
)

GEYSER = (
    "[GameObject]\r\n"
    "PrjID [1] =\r\n"
    "eggeizr1\r\n"
    "seqno [1] =\r\n"
    "1\r\n"
    "pos [1] =\r\n"
    "  x [1] =\r\n"
    "625.345\r\n"
    "  y [1] =\r\n"
    "55.6\r\n"
    "  z [1] =\r\n"
    "782.817\r\n"
    "team [1] =\r\n"
    "0\r\n"
    "label = eggeizr10_geyser\r\n"
    "isUser [1] =\r\n"
    "0\r\n"
    "obj_addr = 00000001\r\n"
    "transform [1] =\r\n"
    "  right_x [1] =\r\n"
    "0.964178\r\n"
    "  right_y [1] =\r\n"
    "-0.0139858\r\n"
    "  right_z [1] =\r\n"
    "0.264887\r\n"
    "  up_x [1] =\r\n"
    "0.019992\r\n"
    "  up_y [1] =\r\n"
    "0.9996\r\n"
    "  up_z [1] =\r\n"
    "-0.019992\r\n"
    "  front_x [1] =\r\n"
    "-0.264502\r\n"
    "  front_y [1] =\r\n"
    "0.0245715\r\n"
    "  front_z [1] =\r\n"
    "0.964072\r\n"
    "  posit_x [1] =\r\n"
    "625.345\r\n"
    "  posit_y [1] =\r\n"
    "55.6\r\n"
    "  posit_z [1] =\r\n"
    "782.817\r\n"
    "illumination [1] =\r\n"
    "0\r\n"
    "pos [1] =\r\n"
    "  x [1] =\r\n"
    "625.345\r\n"
    "  y [1] =\r\n"
    "55.6\r\n"
    "  z [1] =\r\n"
    "782.817\r\n"
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
    "1\r\n"
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

# A player object (team 1) with the four player-only extra fields after transform.
PLAYER = (
    "[GameObject]\r\n"
    "PrjID [1] =\r\n"
    "player\r\n"
    "seqno [1] =\r\n"
    "2\r\n"
    "pos [1] =\r\n"
    "  x [1] =\r\n"
    "600\r\n"
    "  y [1] =\r\n"
    "55\r\n"
    "  z [1] =\r\n"
    "700\r\n"
    "team [1] =\r\n"
    "1\r\n"
    "label = player0_wingman\r\n"
    "isUser [1] =\r\n"
    "0\r\n"
    "obj_addr = 00000002\r\n"
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
    "600\r\n"
    "  posit_y [1] =\r\n"
    "55\r\n"
    "  posit_z [1] =\r\n"
    "700\r\n"
    "abandoned [1] =\r\n"
    "false\r\n"
    "cloakState [1] =\r\n"
    "0\r\n"
    "cloakTransBeginTime [1] =\r\n"
    "0\r\n"
    "cloakTransEndTime [1] =\r\n"
    "0\r\n"
    "illumination [1] =\r\n"
    "1\r\n"
    "pos [1] =\r\n"
    "  x [1] =\r\n"
    "600\r\n"
    "  y [1] =\r\n"
    "55\r\n"
    "  z [1] =\r\n"
    "700\r\n"
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
    "2\r\n"
    "name = \r\n"
    "isCritical [1] =\r\n"
    "false\r\n"
    "isObjective [1] =\r\n"
    "false\r\n"
    "isSelected [1] =\r\n"
    "false\r\n"
    "isVisible [1] =\r\n"
    "2\r\n"
    "seen [1] =\r\n"
    "2\r\n"
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

TAIL = (
    "[AiMission]\r\n"
    "[AOIs]\r\n"
    "size [1] =\r\n"
    "0\r\n"
    "[AiPaths]\r\n"
    "count [1] =\r\n"
    "0\r\n"
)

SAMPLE = HEADER + GEYSER + PLAYER + TAIL


def _write_sample(tmp_path, text=SAMPLE, name="map.bzn"):
    path = tmp_path / name
    path.write_bytes(text.encode("utf-8"))
    return path


# -- round-tripping ----------------------------------------------------------


def test_roundtrip_byte_identical(tmp_path):
    """read -> write reproduces the source .bzn file byte-for-byte."""
    src = _write_sample(tmp_path)
    original = src.read_bytes()

    bzn = read_bzn(src)
    out = tmp_path / "out.bzn"
    write_bzn(out, bzn)

    assert out.read_bytes() == original


def test_roundtrip_preserves_crlf(tmp_path):
    """CRLF line endings survive an untouched round-trip."""
    src = _write_sample(tmp_path)
    bzn = read_bzn(src)
    out = tmp_path / "out.bzn"
    write_bzn(out, bzn)
    data = out.read_bytes()
    assert b"\r\n" in data
    assert b"\n" not in data.replace(b"\r\n", b"")


def test_roundtrip_no_trailing_newline(tmp_path):
    """A file without a trailing CRLF round-trips without gaining one."""
    path = tmp_path / "noeol.bzn"
    path.write_bytes(SAMPLE.rstrip("\r\n").encode("utf-8"))
    bzn = read_bzn(path)
    out = tmp_path / "out.bzn"
    write_bzn(out, bzn)
    assert out.read_bytes() == path.read_bytes()


def test_parses_objects_and_tail(tmp_path):
    """Header, both objects and the trailing block are parsed."""
    bzn = read_bzn(_write_sample(tmp_path))
    assert len(bzn.objects) == 2
    assert [o.prjid for o in bzn.objects] == ["eggeizr1", "player"]
    assert bzn.objects[0].label == "eggeizr10_geyser"
    assert bzn.objects[1].team == 1
    assert "[AiMission]" in "\r\n".join(bzn.tail)


def test_header_values(tmp_path):
    """Header values are readable through header_value()."""
    bzn = read_bzn(_write_sample(tmp_path))
    assert bzn.header_value("version [1]") == "2016"
    assert bzn.header_value("binarySave [1]") == "false"
    assert bzn.header_value("msn_filename") == "uexmap10.bzn"
    assert bzn.header_value("size [1]") == "2"
    assert bzn.header_value("TerrainName") == "uexmap10"


# -- template-and-mutate -----------------------------------------------------


def _geyser_template():
    """A GameObject cloned from the verbatim geyser block (incl. [GameObject])."""
    return GameObject.from_template(GEYSER)


def test_set_position_updates_all_three_places():
    """set_position rewrites both pos blocks and transform.posit_*."""
    obj = _geyser_template()
    obj.set_position(100.0, 20.0, 300.0)
    lines = obj.lines
    # First pos block.
    assert lines[lines.index("  x [1] =") + 1] == "100"
    # transform.posit_x.
    assert lines[lines.index("  posit_x [1] =") + 1] == "100"
    # Second pos block (after illumination).
    assert lines[lines.index("illumination [1] =") + 1] == "0"
    # Count occurrences of each coordinate across the whole block: 3 each.
    xs = [i for i, l in enumerate(lines) if l == "100"]
    assert len(xs) == 3


def test_set_yaw_clean_rotation():
    """set_yaw writes a pure yaw basis: right=(c,0,-s), up=(0,1,0), front=(s,0,c)."""
    obj = _geyser_template()
    theta = math.radians(90.0)
    obj.set_yaw(theta)
    c = math.cos(theta)
    s = math.sin(theta)

    def val(key):
        i = obj.lines.index(f"  {key} [1] =")
        return float(obj.lines[i + 1])

    assert val("right_x") == pytest.approx(c)
    assert val("right_z") == pytest.approx(-s)
    assert val("up_y") == pytest.approx(1.0)
    assert val("front_x") == pytest.approx(s)
    assert val("front_z") == pytest.approx(c)


def test_set_identity_updates_seqno_seqno_addr_label():
    """set_identity updates seqno, seqNo, obj_addr and label."""
    obj = _geyser_template()
    obj.set_identity(seqno=7, addr=3, label="eggeizr10_geyser")
    assert obj.seqno == 7
    assert obj.obj_addr == 3
    assert obj.label == "eggeizr10_geyser"
    # seqNo carries the same value as seqno.
    i = obj.lines.index("seqNo [1] =")
    assert obj.lines[i + 1] == "7"
    # obj_addr is 8-digit hex.
    assert "obj_addr = 00000003" in obj.lines


def test_template_strips_comments():
    """Template annotation lines (#) are stripped on load."""
    text = "# a comment\r\n[GameObject]\r\nPrjID [1] =\r\nx\r\n"
    obj = GameObject.from_template(text)
    assert obj.lines == ["[GameObject]", "PrjID [1] =", "x"]


# -- R4 invariants -----------------------------------------------------------


def test_validate_passes_on_wellformed_file(tmp_path):
    """A correctly-formed file passes all R4 invariants."""
    bzn = read_bzn(_write_sample(tmp_path))
    assert bzn.validate() == []


def test_validate_size_mismatch(tmp_path):
    """size != object count is reported."""
    bzn = read_bzn(_write_sample(tmp_path))
    bzn.set_header("size [1]", 99)
    problems = bzn.validate()
    assert any("size" in p for p in problems)


def test_validate_seq_count_mismatch(tmp_path):
    """seq_count != max(seqno)+1 is reported."""
    bzn = read_bzn(_write_sample(tmp_path))
    bzn.set_header("seq_count [1]", 1)
    problems = bzn.validate()
    assert any("seq_count" in p for p in problems)


def test_validate_missing_player(tmp_path):
    """A file with no player object is reported."""
    bzn = read_bzn(_write_sample(tmp_path))
    # Remove the player object (index 1).
    bzn.objects = [bzn.objects[0]]
    bzn.set_header("size [1]", 1)
    problems = bzn.validate()
    assert any("player" in p for p in problems)


def test_validate_obj_addr_not_contiguous(tmp_path):
    """Non-contiguous obj_addr is reported."""
    bzn = read_bzn(_write_sample(tmp_path))
    bzn.objects[1].set_identity(seqno=2, addr=9, label="player0_wingman")
    problems = bzn.validate()
    assert any("obj_addr" in p for p in problems)


def test_validate_missing_tail(tmp_path):
    """A missing trailing block is reported."""
    text = HEADER + GEYSER + PLAYER  # no TAIL
    bzn = read_bzn(_write_sample(tmp_path, text))
    problems = bzn.validate()
    assert any("AiMission" in p for p in problems)
    assert any("AiPaths" in p for p in problems)


# -- build from templates ----------------------------------------------------


def test_build_assembles_file(tmp_path):
    """BznFile.build() assembles header + objects + tail into a valid file."""
    geyser = GameObject.from_template(GEYSER)
    geyser.set_identity(seqno=1, addr=1, label="eggeizr10_geyser")
    player = GameObject.from_template(PLAYER)
    player.set_identity(seqno=2, addr=2, label="player0_wingman")

    bzn = BznFile.build(HEADER, [geyser, player], TAIL)
    assert bzn.validate() == []

    out = tmp_path / "built.bzn"
    write_bzn(out, bzn)
    assert out.read_bytes() == SAMPLE.encode("utf-8")