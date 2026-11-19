from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from microsoft_intune.tests import common

if TYPE_CHECKING:
    import pathlib

VALID_PACKAGES = ("actions", "connectors", "core", "jobs")
VALID_SUFFIXES = (".py",)


def import_all_integration_modules(integration: pathlib.Path) -> None:
    """Import all Python modules across integration packages to verify import health."""
    if not integration.exists():
        msg = f"Cannot find integration {integration.name}"
        raise AssertionError(msg)

    for import_name in _get_integration_modules_import_strings(integration):
        importlib.import_module(import_name)


def _get_integration_modules_import_strings(integration: pathlib.Path) -> list[str]:
    results: list[str] = []
    for package in integration.iterdir():
        if not package.is_dir() or package.name not in VALID_PACKAGES:
            continue

        for module in package.iterdir():
            if not module.is_file() or module.suffix not in VALID_SUFFIXES or module.stem == "__init__":
                continue

            results.append(f"{integration.stem}.{package.stem}.{module.stem}")

    return results


def test_imports() -> None:
    """Verify all Microsoft Intune integration modules import cleanly."""
    import_all_integration_modules(common.INTEGRATION_PATH)
