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
import os
from typing import TYPE_CHECKING

import mp.core.unix
from mp.core import constants
from mp.core.exceptions import NonFatalValidationError

if TYPE_CHECKING:
    from pathlib import Path

# Patterns that indicate an action returns JSON results
_JSON_RESULT_PATTERNS = (
    "add_result_json",
    "self.json_results",
    "self.soar_action.json",
)


@dataclasses.dataclass(slots=True, frozen=True)
class JsonResultExampleValidation:
    """Validate that actions with JSON results have example files."""

    name: str = "JSON Result Example Validation"

    @staticmethod
    def run(validation_path: Path) -> None:
        """Check that each action returning JSON has a corresponding example.

        Scans action .py files for JSON result patterns and verifies that
        a matching *_JsonResult_example.json file exists in resources/.

        Args:
            validation_path: The path of the integration to validate.

        Raises:
            NonFatalValidationError: If a JSON result example is missing.

        """
        # Only validate integrations with changes in the current PR
        head_sha: str | None = os.environ.get("GITHUB_PR_SHA")
        changed_files: set[str] | None = None
        if head_sha:
            changed = mp.core.unix.get_files_unmerged_to_main_branch("main", head_sha, validation_path)
            if not changed:
                return
            changed_files = {p.name for p in changed}

        actions_dir = validation_path / constants.ACTIONS_DIR
        resources_dir = validation_path / "resources"

        if not actions_dir.is_dir() or not resources_dir.is_dir():
            return

        missing: list[str] = []

        for py_file in actions_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue

            # In PR context, only check actions that were actually changed
            if changed_files is not None and py_file.name not in changed_files:
                continue

            # Check only non-comment lines for JSON result patterns
            source_lines = py_file.read_text(encoding="utf-8").splitlines()
            code_content = "\n".join(line for line in source_lines if not line.strip().startswith("#"))
            has_json_result = any(pattern in code_content for pattern in _JSON_RESULT_PATTERNS)

            if has_json_result:
                action_name = py_file.stem
                expected = resources_dir / f"{action_name}_JsonResult_example.json"
                if not expected.exists():
                    missing.append(action_name)

        if missing:
            names = ", ".join(missing)
            msg = f"Actions with JSON results missing example files in resources/: {names}"
            raise NonFatalValidationError(msg)
