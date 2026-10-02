from __future__ import annotations

from integration_testing.default_tests.import_test import import_all_integration_modules

from .. import common


def test_imports() -> None:
    """Import all integration modules to validate there are no import errors."""
    import_all_integration_modules(common.INTEGRATION_PATH)
