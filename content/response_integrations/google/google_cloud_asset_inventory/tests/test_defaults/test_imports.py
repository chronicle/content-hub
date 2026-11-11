from __future__ import annotations

from integration_testing.default_tests.import_test import import_all_integration_modules

from google_cloud_asset_inventory.tests import common


def test_imports() -> None:
    import_all_integration_modules(common.INTEGRATION_PATH)
