"""Tests for the ``.LGT`` baked lightmap reader/writer (docs/01 §3, docs/09 E1).

The format is unresolved (copy-only), so the tests assert byte round-tripping and
the documented size formula ``(zonesX * zonesZ + 1) * 65536`` across all five map
dimensions, plus rejection of mismatched sizes.
"""

import pytest

from bzmap.formats.lgt import LightMap, read_lgt, write_lgt

# (zonesX, zonesZ) per the docs/01 size table.
DIMENSIONS = [(1, 1), (2, 2), (3, 3), (4, 3), (4, 4)]


def _lgt_bytes(zonesX, zonesZ):
    """Deterministic pseudo-random bytes of the documented LGT size."""
    n = (zonesX * zonesZ + 1) * 65536
    # A repeating 257-byte pattern gives ~200 distinct byte values, mimicking a
    # real baked-lightmap distribution without being a flat fill.
    pattern = bytes(range(256))
    return (pattern * (n // len(pattern) + 1))[:n]


# -- round-tripping ----------------------------------------------------------


@pytest.mark.parametrize("zonesX,zonesZ", DIMENSIONS)
def test_roundtrip_byte_identical(tmp_path, zonesX, zonesZ):
    """read -> write reproduces the source .LGT file byte-for-byte."""
    data = _lgt_bytes(zonesX, zonesZ)
    src = tmp_path / "map.lgt"
    src.write_bytes(data)

    lm = read_lgt(src, zonesX, zonesZ)
    out = tmp_path / "out.lgt"
    write_lgt(out, lm)

    assert out.read_bytes() == data


@pytest.mark.parametrize("zonesX,zonesZ", DIMENSIONS)
def test_lightmap_holds_bytes_verbatim(tmp_path, zonesX, zonesZ):
    """The LightMap stores the exact bytes it read, no decoding or rewriting."""
    data = _lgt_bytes(zonesX, zonesZ)
    src = tmp_path / "map.lgt"
    src.write_bytes(data)
    lm = read_lgt(src, zonesX, zonesZ)
    assert lm.data == data


# -- size formula ------------------------------------------------------------


@pytest.mark.parametrize("zonesX,zonesZ", DIMENSIONS)
def test_size_matches_docs_formula(tmp_path, zonesX, zonesZ):
    """A map's LGT is (zonesX * zonesZ + 1) * 65536 bytes."""
    data = _lgt_bytes(zonesX, zonesZ)
    src = tmp_path / "map.lgt"
    src.write_bytes(data)
    lm = read_lgt(src, zonesX, zonesZ)
    assert lm.plane_count == zonesX * zonesZ + 1
    assert len(lm.data) == (zonesX * zonesZ + 1) * 65536


def test_size_table_exact_byte_counts():
    """Spot-check the verified byte counts from docs/01 §3."""
    expected = {
        (1, 1): 131072,
        (2, 2): 327680,
        (3, 3): 655360,
        (4, 3): 851968,
        (4, 4): 1114112,
    }
    for (zonesX, zonesZ), n in expected.items():
        assert len(_lgt_bytes(zonesX, zonesZ)) == n


# -- validation --------------------------------------------------------------


def test_wrong_size_rejected(tmp_path):
    """A file that does not match the size formula is rejected."""
    src = tmp_path / "map.lgt"
    src.write_bytes(b"\x00" * (65536 + 1))  # one byte short of a 1x1 map
    with pytest.raises(ValueError):
        read_lgt(src, 1, 1)


def test_empty_lgt_rejected(tmp_path):
    """A zero-length .LGT file is rejected."""
    src = tmp_path / "empty.lgt"
    src.write_bytes(b"")
    with pytest.raises(ValueError):
        read_lgt(src, 1, 1)


def test_construct_validates_size():
    """LightMap.__init__ validates the size for any zone dimensions."""
    with pytest.raises(ValueError):
        LightMap(b"\x00" * 65536, 1, 1)  # 1x1 needs two planes