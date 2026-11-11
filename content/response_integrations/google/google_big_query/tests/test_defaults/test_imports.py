from __future__ import annotations

from integration_testing.default_tests.import_test import import_all_integration_modules

from google_big_query.tests import common


def test_imports() -> None:
    import_all_integration_modules(common.INTEGRATION_PATH)
