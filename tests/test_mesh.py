"""The OGRE .mesh writer round-trips with the expected chunk structure."""

import struct
import tempfile
from pathlib import Path

from bzmap.formats.mesh import write_mesh


def _parse(raw):
    """Minimal chunk walker: returns {chunk_id: count} and the submesh facts."""
    assert raw[:2] == struct.pack("<H", 0x1000)
    nl = raw.index(b"\n", 2)
    assert raw[2:nl + 1] == b"[MeshSerializer_v1.100]\n"
    pos = nl + 1
    facts = {}
    # M_MESH
    cid, size = struct.unpack_from("<HI", raw, pos)
    assert cid == 0x3000
    facts["skeletal"] = raw[pos + 6]
    # M_SUBMESH
    sm = pos + 7
    cid, size = struct.unpack_from("<HI", raw, sm)
    assert cid == 0x4000
    body = sm + 6
    nlm = raw.index(b"\n", body)
    facts["material"] = raw[body:nlm].decode()
    p = nlm + 1
    facts["shared"] = raw[p]; p += 1
    facts["indexCount"], = struct.unpack_from("<I", raw, p); p += 4
    facts["indexes32"] = raw[p]; p += 1
    p += facts["indexCount"] * 2
    cid, gsize = struct.unpack_from("<HI", raw, p)
    assert cid == 0x5000, hex(cid)
    facts["vertexCount"], = struct.unpack_from("<I", raw, p + 6)
    return facts


def test_write_mesh_roundtrips():
    verts = [(0, 0, 0), (10, 0, 0), (0, 0, 10), (10, 0, 10)]
    norms = [(0, 1, 0)] * 4
    uvs = [(0, 0), (1, 0), (0, 1), (1, 1)]
    tris = [0, 2, 1, 1, 2, 3]

    d = Path(tempfile.mkdtemp())
    write_mesh(d / "t.mesh", verts, norms, uvs, tris, "xxwater")

    facts = _parse((d / "t.mesh").read_bytes())
    assert facts["material"] == "xxwater"
    assert facts["skeletal"] == 0
    assert facts["shared"] == 0
    assert facts["indexes32"] == 0
    assert facts["indexCount"] == 6
    assert facts["vertexCount"] == 4


def test_index_out_of_range_rejected():
    import pytest
    with pytest.raises(ValueError):
        write_mesh("/tmp/bad.mesh", [(0, 0, 0)], [(0, 1, 0)], [(0, 0)], [0, 1, 2], "m")
