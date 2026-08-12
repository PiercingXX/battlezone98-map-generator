"""Tests for the ``.HG2`` heightmap reader/writer (docs/01 §1).

Covers the zone-major layout trap, header ``unknownA`` preservation, byte
round-tripping, bilinear ``sample_m``, and the slope/buildable masks.
"""

import struct

import numpy as np
import pytest

from bzmap.formats.hg2 import (
    GRID_M,
    HEIGHT_SCALE,
    ZONE_SIZE,
    buildable_mask,
    read_hg2,
    sample_m,
    slope,
    write_hg2,
)

HEADER = struct.Struct("<HHHHHH")


def _zone_major_bytes(zonesX, zonesZ, world):
    """Pack a world row-major uint16 array into zone-major on-disk bytes."""
    out = bytearray()
    for zy in range(zonesZ):
        for zx in range(zonesX):
            zone = world[zy * ZONE_SIZE:(zy + 1) * ZONE_SIZE,
                         zx * ZONE_SIZE:(zx + 1) * ZONE_SIZE]
            out += zone.tobytes()
    return bytes(out)


def _write_hg2(tmp_path, zonesX, zonesZ, world, unknownA=10):
    """Write a full .HG2 file (header + zone-major data) and return its path."""
    path = tmp_path / "map.hg2"
    header = HEADER.pack(1, 8, zonesX, zonesZ, unknownA, 0)
    with open(path, "wb") as fh:
        fh.write(header)
        fh.write(_zone_major_bytes(zonesX, zonesZ, world))
    return path


def _ramp(zonesX, zonesZ):
    """A world array whose value at (x, z) is ``z * 1000 + x`` (unique per cell)."""
    return np.arange(zonesZ * ZONE_SIZE * zonesX * ZONE_SIZE,
                     dtype=np.uint16).reshape(zonesZ * ZONE_SIZE, zonesX * ZONE_SIZE)


# -- zone-major layout ------------------------------------------------------


def test_zone_major_layout_is_not_row_major(tmp_path):
    """De-zoning must recover a coherent map, not tiled garbage.

    A single 2x1-zone map with a step between the two zones: if the reader
    treated the stream as row-major it would interleave the zones' rows.
    """
    zonesX, zonesZ = 2, 1
    world = np.zeros((ZONE_SIZE, ZONE_SIZE * 2), dtype=np.uint16)
    world[:, ZONE_SIZE:] = 4095  # right zone high, left zone low
    path = _write_hg2(tmp_path, zonesX, zonesZ, world)

    hm = read_hg2(path)
    # The two zones must be intact as blocks, not interleaved.
    assert hm.data.shape == (ZONE_SIZE, ZONE_SIZE * 2)
    assert (hm.data[:, :ZONE_SIZE] == 0).all()
    assert (hm.data[:, ZONE_SIZE:] == 4095).all()


def test_roundtrip_byte_identical(tmp_path):
    """read -> write reproduces the source file byte-for-byte."""
    for zonesX, zonesZ in [(1, 1), (2, 2), (3, 3), (4, 3)]:
        world = _ramp(zonesX, zonesZ)
        path = _write_hg2(tmp_path, zonesX, zonesZ, world, unknownA=24)
        original = path.read_bytes()

        hm = read_hg2(path)
        out = tmp_path / f"out_{zonesX}x{zonesZ}.hg2"
        write_hg2(out, hm)

        assert out.read_bytes() == original


def test_unknownA_preserved(tmp_path):
    """The header unknownA field round-trips verbatim."""
    path = _write_hg2(tmp_path, 1, 1, np.zeros((ZONE_SIZE, ZONE_SIZE), dtype=np.uint16),
                      unknownA=11)
    hm = read_hg2(path)
    assert hm.unknownA == 11
    out = tmp_path / "out.hg2"
    write_hg2(out, hm)
    assert HEADER.unpack(out.read_bytes()[:12])[4] == 11


def test_header_fields(tmp_path):
    """version/depth/zonesX/zonesZ are read from the header."""
    path = _write_hg2(tmp_path, 4, 2, _ramp(4, 2))
    hm = read_hg2(path)
    assert hm.version == 1
    assert hm.depth == 8
    assert hm.zonesX == 4
    assert hm.zonesZ == 2
    assert hm.width_m == 4 * 1280
    assert hm.depth_m == 2 * 1280


def test_truncated_data_rejected(tmp_path):
    """A file with the wrong number of samples is rejected."""
    path = tmp_path / "bad.hg2"
    path.write_bytes(HEADER.pack(1, 8, 1, 1, 10, 0) + b"\x00\x00" * 10)
    with pytest.raises(ValueError):
        read_hg2(path)


def test_unsupported_zone_size_rejected(tmp_path):
    """A non-256 zone size is rejected."""
    path = tmp_path / "bad.hg2"
    # depth=6 -> zone size 64.
    path.write_bytes(HEADER.pack(1, 6, 1, 1, 10, 0) + b"\x00\x00" * (64 * 64))
    with pytest.raises(ValueError):
        read_hg2(path)


# -- bilinear sampling ------------------------------------------------------


def test_sample_m_at_grid_point(tmp_path):
    """sample_m at an exact grid point returns raw * HEIGHT_SCALE."""
    world = np.full((ZONE_SIZE, ZONE_SIZE), 1000, dtype=np.uint16)
    path = _write_hg2(tmp_path, 1, 1, world)
    hm = read_hg2(path)
    assert sample_m(hm, 0.0, 0.0) == pytest.approx(1000 * HEIGHT_SCALE)
    # A grid point 5 cells in.
    assert sample_m(hm, 5 * GRID_M, 5 * GRID_M) == pytest.approx(1000 * HEIGHT_SCALE)


def test_sample_m_bilinear_interpolation(tmp_path):
    """sample_m linearly interpolates between four surrounding cells."""
    world = np.zeros((ZONE_SIZE, ZONE_SIZE), dtype=np.uint16)
    # Four cells forming a unit square: 0 100 / 200 300 (raw).
    world[0, 0] = 0
    world[0, 1] = 100
    world[1, 0] = 200
    world[1, 1] = 300
    path = _write_hg2(tmp_path, 1, 1, world)
    hm = read_hg2(path)

    # Centre of the four cells -> average of the corners.
    # The four cells occupy world x,z in [0, 10]; their centre in cell
    # coordinates is (0.5, 0.5), i.e. world (2.5, 2.5).
    cx = 0.5 * GRID_M
    cz = 0.5 * GRID_M
    expected = (0 + 100 + 200 + 300) / 4 * HEIGHT_SCALE
    assert sample_m(hm, cx, cz) == pytest.approx(expected)

    # Halfway between (0,0) and (1,0) horizontally.
    assert sample_m(hm, 0.5 * GRID_M, 0.0) == pytest.approx(50 * HEIGHT_SCALE)


def test_sample_m_clamps_at_edges(tmp_path):
    """Sampling beyond the map edge clamps to the boundary cell."""
    world = np.full((ZONE_SIZE, ZONE_SIZE), 500, dtype=np.uint16)
    path = _write_hg2(tmp_path, 1, 1, world)
    hm = read_hg2(path)
    # Far outside the map -> still returns the edge height, not NaN.
    assert sample_m(hm, -1000.0, -1000.0) == pytest.approx(500 * HEIGHT_SCALE)
    assert sample_m(hm, 1e6, 1e6) == pytest.approx(500 * HEIGHT_SCALE)


# -- slope / buildability ---------------------------------------------------


def test_slope_flat_map_is_zero(tmp_path):
    """A flat map has zero slope everywhere."""
    world = np.full((ZONE_SIZE, ZONE_SIZE), 1000, dtype=np.uint16)
    path = _write_hg2(tmp_path, 1, 1, world)
    hm = read_hg2(path)
    sl = slope(hm)
    assert sl.shape == hm.data.shape
    assert np.allclose(sl, 0.0)


def test_slope_ramp(tmp_path):
    """A constant ramp rises 1 m per 5 m cell -> gradient 0.2."""
    # Height increases by 10 raw (1 m) per cell along X.
    world = (np.arange(ZONE_SIZE * ZONE_SIZE, dtype=np.uint16) % ZONE_SIZE)
    world = (world * 10).astype(np.uint16).reshape(ZONE_SIZE, ZONE_SIZE)
    path = _write_hg2(tmp_path, 1, 1, world)
    hm = read_hg2(path)
    sl = slope(hm)
    assert np.allclose(sl[1:-1, 1:-1], 0.2, atol=1e-6)


def test_buildable_mask_filters_slope(tmp_path):
    """Steep cells are excluded from the buildable mask."""
    world = np.zeros((ZONE_SIZE, ZONE_SIZE), dtype=np.uint16)
    # Left half flat, right half a steep ramp (rise 1 m per 5 m cell). The
    # first ramp column is already elevated so it rises against the flat half.
    world[:, ZONE_SIZE // 2:] = (np.arange(ZONE_SIZE // 2, dtype=np.uint16) + 1) * 10
    path = _write_hg2(tmp_path, 1, 1, world)
    hm = read_hg2(path)

    mask = buildable_mask(hm, max_slope=0.15)
    assert mask.dtype == bool
    assert mask.shape == hm.data.shape
    # The flat half is buildable; the steep ramp is not.
    assert mask[:, :ZONE_SIZE // 2].all()
    assert not mask[:, ZONE_SIZE // 2:].any()


def test_buildable_mask_default_threshold(tmp_path):
    """The default threshold is permissive enough for flat terrain."""
    world = np.full((ZONE_SIZE, ZONE_SIZE), 800, dtype=np.uint16)
    path = _write_hg2(tmp_path, 1, 1, world)
    hm = read_hg2(path)
    assert buildable_mask(hm).all()