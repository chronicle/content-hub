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

import dataclasses
import json
import os
from typing import TYPE_CHECKING

import mp.core.unix
from mp.core.exceptions import NonFatalValidationError

if TYPE_CHECKING:
    from pathlib import Path


@dataclasses.dataclass(slots=True, frozen=True)
class TestConfigValidation:
    """Validate that tests/config.json exists and is well-formed."""

    name: str = "Test Config Validation"

    @staticmethod
    def run(validation_path: Path) -> None:
        """Check that tests/config.json exists and contains valid JSON.

        Args:
            validation_path: The path of the integration to validate.

        Raises:
            NonFatalValidationError: If config.json is missing or invalid.

        """
        head_sha: str | None = os.environ.get("GITHUB_PR_SHA")
        if head_sha:
            changed = mp.core.unix.get_files_unmerged_to_main_branch("main", head_sha, validation_path)
            if not changed:
                return

        tests_dir = validation_path / "tests"
        if not tests_dir.is_dir():
            return  # No tests directory — other validators handle this

        config_file = tests_dir / "config.json"
        if not config_file.exists():
            msg = f"'{validation_path.name}' is missing tests/config.json"
            raise NonFatalValidationError(msg)

        try:
            config = json.loads(config_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            msg = f"tests/config.json is not valid JSON: {e}"
            raise NonFatalValidationError(msg) from e

        if not isinstance(config, dict):
            msg = "tests/config.json must be a JSON object (dict)"
            raise NonFatalValidationError(msg)
