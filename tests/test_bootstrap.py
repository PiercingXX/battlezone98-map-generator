"""Bootstrap smoke tests.

Verify the workspace is set up so the rest of the suite can run: the ``bzmap``
package is importable from the checkout, and the third-party dependencies the
toolchain relies on (numpy, scipy, Pillow, imageio) resolve in the venv.
"""

import importlib


def test_bzmap_package_importable():
    import bzmap

    assert bzmap.__version__


def test_required_dependencies_importable():
    for name in ("numpy", "scipy", "PIL", "imageio"):
        assert importlib.import_module(name) is not None, name