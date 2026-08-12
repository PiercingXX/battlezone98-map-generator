"""Round-trip gate test against an installed corpus pack (docs/06, Rule 4).

This is the gate for everything else (docs/05 "Testing"): every stock corpus
``.bzn`` must parse and re-emit **byte-identically** (128 files), and every
stock ``.HG2`` must round-trip byte-identically (36 files). It is run by the
operator against the installed pack — which is read-only reference data and is
never modified (AGENTS.md Rule 2).

The pack is not in the repo, so this test resolves it from ``CORPUS_PACK_DIR``
(env var) or the default Steam workshop path, and ``pytest.skip``s when it is
absent. The normal CI suite passes without the pack; the operator runs this
gate with the pack installed.

Any file that fails to round-trip is **quarantined**: a written explanation is
recorded under ``build/quarantine/`` (AGENTS.md: write output only into
``build/``) and the gate fails. A non-empty quarantine is a hard error — a
format regression must be fixed, not silently tolerated.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from bzmap.formats.bzn import read_bzn, write_bzn
from bzmap.formats.hg2 import read_hg2, write_hg2

# Expected corpus sizes (docs/06 §Tier 1, measured 2026-08-10). The corpus pack is actively
# maintained (R1 in docs/09) — if the pack grows, update these and re-measure.
EXPECTED_BZN = 128
EXPECTED_HG2 = 36

# Corpus pack location; not installed by default — set CORPUS_PACK_DIR.
_DEFAULT_PACK = None

# Where quarantine explanations are written.
_REPO_ROOT = Path(__file__).resolve().parent.parent
QUARANTINE_DIR = _REPO_ROOT / "build" / "quarantine"


def _pack_dir() -> Path:
    """Return the corpus pack directory, from ``CORPUS_PACK_DIR`` or the default."""
    env = os.environ.get("CORPUS_PACK_DIR")
    return Path(env) if env else None


@pytest.fixture(scope="module")
def pack_dir() -> Path:
    """The installed corpus pack directory; skip the gate when it is absent."""
    d = _pack_dir()
    if d is None or not d.is_dir():
        pytest.skip(
            f"corpus pack not found at {d}; set CORPUS_PACK_DIR to run the round-trip gate"
        )
    return d


def _files_with_suffix(pack_dir: Path, suffix: str):
    """Return the top-level pack files with ``suffix`` (case-insensitive)."""
    return [
        p
        for p in pack_dir.iterdir()
        if p.is_file() and p.suffix.lower() == suffix.lower()
    ]


def _roundtrip_bzn(path: Path, tmp_dir: Path) -> bool:
    """Return True when ``path`` re-emits byte-identically."""
    original = path.read_bytes()
    bzn = read_bzn(path)
    out = tmp_dir / path.name
    write_bzn(out, bzn)
    return out.read_bytes() == original


def _roundtrip_hg2(path: Path, tmp_dir: Path) -> bool:
    """Return True when ``path`` re-emits byte-identically."""
    original = path.read_bytes()
    hm = read_hg2(path)
    out = tmp_dir / path.name
    write_hg2(out, hm)
    return out.read_bytes() == original


def _roundtrip_files(files, roundtrip, tmp_dir):
    """Round-trip each file; return a list of ``(name, reason)`` failures."""
    failures = []
    for path in sorted(files):
        try:
            if not roundtrip(path, tmp_dir):
                failures.append((path.name, "bytes differ after round-trip"))
        except (ValueError, OSError, UnicodeDecodeError) as exc:
            # A parse/write error is a quarantine too — the file is not
            # round-trippable by our reader/writer.
            failures.append((path.name, f"{type(exc).__name__}: {exc}"))
    return failures


def _write_quarantine(kind: str, failures, tmp_dir) -> None:
    """Write a quarantine record for ``failures`` under build/quarantine/."""
    if not failures:
        return
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    record = QUARANTINE_DIR / f"{kind}-quarantine.txt"
    lines = [
        f"Round-trip gate: {len(failures)} {kind} file(s) failed to round-trip.",
        f"Temporary output written to: {tmp_dir}",
        "",
    ]
    for name, reason in failures:
        lines.append(f"{name}: {reason}")
    record.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_roundtrip_all_bzn(pack_dir, tmp_path):
    """Every stock corpus ``.bzn`` re-emits byte-identically (128 files)."""
    files = _files_with_suffix(pack_dir, ".bzn")
    assert len(files) == EXPECTED_BZN, (
        f"expected {EXPECTED_BZN} corpus .bzn files, found {len(files)}; "
        "if the pack changed, update EXPECTED_BZN and re-measure"
    )
    failures = _roundtrip_files(files, _roundtrip_bzn, tmp_path)
    _write_quarantine("bzn", failures, tmp_path)
    assert not failures, (
        f"{len(failures)} BZN file(s) failed to round-trip (see "
        f"build/quarantine/bzn-quarantine.txt): {failures}"
    )


def test_roundtrip_all_hg2(pack_dir, tmp_path):
    """Every stock ``.HG2`` round-trips byte-identically (36 files)."""
    files = _files_with_suffix(pack_dir, ".hg2")
    assert len(files) == EXPECTED_HG2, (
        f"expected {EXPECTED_HG2} corpus .HG2 files, found {len(files)}; "
        "if the pack changed, update EXPECTED_HG2 and re-measure"
    )
    failures = _roundtrip_files(files, _roundtrip_hg2, tmp_path)
    _write_quarantine("hg2", failures, tmp_path)
    assert not failures, (
        f"{len(failures)} HG2 file(s) failed to round-trip (see "
        f"build/quarantine/hg2-quarantine.txt): {failures}"
    )