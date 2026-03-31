"""Test imports for CYJAX Threat Intelligence integration."""

from __future__ import annotations

from integration_testing.default_tests.import_test import import_all_integration_modules

from cyjax_threat_intelligence.tests import common


def test_imports() -> None:
    """Test that all integration modules can be imported successfully."""
    import_all_integration_modules(common.INTEGRATION_PATH)
