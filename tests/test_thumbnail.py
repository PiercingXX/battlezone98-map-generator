"""Conformance: build_map ships per-map thumbnails.

the generator-fixes audit, task 5 (as corrected in the contract): a 512x512
.BMP for the shell/lobby AND a 1024x1024 .png — 3/30 corpus maps ship the png and
its absence rendered a blank in-game map radar during testing. docs/07 already
carries the corrected claim; this test pins the build output.
"""

from PIL import Image

from bzmap import cli
from bzmap.package.build_map import build_map

from tests.test_build_map import _make_source_dir, _write_stock_bzn


def test_build_ships_bmp_and_png(tmp_path):
    result = cli.generate_map(seed=42)
    stock = _write_stock_bzn(tmp_path)
    src = _make_source_dir(tmp_path)

    map_dir = build_map(
        result, "xx01ridg", tmp_path / "build",
        bzn_path=stock, source_dir=src, mission_name="Ridge Run",
    )

    bmp = Image.open(map_dir / "xx01ridg.BMP")
    png = Image.open(map_dir / "xx01ridg.png")
    assert bmp.size == (512, 512) and bmp.mode == "RGB"
    assert png.size == (1024, 1024)
    # not a blank fill — the render carries actual terrain shading
    extrema = png.convert("L").getextrema()
    assert extrema[1] > extrema[0], "thumbnail is a flat fill"
