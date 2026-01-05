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

import tomllib
from pathlib import Path
from typing import Any

from pydantic import dataclasses

from mp.core.exceptions import FatalValidationError

ALLOWED_DEPENDENCY_PROVIDER: set[str] = {"pypi"}
UV_INDEX: str = "[[tool.uv.index]] \n url = 'https://pypi.org/simple'\n default = true\n"


@dataclasses.dataclass(slots=True, frozen=True)
class DependencyProviderValidation:
    name: str = "Dependency Provider Validation"

    @staticmethod
    def run(integration_path: Path) -> None:
        """Run validation for dependency provider in the uv.lock file.

        Args:
            integration_path: The path to the integration directory.

        Raises:
            FatalValidationError: If the `uv.lock` file is not found, or if an
                unsupported dependency provider is found in `uv.lock`.

        """
        uv_lock_path: Path = integration_path / "uv.lock"

        if not uv_lock_path.exists():
            msg: str = f"uv.lock file not found at {uv_lock_path}"
            raise FatalValidationError(msg)

        with Path.open(uv_lock_path, "rb") as uv_lock_file:
            uv_lock_data: dict[str, dict[str, str]] = tomllib.load(uv_lock_file)

        packages: list[dict[str, Any]] = uv_lock_data.get("package", [])
        for pkg in packages:
            pkg_source: dict[str, str] = pkg.get("source")
            if not pkg_source:
                continue

            registry_url: str | None = pkg_source.get("registry")
            if not registry_url:
                continue
            is_valid = any(provider in registry_url for provider in ALLOWED_DEPENDENCY_PROVIDER)
            if not is_valid:
                pkg_name: str = pkg.get("name", "Unknown package")
                msg: str = (
                    f"Package '{pkg_name}' has an unsupported dependency provider "
                    f"from registry: {registry_url}. "
                    f"Only registries containing one of {list(ALLOWED_DEPENDENCY_PROVIDER)} "
                    "are allowed. "
                    "Please add the following to the integration's "
                    f"pyproject.toml file:\n{UV_INDEX}"
                )
                raise FatalValidationError(msg)
