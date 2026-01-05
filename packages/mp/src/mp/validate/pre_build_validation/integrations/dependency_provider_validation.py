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
            FatalValidationError: If there are any SSL parameter validation errors
                in the integration's connectors.

        """
        uv_lock_path: Path = integration_path / "uv.lock"

        if not uv_lock_path.exists():
            msg: str = f"uv.lock file not found at {uv_lock_path}"
            raise FatalValidationError(msg)

        with Path.open(uv_lock_path, "rb") as uv_lock_file:
            uv_lock_data: dict[str, dict[str, str]] = tomllib.load(uv_lock_file)

        packages: list[Any] = uv_lock_data.get("package", [])
        for pkg in packages:
            pkg_source: str = pkg.get("source")
            if not pkg_source:
                continue
            pkg_registry: dict[str, str] = pkg_source.get("registry")
            if not pkg_registry:
                continue
            is_valid = any(provider in pkg_registry for provider in ALLOWED_DEPENDENCY_PROVIDER)
            if not is_valid:
                msg: str = (
                    f"Unsupported dependency provider: {pkg_registry}, "
                    f"Only {ALLOWED_DEPENDENCY_PROVIDER} are allowed. Please add {UV_INDEX}"
                    "to the integration pyproject.toml file"
                )
                raise FatalValidationError(msg)
