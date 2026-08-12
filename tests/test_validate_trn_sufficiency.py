"""Conformance: the terrain validator asserts .trn SUFFICIENCY, not presence.

the generator-fixes audit, task 2 — "the check that would have caught the
3-line stub in seconds". Rule 5: each assertion FAILS on the historical stub
output and passes on a complete file.
"""

import numpy as np

from bzmap.formats.trn import write_complete_trn
from bzmap.validate.terrain import check_trn_sufficiency


def _stub(tmp_path):
    p = tmp_path / "stub.trn"
    p.write_text("[Size]\r\nWidth = 1280\r\nDepth = 1280\r\n")
    return p


def test_the_historical_stub_fails(tmp_path):
    problems = check_trn_sufficiency(_stub(tmp_path))

    assert problems, "the [Size]-only stub must not validate clean"
    text = "\n".join(problems)
    assert "[Color]" in text and "[Sky]" in text and "[Atlases]" in text
    assert "TextureType" in text


def test_a_complete_file_passes(tmp_path):
    out = write_complete_trn(tmp_path / "map.trn", 2560, 2560)

    assert check_trn_sufficiency(out) == []


def test_mat_material_indices_must_be_declared(tmp_path):
    """Every material index the .MAT references needs a [TextureType<i>]."""
    out = write_complete_trn(tmp_path / "map.trn", 2560, 2560)  # declares 0..4
    mat = tmp_path / "map.MAT"
    grid = np.zeros(64, dtype="<u2")
    grid[0] = 0x7700  # material index 7 — undeclared
    grid.tofile(mat)

    problems = check_trn_sufficiency(out, mat)

    assert any("index 7" in p for p in problems)
    # declared indices are fine
    grid[:] = 0x1100
    grid.tofile(mat)
    assert check_trn_sufficiency(out, mat) == []


def test_commented_section_headers_are_seen(tmp_path):
    """Corpus maps write '[TextureType0] // Lava' — the old parser dropped every such
    header, which would make this validator blind to real texture blocks."""
    p = tmp_path / "c.trn"
    p.write_text(
        "[Size]\r\nWidth = 1280\r\nDepth = 1280\r\n"
        "[Color]\r\nPalette=elysium.act\r\n"
        "[Sky]\r\nSkyTexture=elysium.map\r\n"
        "[Atlases]\r\nMaterialName = el_detail_atlas\r\n"
        "[TextureType0] // Lava\r\nSolidA0 = ma11sA0.map\r\n"
    )

    assert check_trn_sufficiency(p) == []
