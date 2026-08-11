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

"""Unit tests for accept regression test functionality."""

from __future__ import annotations

from pathlib import Path  # ruff:ignore[typing-only-standard-library-import]

from typer.testing import CliRunner

from mp.describe.regression_test.accept import run_accept_regression_test
from mp.describe.typer_app import app


def test_run_accept_regression_test_success(tmp_path: Path) -> None:
    src_dir = tmp_path / "integrations"
    int_dir = src_dir / "test_int"
    baseline_ai_dir = int_dir / "resources" / "ai"
    baseline_ai_dir.mkdir(parents=True, exist_ok=True)

    baseline_yaml = baseline_ai_dir / "actions_ai_description.yaml"
    baseline_yaml.write_text("old_description: 'version 1'", encoding="utf-8")

    dst_dir = tmp_path / "test_descriptions"
    test_ai_dir = dst_dir / "test_int" / "resources" / "ai"
    test_ai_dir.mkdir(parents=True, exist_ok=True)

    test_yaml = test_ai_dir / "actions_ai_description.yaml"
    test_yaml.write_text("new_description: 'version 2'", encoding="utf-8")

    accepted = run_accept_regression_test(
        content_type="action",
        integration="test_int",
        src=src_dir,
        dst=dst_dir,
        dry_run=False,
    )

    assert len(accepted) == 1
    assert str(baseline_yaml) in accepted[0]
    assert baseline_yaml.read_text(encoding="utf-8") == "new_description: 'version 2'"
    assert not test_yaml.exists()


def test_run_accept_regression_test_dry_run(tmp_path: Path) -> None:
    src_dir = tmp_path / "integrations"
    int_dir = src_dir / "test_int"
    baseline_ai_dir = int_dir / "resources" / "ai"
    baseline_ai_dir.mkdir(parents=True, exist_ok=True)

    baseline_yaml = baseline_ai_dir / "actions_ai_description.yaml"
    baseline_yaml.write_text("old_description: 'version 1'", encoding="utf-8")

    dst_dir = tmp_path / "test_descriptions"
    test_ai_dir = dst_dir / "test_int" / "resources" / "ai"
    test_ai_dir.mkdir(parents=True, exist_ok=True)

    test_yaml = test_ai_dir / "actions_ai_description.yaml"
    test_yaml.write_text("new_description: 'version 2'", encoding="utf-8")

    accepted = run_accept_regression_test(
        content_type="action",
        integration="test_int",
        src=src_dir,
        dst=dst_dir,
        dry_run=True,
    )

    assert len(accepted) == 1
    assert baseline_yaml.read_text(encoding="utf-8") == "old_description: 'version 1'"
    assert test_yaml.exists()


def test_run_accept_regression_test_missing_candidate(tmp_path: Path) -> None:
    src_dir = tmp_path / "integrations"
    int_dir = src_dir / "test_int"
    baseline_ai_dir = int_dir / "resources" / "ai"
    baseline_ai_dir.mkdir(parents=True, exist_ok=True)

    baseline_yaml = baseline_ai_dir / "actions_ai_description.yaml"
    baseline_yaml.write_text("old_description: 'version 1'", encoding="utf-8")

    dst_dir = tmp_path / "test_descriptions"
    dst_dir.mkdir(parents=True, exist_ok=True)

    accepted = run_accept_regression_test(
        content_type="action",
        integration="test_int",
        src=src_dir,
        dst=dst_dir,
        dry_run=False,
    )

    assert accepted == []
    assert baseline_yaml.read_text(encoding="utf-8") == "old_description: 'version 1'"


def test_cli_describe_accept_command(tmp_path: Path) -> None:
    runner = CliRunner()
    src_dir = tmp_path / "integrations"
    int_dir = src_dir / "test_int"
    baseline_ai_dir = int_dir / "resources" / "ai"
    baseline_ai_dir.mkdir(parents=True, exist_ok=True)

    baseline_yaml = baseline_ai_dir / "actions_ai_description.yaml"
    baseline_yaml.write_text("old_description: 'version 1'", encoding="utf-8")

    dst_dir = tmp_path / "test_descriptions"
    test_ai_dir = dst_dir / "test_int" / "resources" / "ai"
    test_ai_dir.mkdir(parents=True, exist_ok=True)

    test_yaml = test_ai_dir / "actions_ai_description.yaml"
    test_yaml.write_text("new_description: 'version 2'", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "describe-accept",
            "action",
            "-i",
            "test_int",
            "--src",
            str(src_dir),
            "--dst",
            str(dst_dir),
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "Simulation complete." in result.stdout
    assert baseline_yaml.read_text(encoding="utf-8") == "old_description: 'version 1'"
