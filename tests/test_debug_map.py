"""The top-down debug render produces a valid annotated PNG."""

import numpy as np
from PIL import Image

from bzmap.formats.hg2 import HeightMap, write_hg2
from bzmap.formats.mesh import write_mesh
from bzmap.render.debug_map import _water_footprint, render_debug


def _tiny_map(tmp_path, stem="xx01test"):
    d = tmp_path / stem
    d.mkdir()
    rng = np.random.default_rng(0)
    data = (rng.random((256, 256)) * 1500 + 300).astype(np.uint16)
    write_hg2(d / f"{stem}.HG2", HeightMap(1, 1, data))
    # a minimal _S bzn with a couple of objects
    obj = lambda pid, x, z: (
        f"[GameObject]\r\nPrjID [1] =\r\n{pid}\r\n"
        f"  x [1] =\r\n{x}\r\n  z [1] =\r\n{z}\r\nteam [1] =\r\n0\r\n"
    )
    (d / f"{stem}_S.bzn").write_text(
        "size [1] =\r\n3\r\n"
        + obj("player", 100, 100) + obj("eggeizr1", 600, 600)
        + obj("npscr1", 800, 400) + "[AiMission]\r\n[AOIs]\r\n",
        newline="",
    )
    return d


def test_render_debug_writes_png(tmp_path):
    d = _tiny_map(tmp_path)
    out = render_debug(d)

    assert out.is_file()
    im = Image.open(out)
    assert im.size == (900, 900) and im.mode == "RGB"


def test_water_footprint_reads_a_real_mesh(tmp_path):
    from bzmap.formats.hg2 import read_hg2

    d = _tiny_map(tmp_path)
    hm = read_hg2(d / "xx01test.HG2")
    # a small water quad covering cells around (500,500)
    verts = [(490, 100, 490), (510, 100, 490), (490, 100, 510), (510, 100, 510)]
    write_mesh(d / "w.mesh", verts, [(0, 1, 0)] * 4,
               [(0, 0), (1, 0), (0, 1), (1, 1)], [0, 2, 1, 1, 2, 3], "water")

    mask = _water_footprint(d / "w.mesh", hm)
    assert mask is not None and mask.any()
    # the marked cells are near x/z 490-510 m -> grid ~98-102
    zz, xx = np.nonzero(mask)
    assert 95 <= xx.min() and xx.max() <= 105
