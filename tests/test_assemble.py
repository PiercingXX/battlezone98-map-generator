"""Tests for :mod:`bzmap.package.assemble` (docs/07 §"Pack layout").

The contract under test: a set of generated, already-validated per-map files is
flattened into ``build/Expansion-Pack/`` — every file at the item root, no
subdirectories (BZ98R workshop items are flat) — plus a single top-level
``preview.png`` workshop thumbnail. The pack is written into ``build/`` per
AGENTS.md rule 2; tests use a scratch ``tmp_path`` so no real pack is touched.
"""

from PIL import Image

from bzmap.package.assemble import (
    MAP_SUFFIXES,
    PREVIEW_SIZE,
    AssembleError,
    assemble_pack,
)


def _stage_map_files(tmp_path, terrain="xx01ridg"):
    """Create a small generated map file set and return the staging dir.

    Mirrors the docs/07 pack layout for one map: terrain files, the base and
    variant BZNs, mission/metadata files, and the per-map thumbnails.
    """
    src = tmp_path / "staging"
    src.mkdir(exist_ok=True)
    for suffix in (".trn", ".hg2", ".mat", ".lgt", ".vxt"):
        (src / f"{terrain}{suffix}").write_bytes(b"terrain")
    (src / f"{terrain}.bzn").write_bytes(b"base")
    (src / f"{terrain}_S.bzn").write_bytes(b"s")
    (src / f"{terrain}_ST.bzn").write_bytes(b"st")
    (src / f"{terrain}_SW.bzn").write_bytes(b"sw")
    for suffix in (".ini", ".des", ".odf", ".lua"):
        (src / f"{terrain}{suffix}").write_bytes(b"meta")
    (src / f"{terrain}.png").write_bytes(b"png")
    (src / f"{terrain}.bmp").write_bytes(b"bmp")
    return src


def test_assemble_flattens_all_map_files(tmp_path):
    """Every per-map file lands flat at the pack root, nothing nested."""
    src = _stage_map_files(tmp_path)
    pack = assemble_pack(src, tmp_path / "build" / "Expansion-Pack",
                         preview=Image.new("RGB", PREVIEW_SIZE))

    names = sorted(p.name for p in pack.iterdir())
    expected = sorted(
        [f"xx01ridg{s}" for s in MAP_SUFFIXES]
        + ["xx01ridg_S.bzn", "xx01ridg_ST.bzn", "xx01ridg_SW.bzn"]
        + ["preview.png"]
    )
    assert names == expected
    # Flat: no subdirectories in the pack.
    assert not any(p.is_dir() for p in pack.iterdir())


def test_assemble_copies_bytes_verbatim(tmp_path):
    """Copied map files are byte-identical to the staged sources."""
    src = _stage_map_files(tmp_path)
    pack = assemble_pack(src, tmp_path / "pack",
                         preview=Image.new("RGB", PREVIEW_SIZE))
    assert (pack / "xx01ridg.hg2").read_bytes() == b"terrain"
    assert (pack / "xx01ridg_SW.bzn").read_bytes() == b"sw"
    assert (pack / "xx01ridg.des").read_bytes() == b"meta"


def test_assemble_writes_preview_from_image(tmp_path):
    """A supplied PIL image becomes the top-level preview.png."""
    src = _stage_map_files(tmp_path)
    img = Image.new("RGB", (64, 64), (10, 20, 30))
    pack = assemble_pack(src, tmp_path / "pack", preview=img)
    with Image.open(pack / "preview.png") as im:
        assert im.format == "PNG"
        assert im.size == PREVIEW_SIZE


def test_assemble_copies_staged_preview(tmp_path):
    """Without a PIL image, a staged preview.png is copied as the thumbnail."""
    src = _stage_map_files(tmp_path)
    (src / "preview.png").write_bytes(b"staged-preview")
    pack = assemble_pack(src, tmp_path / "pack")
    assert (pack / "preview.png").read_bytes() == b"staged-preview"


def test_assemble_raises_when_no_preview(tmp_path):
    """No preview image and no staged preview.png is an error."""
    src = _stage_map_files(tmp_path)
    try:
        assemble_pack(src, tmp_path / "pack")
    except AssembleError as exc:
        assert "preview" in str(exc)
    else:
        raise AssertionError("expected AssembleError for missing preview")


def test_assemble_raises_when_no_map_files(tmp_path):
    """A staging dir with no map files is an error, even with a preview."""
    src = tmp_path / "empty"
    src.mkdir()
    try:
        assemble_pack(src, tmp_path / "pack",
                      preview=Image.new("RGB", PREVIEW_SIZE))
    except AssembleError as exc:
        assert "no map files" in str(exc)
    else:
        raise AssertionError("expected AssembleError for empty staging dir")


def test_assemble_ignores_non_map_files(tmp_path):
    """report.json and other non-map files are not copied into the pack."""
    src = _stage_map_files(tmp_path)
    (src / "report.json").write_bytes(b"{}")
    pack = assemble_pack(src, tmp_path / "pack",
                         preview=Image.new("RGB", PREVIEW_SIZE))
    assert not (pack / "report.json").exists()


def test_assemble_multiple_maps(tmp_path):
    """Two staged maps both land flat in the same pack."""
    src = _stage_map_files(tmp_path, terrain="xx01ridg")
    _stage_map_files(tmp_path, terrain="xx02cany")
    pack = assemble_pack(src, tmp_path / "pack",
                         preview=Image.new("RGB", PREVIEW_SIZE))
    names = sorted(p.name for p in pack.iterdir())
    assert "xx01ridg.trn" in names
    assert "xx02cany.trn" in names
    assert "xx02cany_SW.bzn" in names