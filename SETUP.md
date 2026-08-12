# Local setup — before the tests run

The toolchain is pure-Python but two things are intentionally NOT in git:

1. **`.venv/`** — `python3 -m venv .venv && .venv/bin/pip install -e .`
   (deps: numpy, scipy, Pillow, imageio; dev adds pytest).
2. **`third_party/Battlezone98Redux_WorldBuilder/`** — the vendored WorldBuilder
   format reference. It is foreign-licensed and gitignored by deliberate
   decision (this repo does not redistribute it). Vendor it locally before
   running `tests/test_vendor.py`; those tests are setup-gated, like the venv.

With the venv but WITHOUT `third_party/`: `.venv/bin/pytest -q tests/` →
**323 passed, 3 failed, 3 skipped** (measured 2026-08-12). The 3 failures are
expected in that setup: two `test_vendor.py` gates that need the vendored
WorldBuilder, and one pre-existing `test_assemble.py` failure
(`test_assemble_flattens_all_map_files`), tracked as a known packaging-test
bug. With `third_party/` vendored the vendor gates pass as well.
