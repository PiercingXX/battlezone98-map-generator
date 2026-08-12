"""Tests for :mod:`bzmap.package.install` (docs/07 §"Local testing install").

The contract under test:

- A generated map is copied into a **separate** test mod dir
  ``<game root>/mods/<test-id>/`` — never into installed Workshop content. The module
  takes the game root as a parameter, so tests use a scratch ``tmp_path`` and
  no real game install is ever touched.
- ``modEnabled.dat`` is snapshotted before it is changed and restored
  afterwards, byte-for-byte (or removed if it did not exist).
"""

from bzmap.package.install import (
    InstallError,
    install_map,
    mod_dir,
    restore_mod_enabled,
    set_mod_enabled,
    snapshot_mod_enabled,
)


def _write_map_files(tmp_path):
    """Create a small generated map file set and return the source dir."""
    src = tmp_path / "build"
    src.mkdir()
    (src / "xx01ridg.trn").write_text("[Size]\nWidth = 2048\n", encoding="utf-8")
    (src / "xx01ridg.hg2").write_bytes(b"\x00\x01\x02")
    (src / "xx01ridg.bzn").write_text("[GameObject]\n", encoding="utf-8")
    return src


def test_install_into_separate_mod_dir(tmp_path):
    """Files land under mods/<test-id>/, never at the game root."""
    game = tmp_path / "game"
    src = _write_map_files(tmp_path)
    files = [src / "xx01ridg.trn", src / "xx01ridg.hg2", src / "xx01ridg.bzn"]

    dest = install_map(game, "test-001", files)

    assert dest == game / "mods" / "test-001"
    assert (dest / "xx01ridg.trn").read_text(encoding="utf-8").startswith("[Size]")
    assert (dest / "xx01ridg.hg2").read_bytes() == b"\x00\x01\x02"
    assert (dest / "xx01ridg.bzn").read_text(encoding="utf-8") == "[GameObject]\n"
    # Nothing was written into the workshop dir (there is none here), and the
    # mod dir is the only thing created under the game root besides mods/.
    assert (game / "mods").is_dir()
    assert list((game / "mods").iterdir()) == [dest]


def test_install_renames_dest_file(tmp_path):
    """A (source, dest_name) pair copies under an explicit destination name."""
    game = tmp_path / "game"
    src = _write_map_files(tmp_path)

    dest = install_map(game, "test-002", [(src / "xx01ridg.trn", "map.trn")])

    assert (dest / "map.trn").is_file()
    assert not (dest / "xx01ridg.trn").exists()


def test_install_creates_missing_source_error(tmp_path):
    """A missing source file raises InstallError instead of silently skipping."""
    game = tmp_path / "game"
    missing = tmp_path / "nope.trn"

    try:
        install_map(game, "test-003", [missing])
    except InstallError as exc:
        assert str(missing) in str(exc)
    else:
        raise AssertionError("expected InstallError for missing source")


def test_mod_dir_path(tmp_path):
    """mod_dir computes the test mod path without creating it."""
    game = tmp_path / "game"
    assert mod_dir(game, "abc") == game / "mods" / "abc"
    assert not mod_dir(game, "abc").exists()


def test_snapshot_restore_roundtrip(tmp_path):
    """modEnabled.dat bytes are restored verbatim after being changed."""
    game = tmp_path / "game"
    game.mkdir()
    (game / "modEnabled.dat").write_bytes(b"some-old-mod\x00\x01")

    snap = snapshot_mod_enabled(game)
    assert snap == b"some-old-mod\x00\x01"

    set_mod_enabled(game, "test-001")
    assert (game / "modEnabled.dat").read_text(encoding="ascii") == "test-001"

    restore_mod_enabled(game, snap)
    assert (game / "modEnabled.dat").read_bytes() == b"some-old-mod\x00\x01"


def test_snapshot_none_when_absent(tmp_path):
    """An absent modEnabled.dat snapshots to None and restore removes it."""
    game = tmp_path / "game"
    game.mkdir()

    assert snapshot_mod_enabled(game) is None

    set_mod_enabled(game, "test-001")
    assert (game / "modEnabled.dat").exists()

    restore_mod_enabled(game, None)
    assert not (game / "modEnabled.dat").exists()


def test_set_mod_enabled_returns_previous_snapshot(tmp_path):
    """set_mod_enabled returns the prior state for a finally-restore."""
    game = tmp_path / "game"
    game.mkdir()
    (game / "modEnabled.dat").write_text("old", encoding="ascii")

    previous = set_mod_enabled(game, "test-001")
    assert previous == b"old"

    restore_mod_enabled(game, previous)
    assert (game / "modEnabled.dat").read_text(encoding="ascii") == "old"