# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pathlib

VALID_SUFFIXES = (".py",)


def import_all_integration_modules(integration: pathlib.Path) -> None:
    """Import all integration components, asserting they managed to be imported.

    Args:
        integration: The path to the integration

    """
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
