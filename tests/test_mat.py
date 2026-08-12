"""Tests for the ``.MAT`` material grid reader/writer and auto-painter (docs/01 §2).

Covers byte round-tripping, the 16-bit field encoding, and auto-painting a
material grid from a heightmap via marching-squares tile transitions.
"""

import numpy as np
import pytest

from bzmap.formats.hg2 import ZONE_SIZE, read_hg2
from bzmap.formats.mat import (
    MATERIAL_MASK,
    TILE_CELLS,
    TILE_M,
    MaterialGrid,
    auto_paint,
    encode_entry,
    read_mat,
    write_mat,
)


def _write_hg2(tmp_path, zonesX, zonesZ, world, unknownA=10):
    """Write a full .HG2 file (header + zone-major data) and return its path."""
    import struct

    header = struct.Struct("<HHHHHH").pack(1, 8, zonesX, zonesZ, unknownA, 0)
    path = tmp_path / "map.hg2"
    with open(path, "wb") as fh:
        fh.write(header)
        for zy in range(zonesZ):
            for zx in range(zonesX):
                zone = world[zy * ZONE_SIZE:(zy + 1) * ZONE_SIZE,
                             zx * ZONE_SIZE:(zx + 1) * ZONE_SIZE]
                fh.write(zone.tobytes())
    return path


def _flat_world(zonesX, zonesZ, value):
    return np.full((zonesZ * ZONE_SIZE, zonesX * ZONE_SIZE), value, dtype=np.uint16)


# -- round-tripping ----------------------------------------------------------


def test_roundtrip_byte_identical(tmp_path):
    """read -> write reproduces the source .MAT file byte-for-byte."""
    for gx, gz in [(64, 64), (128, 128), (192, 192), (256, 192)]:
        grid = np.arange(gx * gz, dtype=np.uint16).reshape(gz, gx)
        path = tmp_path / f"map_{gx}x{gz}.mat"
        grid.tofile(path)
        original = path.read_bytes()

        mg = read_mat(path)
        out = tmp_path / f"out_{gx}x{gz}.mat"
        write_mat(out, mg)

        assert out.read_bytes() == original


def test_mat_grid_size_matches_docs(tmp_path):
    """A 1x1-zone (1280 m) map has a 64x64 MAT grid (8192 bytes)."""
    path = tmp_path / "map.mat"
    np.arange(64 * 64, dtype=np.uint16).reshape(64, 64).tofile(path)
    mg = read_mat(path)
    assert mg.grid_x == 64
    assert mg.grid_z == 64
    assert mg.width_m == 64 * TILE_M
    assert mg.depth_m == 64 * TILE_M


def test_empty_mat_rejected(tmp_path):
    """A zero-length .MAT file is rejected."""
    path = tmp_path / "empty.mat"
    path.write_bytes(b"")
    with pytest.raises(ValueError):
        read_mat(path)


# -- encoding / decoding -----------------------------------------------------


def test_encode_entry_field_layout():
    """encode_entry packs the documented 16-bit fields."""
    # mat_a=1, mat_b=2, cap=0, flip=0, rot=0, variant=0 -> 0x1200
    assert encode_entry(1, 2) == 0x1200
    # A solid tile: same base and target.
    assert encode_entry(3, 3) == 0x3300
    # Rotation occupies bits 4-5.
    assert encode_entry(1, 2, rot=3) == 0x1230
    # Cap and flip flags.
    assert encode_entry(1, 2, cap=1) == 0x1280
    assert encode_entry(1, 2, flip=1) == 0x1240
    # Variant occupies bits 0-1.
    assert encode_entry(1, 2, variant=3) == 0x1203
    # Out-of-range material indices are masked to 4 bits.
    assert encode_entry(0x1F, 0x2F) == 0xFF00


def test_decode_roundtrips_encode():
    """decode() recovers the fields encode_entry() packed."""
    value = encode_entry(5, 9, cap=1, flip=1, rot=2, variant=1)
    mg = MaterialGrid(np.array([[value]], dtype=np.uint16))
    mat_a, mat_b, cap, flip, rot, variant = mg.decode()[0, 0]
    assert (mat_a, mat_b, cap, flip, rot, variant) == (5, 9, 1, 1, 2, 1)


def test_decode_masks_fields():
    """decode() masks each field to its bit width."""
    value = encode_entry(MATERIAL_MASK, MATERIAL_MASK, cap=1, flip=1, rot=3, variant=3)
    mat_a, mat_b, cap, flip, rot, variant = MaterialGrid(
        np.array([[value]], dtype=np.uint16)
    ).decode()[0, 0]
    assert mat_a == MATERIAL_MASK
    assert mat_b == MATERIAL_MASK
    assert (cap, flip, rot, variant) == (1, 1, 3, 3)


# -- auto-painting -----------------------------------------------------------


def _make_heightmap(tmp_path, zonesX=1, zonesZ=1, world=None):
    if world is None:
        world = _flat_world(zonesX, zonesZ, 1000)
    path = _write_hg2(tmp_path, zonesX, zonesZ, world)
    return read_hg2(path)


def test_auto_paint_solid_flat(tmp_path):
    """A flat map with one rule paints every tile solid with that material."""
    hm = _make_heightmap(tmp_path)
    rules = [{"mat_id": 2, "min_h": 0.0, "max_h": 500.0, "min_s": 0.0, "max_s": 1.0}]
    mg = auto_paint(hm, rules)
    assert mg.grid_x == ZONE_SIZE // TILE_CELLS
    assert mg.grid_z == ZONE_SIZE // TILE_CELLS
    assert (mg.data == encode_entry(2, 2)).all()


def test_auto_paint_uses_elevation_bands(tmp_path):
    """Different elevation bands map to different materials."""
    world = _flat_world(1, 1, 0)
    # Left half low (raw 100 = 10 m), right half high (raw 2000 = 200 m).
    world[:, :ZONE_SIZE // 2] = 100
    world[:, ZONE_SIZE // 2:] = 2000
    hm = _make_heightmap(tmp_path, world=world)

    rules = [
        {"mat_id": 1, "min_h": 0.0, "max_h": 50.0, "min_s": 0.0, "max_s": 100.0},
        {"mat_id": 2, "min_h": 100.0, "max_h": 300.0, "min_s": 0.0, "max_s": 100.0},
    ]
    mg = auto_paint(hm, rules)
    decoded = mg.decode()
    # Interior left-half tiles are material 1, interior right-half are 2.
    # (Boundary tiles straddle the step and may be transitions.)
    left = decoded[:, :mg.grid_x // 2 - 2, 0]
    right = decoded[:, mg.grid_x // 2 + 2:, 0]
    assert (left == 1).all()
    assert (right == 2).all()


def test_auto_paint_transition_tile(tmp_path):
    """A tile straddling two materials becomes a transition, not solid."""
    world = _flat_world(1, 1, 0)
    # Make a single 4x4 tile whose top-left cell differs from the other three.
    world[:1, :1] = 2000
    world[1:, :] = 100
    world[0, 1:] = 100
    hm = _make_heightmap(tmp_path, world=world)

    rules = [
        {"mat_id": 1, "min_h": 0.0, "max_h": 50.0, "min_s": 0.0, "max_s": 100.0},
        {"mat_id": 2, "min_h": 100.0, "max_h": 300.0, "min_s": 0.0, "max_s": 100.0},
    ]
    mg = auto_paint(hm, rules)
    # The tile at (0,0) has a single high corner (TL) -> material 2 cap.
    entry = int(mg.data[0, 0])
    mat_a, mat_b, cap, flip, rot, _ = mg.decode()[0, 0]
    assert mat_a == 1 and mat_b == 2
    assert cap == 0 and flip == 0 and rot == 0
    assert entry == encode_entry(1, 2, rot=0)


def test_auto_paint_non_multiple_rejected():
    """auto_paint rejects a heightmap whose cells aren't a multiple of 4.

    A real ``HeightMap`` always has dimensions that are multiples of 256, so
    the guard is exercised here with a lightweight stub whose ``data`` is not
    a multiple of ``TILE_CELLS``.
    """
    class Stub:
        data = np.zeros((10, 10), dtype=np.uint16)
    with pytest.raises(ValueError):
        auto_paint(Stub(), [])


def test_auto_paint_slope_bands(tmp_path):
    """Slope rules select materials on ramps, matching hg2.slope."""
    # A ramp rising 1 m per 5 m cell -> gradient 0.2.
    world = (np.arange(ZONE_SIZE * ZONE_SIZE, dtype=np.uint16) % ZONE_SIZE)
    world = (world * 10).astype(np.uint16).reshape(ZONE_SIZE, ZONE_SIZE)
    hm = _make_heightmap(tmp_path, world=world)

    # Flat rule (slope <= 0.05) and a steep rule (slope >= 0.15).
    rules = [
        {"mat_id": 1, "min_h": 0.0, "max_h": 500.0, "min_s": 0.0, "max_s": 0.05},
        {"mat_id": 2, "min_h": 0.0, "max_h": 500.0, "min_s": 0.15, "max_s": 1.0},
    ]
    mg = auto_paint(hm, rules)
    decoded = mg.decode()
    # Interior tiles (away from the ramp's flat edge) are material 2.
    assert (decoded[1:-1, 1:-1, 0] == 2).all()