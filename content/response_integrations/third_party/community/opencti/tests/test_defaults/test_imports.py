from __future__ import annotations

from integration_testing.default_tests.import_test import import_all_integration_modules

from .. import conftest


def test_imports() -> None:
    import_all_integration_modules(conftest.INTEGRATION_PATH)
