"""Tests for the top-down render and thumbnail modules (docs/06, docs/07).

Builds small ``HeightMap`` objects directly (no game pack needed) and verifies
that the shaded render reflects terrain, that overlays change pixels at the
mapped world coordinates, and that PNG/BMP thumbnails are written with the
requested dimensions.
"""

import numpy as np
import pytest
from PIL import Image

from bzmap.formats.hg2 import ZONE_SIZE, HeightMap
from bzmap.render.preview import Preview, render_heightmap, render_preview
from bzmap.render.thumbnail import write_bmp, write_png, write_thumbnail


def _flat_map():
    """A 1x1-zone flat heightmap at a nonzero elevation."""
    data = np.full((ZONE_SIZE, ZONE_SIZE), 1000, dtype=np.uint16)
    return HeightMap(1, 1, data)


def _ramp_map():
    """A 1x1-zone map rising along X so the render is non-uniform."""
    data = (np.arange(ZONE_SIZE * ZONE_SIZE, dtype=np.uint16) % ZONE_SIZE * 10)
    data = data.reshape(ZONE_SIZE, ZONE_SIZE)
    return HeightMap(1, 1, data)


# -- base render -------------------------------------------------------------


def test_render_heightmap_returns_rgb_image():
    img = render_heightmap(_flat_map(), size=(64, 64))
    assert img.mode == "RGB"
    assert img.size == (64, 64)


def test_render_heightmap_default_size_is_grid():
    hm = _flat_map()
    img = render_heightmap(hm)
    assert img.size == (hm.grid_x, hm.grid_z)


def test_render_reflects_terrain():
    """A ramp map must not render as a uniform flat image."""
    flat = np.asarray(render_heightmap(_flat_map(), size=(64, 64)))
    ramp = np.asarray(render_heightmap(_ramp_map(), size=(64, 64)))
    # Flat map is uniform (every pixel identical); the ramp is not.
    assert np.all(flat == flat[0, 0])
    assert not np.all(ramp == ramp[0, 0])


def test_render_height_scale_changes_colour():
    """A higher plateau renders differently (colour follows height)."""
    low = HeightMap(1, 1, np.full((ZONE_SIZE, ZONE_SIZE), 200, dtype=np.uint16))
    high = HeightMap(1, 1, np.full((ZONE_SIZE, ZONE_SIZE), 3000, dtype=np.uint16))
    a = np.asarray(render_heightmap(low, size=(16, 16)))
    b = np.asarray(render_heightmap(high, size=(16, 16)))
    assert not np.array_equal(a, b)


# -- overlays ----------------------------------------------------------------


def test_draw_points_changes_pixels():
    hm = _flat_map()
    pv = Preview(hm, size=(64, 64))
    before = np.asarray(pv.image).copy()
    # Centre of the map in world metres.
    pv.draw_points([(hm.width_m / 2, hm.depth_m / 2)], color=(255, 0, 0), radius=3)
    after = np.asarray(pv.image)
    assert not np.array_equal(before, after)
    # The red channel is boosted at the centre pixel.
    cx, cy = pv._px(hm.width_m / 2, hm.depth_m / 2)
    assert after[cy, cx, 0] > before[cy, cx, 0]


def test_draw_routes_changes_pixels():
    hm = _flat_map()
    pv = Preview(hm, size=(64, 64))
    before = np.asarray(pv.image).copy()
    route = [(0, 0), (hm.width_m, hm.depth_m)]
    pv.draw_routes([route], color=(255, 255, 0), width=3)
    assert not np.array_equal(before, np.asarray(pv.image))


def test_draw_regions_tints_pixels():
    hm = _flat_map()
    pv = Preview(hm, size=(64, 64))
    before = np.asarray(pv.image).copy()
    mask = np.zeros_like(hm.data, dtype=bool)
    mask[: ZONE_SIZE // 2, :] = True
    pv.draw_regions([mask], color=(0, 255, 0), alpha=80)
    after = np.asarray(pv.image)
    assert not np.array_equal(before, after)
    # The image is north-up (+z at the top), so the tinted LOW-z half is the
    # BOTTOM of the image; the top stays untinted.
    assert after[54, 10, 1] > before[54, 10, 1]
    assert after[10, 10, 1] == before[10, 10, 1]


def test_draw_regions_rejects_wrong_shape():
    hm = _flat_map()
    pv = Preview(hm, size=(64, 64))
    with pytest.raises(ValueError):
        pv.draw_regions([np.zeros((8, 8), dtype=bool)])


def test_render_preview_applies_all_overlays():
    hm = _flat_map()
    pv = render_preview(
        hm,
        objects=[(hm.width_m / 2, hm.depth_m / 2)],
        routes=[[(0, 0), (hm.width_m, hm.depth_m)]],
        regions=[np.ones_like(hm.data, dtype=bool)],
        size=(64, 64),
    )
    assert pv.image.size == (64, 64)
    assert pv.image.mode == "RGB"


def test_preview_save_png(tmp_path):
    pv = Preview(_flat_map(), size=(32, 32))
    out = tmp_path / "preview.png"
    pv.save(out)
    assert out.is_file()
    with Image.open(out) as im:
        assert im.format == "PNG"
        assert im.size == (32, 32)


# -- thumbnails --------------------------------------------------------------


def test_write_png_resizes(tmp_path):
    img = render_heightmap(_flat_map(), size=(64, 64))
    out = tmp_path / "thumb.png"
    write_png(img, out, size=(256, 256))
    with Image.open(out) as im:
        assert im.format == "PNG"
        assert im.size == (256, 256)


def test_write_bmp(tmp_path):
    img = render_heightmap(_flat_map(), size=(64, 64))
    out = tmp_path / "thumb.bmp"
    write_bmp(img, out, size=(128, 128))
    with Image.open(out) as im:
        assert im.format == "BMP"
        assert im.size == (128, 128)


def test_write_thumbnail_both(tmp_path):
    img = render_heightmap(_flat_map(), size=(64, 64))
    png = tmp_path / "t.png"
    bmp = tmp_path / "t.bmp"
    write_thumbnail(img, png, bmp, size=(64, 64))
    assert png.is_file() and bmp.is_file()
    with Image.open(png) as a, Image.open(bmp) as b:
        assert a.size == b.size == (64, 64)