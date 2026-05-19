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
import typer

from mp.core.file_utils.common.file_utils import validate_safe_path

if TYPE_CHECKING:
    from pathlib import Path


def test_validate_safe_path_valid(tmp_path: Path) -> None:
    base_path: Path = tmp_path / "integration_dir"
    base_path.mkdir()

    # Valid relative paths
    validate_safe_path(base_path, "example.json")
    validate_safe_path(base_path, "subdir/example.json")


def test_validate_safe_path_absolute_path(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    base_path: Path = tmp_path / "integration_dir"
    base_path.mkdir()

    absolute_path: str = "/etc/passwd"

    with pytest.raises(typer.Exit) as exc_info:
        validate_safe_path(base_path, absolute_path)

    assert exc_info.value.exit_code == 1
    assert "Path traversal detected" in caplog.text
    assert "is an absolute path" in caplog.text


def test_validate_safe_path_traversal(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    base_path: Path = tmp_path / "integration_dir"
    base_path.mkdir()

    traversal_path: str = "../other_integration/example.json"

    with pytest.raises(typer.Exit) as exc_info:
        validate_safe_path(base_path, traversal_path)

    assert exc_info.value.exit_code == 1
    assert "Path traversal detected" in caplog.text
    assert "attempts to escape the base directory" in caplog.text


def test_validate_safe_path_traversal_trick(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    base_path: Path = tmp_path / "integration_dir"
    base_path.mkdir()

    traversal_path: str = "subdir/../../other_integration/example.json"

    with pytest.raises(typer.Exit) as exc_info:
        validate_safe_path(base_path, traversal_path)

    assert exc_info.value.exit_code == 1
    assert "Path traversal detected" in caplog.text
    assert "attempts to escape the base directory" in caplog.text
