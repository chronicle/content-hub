# Copyright 2026 Google LLC
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
import pathlib

from google_cloud_asset_inventory.tests import common

VALID_PACKAGES = ("actions", "connectors", "core", "jobs")
VALID_SUFFIXES = (".py",)


def import_all_integration_modules(integration: pathlib.Path) -> None:
    """Import all runtime modules of the integration to verify valid syntax/imports."""
    if not integration.exists():
        msg = f"Cannot find integration {integration.name}"
        raise AssertionError(msg)

    for package in integration.iterdir():
        if not package.is_dir() or package.name not in VALID_PACKAGES:
            continue
        for module in package.iterdir():
            if not module.is_file() or module.suffix not in VALID_SUFFIXES:
                continue
            importlib.import_module(
                f"{integration.stem}.{package.stem}.{module.stem}"
            )


def test_imports() -> None:
    """Test that all integration modules import cleanly."""
    import_all_integration_modules(common.INTEGRATION_PATH)
