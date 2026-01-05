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

from typing import TYPE_CHECKING

import pytest

from mp.core.exceptions import FatalValidationError
from mp.validate.pre_build_validation.integrations.dependency_provider_validation import (
    DependencyProviderValidation,
)

if TYPE_CHECKING:
    from pathlib import Path


def _setup_invalid_dependency_provider(integration_path: Path) -> None:
    uv_lock_path = integration_path / "uv.lock"
    invalid_package_toml = """
[[package]]
name = "invalid-package"
version = "1.0.0"
source = { registry = "invalid-registry" }
"""
    with uv_lock_path.open("a") as f:
        f.write(invalid_package_toml)


class TestDependencyProviderValidation:
    validation_runner: DependencyProviderValidation = DependencyProviderValidation()

    def test_integration_with_pypi_success(self, temp_integration: Path) -> None:
        self.validation_runner.run(temp_integration)

    def test_invalid_dependency_provider_fail(self, temp_integration: Path) -> None:
        _setup_invalid_dependency_provider(temp_integration)

        with pytest.raises(FatalValidationError, match="Unsupported dependency provider"):
            self.validation_runner.run(temp_integration)
