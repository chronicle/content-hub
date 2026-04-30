from __future__ import annotations

from integration_testing.default_tests.import_test import import_all_integration_modules

from .. import common


def test_imports() -> None:
    """Smoke test: verify all integration modules can be imported without error."""
    import_all_integration_modules(common.INTEGRATION_PATH)
