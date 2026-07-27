from __future__ import annotations

import importlib
import pathlib

from .. import common


VALID_SUFFIXES = (".py",)


def import_all_integration_modules(integration: pathlib.Path) -> None:
    if not integration.exists():
        msg: str = f"Cannot find integration {integration.name}"
        raise AssertionError(msg)

    imports: list[str] = _get_integration_modules_import_strings(integration)
    for import_ in imports:
        importlib.import_module(import_)


def _get_integration_modules_import_strings(integration: pathlib.Path) -> list[str]:
    results: list[str] = []
    for package in integration.iterdir():
        if not package.is_dir():
            continue

        for module in package.iterdir():
            if not module.is_file() or module.suffix not in VALID_SUFFIXES:
                continue

            import_: str = _get_import_string(integration.stem, package.stem, module.stem)
            results.append(import_)

    return results


def _get_import_string(integration: str, package: str, module: str) -> str:
    return f"{integration}.{package}.{module}"


def test_imports() -> None:
    import_all_integration_modules(common.INTEGRATION_PATH)
