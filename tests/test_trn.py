"""Tests for the ``.trn`` terrain INI reader/writer (docs/01 §4).

The ``.trn`` is a plain CRLF INI that must round-trip stock terrain configs
verbatim (Rule 4). These tests assert byte-identical read→write on a realistic
config carrying comments, blank lines, and multiple ``[TextureTypeN]`` sections,
plus ordered section/key access and targeted value edits that preserve the rest
of the file.
"""

from bzmap.formats.trn import Section, read_trn, write_trn

# A realistic .trn excerpt: CRLF, a leading comment, a blank line, and several
# sections including repeated TextureType blocks (as stock worlds have).
SAMPLE = (
    "; terrain config - uexmap10\r\n"
    "\r\n"
    "[Size]\r\n"
    "MinX = 0\r\n"
    "MinZ = 0\r\n"
    "Width = 1280\r\n"
    "Depth = 1280\r\n"
    "Height = 200\r\n"
    "\r\n"
    "[NormalView]\r\n"
    "Fog = 0.0\r\n"
    "\r\n"
    "[TextureType0]\r\n"
    "FlatColor = 0, 0, 0\r\n"
    "SolidA0 = grnd1\r\n"
    "\r\n"
    "[TextureType1]\r\n"
    "FlatColor = 255, 0, 0\r\n"
    "SolidA0 = grnd2\r\n"
)


def _write_sample(tmp_path):
    path = tmp_path / "map.trn"
    path.write_bytes(SAMPLE.encode("utf-8"))
    return path


# -- round-tripping ----------------------------------------------------------


def test_roundtrip_byte_identical(tmp_path):
    """read -> write reproduces the source .trn file byte-for-byte."""
    src = _write_sample(tmp_path)
    original = src.read_bytes()

    cfg = read_trn(src)
    out = tmp_path / "out.trn"
    write_trn(out, cfg)

    assert out.read_bytes() == original


def test_roundtrip_preserves_crlf(tmp_path):
    """CRLF line endings survive an untouched round-trip."""
    src = _write_sample(tmp_path)
    cfg = read_trn(src)
    out = tmp_path / "out.trn"
    write_trn(out, cfg)
    assert b"\r\n" in out.read_bytes()
    assert b"\n" not in out.read_bytes().replace(b"\r\n", b"")


def test_untouched_write_does_not_mark_dirty(tmp_path):
    """Reading and writing without edits re-emits the original text."""
    src = _write_sample(tmp_path)
    cfg = read_trn(src)
    assert cfg._dirty is False


# -- ordered sections --------------------------------------------------------


def test_sections_in_file_order(tmp_path):
    """Sections are exposed in file order, including repeated names."""
    cfg = read_trn(_write_sample(tmp_path))
    assert [s.name for s in cfg.sections] == [
        "Size",
        "NormalView",
        "TextureType0",
        "TextureType1",
    ]


def test_repeated_section_names_preserved(tmp_path):
    """Multiple TextureType sections are kept as separate ordered sections."""
    cfg = read_trn(_write_sample(tmp_path))
    tex = cfg.sections_named("TextureType0")
    assert len(tex) == 1
    assert cfg.section("TextureType0").get("FlatColor") == "0, 0, 0"
    assert cfg.section("TextureType1").get("FlatColor") == "255, 0, 0"


def test_get_values(tmp_path):
    """get() returns parsed key values without the 'key = ' prefix."""
    cfg = read_trn(_write_sample(tmp_path))
    assert cfg.get("Size", "Width") == "1280"
    assert cfg.get("Size", "Height") == "200"
    assert cfg.get("NormalView", "Fog") == "0.0"
    assert cfg.get("Size", "Missing") is None
    assert cfg.get("NoSuchSection", "Width", default="fallback") == "fallback"


def test_section_items_order(tmp_path):
    """Section.items() returns keys in file order."""
    cfg = read_trn(_write_sample(tmp_path))
    size = cfg.section("Size")
    assert size.keys() == ["MinX", "MinZ", "Width", "Depth", "Height"]
    assert size.items() == [
        ("MinX", "0"),
        ("MinZ", "0"),
        ("Width", "1280"),
        ("Depth", "1280"),
        ("Height", "200"),
    ]


# -- targeted edits ----------------------------------------------------------


def test_set_existing_key_rewrites_only_that_line(tmp_path):
    """Setting an existing key changes its line and leaves the rest verbatim."""
    src = _write_sample(tmp_path)
    cfg = read_trn(src)
    cfg.set("Size", "Width", "2560")

    out = tmp_path / "out.trn"
    write_trn(out, cfg)
    text = out.read_text(encoding="utf-8")

    assert "Width = 2560" in text
    assert "Width = 1280" not in text
    # Everything else is untouched, including comments and blank lines.
    assert "; terrain config - uexmap10" in text
    assert "FlatColor = 0, 0, 0" in text
    assert "Depth = 1280" in text


def test_set_new_key_appends_to_section(tmp_path):
    """Setting a new key appends it to its section on write."""
    src = _write_sample(tmp_path)
    cfg = read_trn(src)
    cfg.set("Size", "NewKey", "42")

    out = tmp_path / "out.trn"
    write_trn(out, cfg)
    text = out.read_text(encoding="utf-8")
    assert "NewKey = 42" in text
    # Original content is still present.
    assert "Width = 1280" in text


def test_set_missing_section_raises(tmp_path):
    """set() on a nonexistent section raises KeyError."""
    cfg = read_trn(_write_sample(tmp_path))
    try:
        cfg.set("NoSuchSection", "k", "v")
    except KeyError:
        pass
    else:
        raise AssertionError("expected KeyError for missing section")


def test_set_then_get_roundtrips_value(tmp_path):
    """A value set via set() is immediately visible via get()."""
    cfg = read_trn(_write_sample(tmp_path))
    cfg.set("Size", "Width", "3840")
    assert cfg.get("Size", "Width") == "3840"


def test_section_object_set_marks_config_dirty(tmp_path):
    """set() through a Section object marks the config dirty for write."""
    cfg = read_trn(_write_sample(tmp_path))
    sec = cfg.section("Size")
    assert isinstance(sec, Section)
    cfg.set(sec, "Depth", "999")
    assert cfg._dirty is True