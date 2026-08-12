"""Vendor import tests.

Verify that the vendored Battlezone98Redux_WorldBuilder is present under
``third_party/`` and that its HG2/MAT/TRN format concerns are importable from
the toolchain.

The upstream repo is a single monolithic GUI file that imports ``tkinter`` at
module top level, which is unavailable in a headless venv. The toolchain imports
the format logic through the shim submodules exposed by the vendored package
(``HG2``, ``MAT``, ``TRN``), so this test asserts those shims resolve and that
the real format classes are reachable through them.
"""

import importlib
import importlib.util


def test_vendor_imports():
    """The vendored package and its HG2/MAT/TRN shims are importable."""
    wb = importlib.import_module("third_party.Battlezone98Redux_WorldBuilder")

    for name in ("HG2", "MAT", "TRN"):
        assert hasattr(wb, name), f"vendored package missing {name!r}"
        mod = getattr(wb, name)
        assert mod is not None

    # The shims re-export the real format classes from the vendored module.
    assert hasattr(wb.HG2, "BZMapFormat")
    assert hasattr(wb.MAT, "AutoPainter")
    assert hasattr(wb.TRN, "TRNParser")


def test_vendor_world_builder_present():
    """The upstream world_builder.py source file is vendored."""
    import third_party.Battlezone98Redux_WorldBuilder as wb

    src = importlib.util.find_spec(
        "third_party.Battlezone98Redux_WorldBuilder.world_builder"
    )
    assert src is not None
    assert wb.__file__ is not None