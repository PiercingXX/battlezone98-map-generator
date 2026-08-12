"""Tests for the ``bzmap generate`` CLI pipeline (docs/08).

The ``generate`` subcommand wires the full
layout→terrain→economy→spawns→variants pipeline for a seed and emits the four
variant object sets as deterministic JSON.  These tests verify:

- the pipeline runs end-to-end and produces the four variants;
- the layout graph passes its graph-level validation before terrain synthesis;
- **fixed-seed determinism** — the same seed reproduces byte-identical output
  twice, and a different seed produces different output;
- the CLI subcommand surfaces the same determinism through ``main()``.
"""

import json

from bzmap import cli


def test_generate_map_produces_four_variants():
    result = cli.generate_map(seed=42)
    assert result.layout_ok is True
    assert set(result.variants) == {"", "_S", "_ST", "_SW"}


def test_generate_map_layout_validates():
    # The pipeline must reject a bad layout before terrain synthesis; a valid
    # one must pass the graph-level rules (C1, C3, B2, E4, E5, B3).
    result = cli.generate_map(seed=7)
    assert result.layout_ok is True


def test_base_variant_has_player_and_14_spawns():
    result = cli.generate_map(seed=42)
    base = result.variants[""].objects
    prjids = [o.prjid for o in base]
    assert prjids.count("player") == 1
    assert prjids.count("pspwn_1") == 14


def test_strategy_variant_carries_economy():
    result = cli.generate_map(seed=42)
    s = result.variants["_S"].objects
    prjids = [o.prjid for o in s]
    assert "eggeizr1" in prjids
    assert any(p.startswith("npscr") for p in prjids)


def test_sw_variant_carries_depots():
    result = cli.generate_map(seed=42)
    sw = result.variants["_SW"].objects
    prjids = [o.prjid for o in sw]
    assert "abhang" in prjids
    assert "absupp" in prjids


def test_fixed_seed_is_byte_identical():
    a = cli.generate_map(seed=42).to_json()
    b = cli.generate_map(seed=42).to_json()
    assert a == b
    assert a.encode("utf-8") == b.encode("utf-8")


def test_different_seed_differs():
    a = cli.generate_map(seed=42).to_json()
    b = cli.generate_map(seed=99).to_json()
    assert a != b


def test_seed_is_deterministic_across_instances():
    # Two independent runs (fresh RNG) with the same seed must agree.
    a = cli.generate_map(seed=123).to_json()
    b = cli.generate_map(seed=123).to_json()
    assert a == b


def test_cli_generate_output_is_stable_json(tmp_path, capsys):
    out = tmp_path / "map.json"
    rc = cli.main(["generate", "--seed", "5", "-o", str(out)])
    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert set(data["variants"]) == {"", "_S", "_ST", "_SW"}
    assert data["seed"] == 5
    assert data["layout_ok"] is True


def test_cli_generate_stdout_matches_file(tmp_path, capsys):
    out = tmp_path / "map.json"
    cli.main(["generate", "--seed", "5", "-o", str(out)])
    file_text = out.read_text(encoding="utf-8").strip()
    # Clear the "wrote …" confirmation printed by the file-writing call.
    capsys.readouterr()
    cli.main(["generate", "--seed", "5"])
    captured = capsys.readouterr()
    assert captured.out.strip() == file_text