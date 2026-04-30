from __future__ import annotations

from integration_testing.default_tests.import_test import (  # type: ignore[import-not-found]
    import_all_integration_modules,
)

from .. import common


def test_imports() -> None:
    import_all_integration_modules(common.INTEGRATION_PATH)
