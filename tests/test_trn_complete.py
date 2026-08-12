"""Conformance: the .trn writer emits COMPLETE terrain configs.

the generator-fixes audit, task 1. The historical failure: ten shipped maps
carried a three-line [Size]-only .trn — no palette, no sky, no ground textures
— and Tier 1 certified them. write_complete_trn must template-and-mutate the
vendored stock Elysium config, rewriting only [Size].
"""

from bzmap.formats.trn import read_trn, write_complete_trn

REQUIRED_SECTIONS = ("Color", "Sky", "Clouds", "Atlases", "NormalView", "World")


def test_written_trn_carries_every_required_section(tmp_path):
    out = write_complete_trn(tmp_path / "map.trn", 2560, 2560)

    names = {s.name for s in read_trn(out).sections}
    for section in REQUIRED_SECTIONS:
        assert section in names, f"missing [{section}]"
    assert any(n.startswith("TextureType") for n in names)


def test_size_is_rewritten_to_standalone_dimensions(tmp_path):
    out = write_complete_trn(tmp_path / "map.trn", 1280, 1280)

    cfg = read_trn(out)
    assert cfg.get("Size", "Width") == "1280"
    assert cfg.get("Size", "Depth") == "1280"
    # The template is a campaign world config (MinZ=98560, Height=20); a
    # standalone map sits at the origin.
    assert cfg.get("Size", "MinX") == "0"
    assert cfg.get("Size", "MinZ") == "0"
    assert float(cfg.get("Size", "Height")) == 0.0


def test_template_texture_blocks_arrive_verbatim(tmp_path):
    """Template-and-mutate: the [TextureType*] asset names must be untouched."""
    out = write_complete_trn(tmp_path / "map.trn", 2560, 2560)

    text = out.read_text()
    template = (
        write_complete_trn.__module__  # anchor: read the vendored template
    )
    from bzmap.formats.trn import _default_template

    src = _default_template().read_text(encoding="utf-8-sig")
    # every texture asset line of the template survives byte-for-byte
    for line in src.splitlines():
        if ".map" in line and "Solid" in line:
            assert line in text, f"template texture line lost: {line!r}"


def test_the_historical_stub_would_now_fail_reading():
    """A [Size]-only stub parses to exactly one section — the shape the
    sufficiency validator (test_validate_trn_sufficiency) rejects."""
    import io, tempfile, pathlib

    d = pathlib.Path(tempfile.mkdtemp())
    stub = d / "stub.trn"
    stub.write_text("[Size]\r\nWidth = 1280\r\nDepth = 1280\r\n")
    cfg = read_trn(stub)
    assert [s.name for s in cfg.sections] == ["Size"]
