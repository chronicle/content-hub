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

"""Unit tests for mp describe-regression-test tool."""

from __future__ import annotations

import csv
from typing import TYPE_CHECKING
from unittest import mock

import yaml
from typer.testing import CliRunner

from mp.describe.regression_test.comparator import (
    RegressionIssue,
    compare_yaml_dicts,
    compare_yaml_files,
    write_regression_report_csv,
)
from mp.describe.regression_test.judge import JudgeEvaluationResult, JudgeVerdict
from mp.describe.regression_test.orchestrator import format_integration_and_component, run_regression_test
from mp.describe.regression_test.typer_app import app as regression_app

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()


def test_compare_yaml_dicts_matching() -> None:
    baseline = {
        "Get Related Associations": {
            "ai_description": "General description",
            "capabilities": {
                "can_mutate_internal_data": True,
                "can_create_case_comments": False,
            },
        }
    }
    test = {
        "Get Related Associations": {
            "ai_description": "General description",
            "capabilities": {
                "can_mutate_internal_data": True,
                "can_create_case_comments": False,
            },
        }
    }

    issues = compare_yaml_dicts(
        baseline_data=baseline,
        test_data=test,
        path_of_files="actions_ai_description.yaml",
        baseline_file_str="baseline.yaml",
        test_file_str="test.yaml",
    )
    assert len(issues) == 0


def test_compare_yaml_dicts_true_to_false_regression() -> None:
    baseline = {
        "Action1": {
            "capabilities": {
                "can_mutate_internal_data": True,
                "reasoning": "Mutates entities in case",
            }
        }
    }
    test = {
        "Action1": {
            "capabilities": {
                "can_mutate_internal_data": False,
                "reasoning": "Does not mutate entities",
            }
        }
    }

    issues = compare_yaml_dicts(
        baseline_data=baseline,
        test_data=test,
        path_of_files="actions_ai_description.yaml",
        baseline_file_str="baseline.yaml",
        test_file_str="test.yaml",
    )

    reg_issues = [i for i in issues if i.issue == "marked as a regression for manual checking"]
    assert len(reg_issues) == 1
    assert reg_issues[0].entry == "Action1 -> capabilities -> can_mutate_internal_data"
    assert reg_issues[0].llm_input == "Mutates entities in case"


def test_compare_yaml_dicts_false_to_true_regression() -> None:
    baseline = {
        "Action1": {
            "capabilities": {
                "fetches_data": False,
            }
        }
    }
    test = {
        "Action1": {
            "capabilities": {
                "fetches_data": True,
            }
        }
    }

    issues = compare_yaml_dicts(
        baseline_data=baseline,
        test_data=test,
        path_of_files="actions_ai_description.yaml",
        baseline_file_str="baseline.yaml",
        test_file_str="test.yaml",
    )

    might_reg = [i for i in issues if i.issue == "might be a regression"]
    assert len(might_reg) == 1
    assert might_reg[0].entry == "Action1 -> capabilities -> fetches_data"


def test_compare_yaml_dicts_text_mismatch_ignored() -> None:
    baseline = {
        "Action1": {
            "ai_short_description": "Old short description",
        }
    }
    test = {
        "Action1": {
            "ai_short_description": "New short description",
        }
    }

    issues = compare_yaml_dicts(
        baseline_data=baseline,
        test_data=test,
        path_of_files="actions_ai_description.yaml",
        baseline_file_str="baseline.yaml",
        test_file_str="test.yaml",
    )

    assert len(issues) == 0


def test_compare_yaml_files_file_io(tmp_path: Path) -> None:
    b_file = tmp_path / "baseline.yaml"
    t_file = tmp_path / "test.yaml"

    b_content = {"Action1": {"capabilities": {"can_update_entities": True}}}
    t_content = {"Action1": {"capabilities": {"can_update_entities": False}}}

    b_file.write_text(yaml.safe_dump(b_content), encoding="utf-8")
    t_file.write_text(yaml.safe_dump(t_content), encoding="utf-8")

    issues = compare_yaml_files(b_file, t_file)
    assert len(issues) == 1
    assert issues[0].issue == "marked as a regression for manual checking"


def test_compare_yaml_files_with_target_entries(tmp_path: Path) -> None:
    b_file = tmp_path / "baseline.yaml"
    t_file = tmp_path / "test.yaml"

    b_content = {
        "Action1": {"capabilities": {"can_update_entities": True}},
        "Action2": {"capabilities": {"can_update_entities": True}},
    }
    t_content = {
        "Action1": {"capabilities": {"can_update_entities": False}},
        "Action2": {"capabilities": {"can_update_entities": False}},
    }

    b_file.write_text(yaml.safe_dump(b_content), encoding="utf-8")
    t_file.write_text(yaml.safe_dump(t_content), encoding="utf-8")

    issues_all = compare_yaml_files(b_file, t_file)
    assert len(issues_all) == 2

    issues_filtered = compare_yaml_files(b_file, t_file, target_entries={"Action1"})
    assert len(issues_filtered) == 1
    assert "Action1" in issues_filtered[0].entry


def test_write_regression_report_csv(tmp_path: Path) -> None:
    csv_file = tmp_path / "report.csv"
    issue = RegressionIssue(
        path_of_files="content/test/actions_ai_description.yaml",
        baseline_file="baseline.yaml",
        test_file="test.yaml",
        entry="Action1 -> capabilities -> fetches_data",
        issue="marked as a regression for manual checking",
        llm_input="Baseline: True | Test: False",
    )

    write_regression_report_csv([issue], csv_file)

    assert csv_file.exists()
    with csv_file.open("r", encoding="utf-8") as f:
        reader = list(csv.reader(f))
        assert len(reader) == 2
        assert reader[0] == ["Path_of_files", "BaselineFile", "TestFile", "Entry", "issue", "LLM Input"]
        assert reader[1][0] == "content/test/actions_ai_description.yaml"
        assert reader[1][4] == "marked as a regression for manual checking"


def test_run_regression_test_orchestration(tmp_path: Path) -> None:
    report_file = tmp_path / "custom_report.csv"
    dst_dir = tmp_path / "test_dst"

    int_dir = tmp_path / "my_integration" / "resources" / "ai"
    int_dir.mkdir(parents=True, exist_ok=True)
    baseline_yaml = int_dir / "actions_ai_description.yaml"
    b_data = {"Action1": {"capabilities": {"can_mutate_internal_data": True}}}
    baseline_yaml.write_text(yaml.safe_dump(b_data), encoding="utf-8")

    test_int_dir = dst_dir / "my_integration" / "resources" / "ai"
    test_int_dir.mkdir(parents=True, exist_ok=True)
    test_yaml = test_int_dir / "actions_ai_description.yaml"
    t_data = {"Action1": {"capabilities": {"can_mutate_internal_data": False}}}
    test_yaml.write_text(yaml.safe_dump(t_data), encoding="utf-8")

    with mock.patch(
        "mp.describe.regression_test.orchestrator.get_integration_path", return_value=tmp_path / "my_integration"
    ):
        issues = run_regression_test(
            content_type="action",
            integration="my_integration",
            dst=dst_dir,
            report_file=report_file,
            run_describe=False,
        )

    assert len(issues) == 1
    assert report_file.exists()


def test_run_regression_test_multiple_integrations(tmp_path: Path) -> None:
    report_file = tmp_path / "custom_report.csv"
    dst_dir = tmp_path / "test_dst"

    for int_name in ("int1", "int2"):
        int_dir = tmp_path / int_name / "resources" / "ai"
        int_dir.mkdir(parents=True, exist_ok=True)
        baseline_yaml = int_dir / "actions_ai_description.yaml"
        b_data = {"Action1": {"capabilities": {"can_mutate_internal_data": True}}}
        baseline_yaml.write_text(yaml.safe_dump(b_data), encoding="utf-8")

        test_int_dir = dst_dir / int_name / "resources" / "ai"
        test_int_dir.mkdir(parents=True, exist_ok=True)
        test_yaml = test_int_dir / "actions_ai_description.yaml"
        t_data = {"Action1": {"capabilities": {"can_mutate_internal_data": False}}}
        test_yaml.write_text(yaml.safe_dump(t_data), encoding="utf-8")

    def mock_get_int_path(name: str, **kwargs: object) -> Path:
        return tmp_path / name

    with mock.patch("mp.describe.regression_test.orchestrator.get_integration_path", side_effect=mock_get_int_path):
        issues = run_regression_test(
            content_type="action",
            integration="int1, int2",
            dst=dst_dir,
            report_file=report_file,
            run_describe=False,
        )

    assert len(issues) == 2
    assert report_file.exists()


def test_cli_describe_regression_test_action_command(tmp_path: Path) -> None:
    report_file = tmp_path / "report.csv"
    with mock.patch("mp.describe.regression_test.typer_app.run_regression_test") as mock_run:
        result = runner.invoke(
            regression_app,
            [
                "action",
                "-i",
                "anomali",
                "--report-file",
                str(report_file),
            ],
        )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    mock_run.assert_called_once_with(
        content_type="action",
        resource_names=None,
        integration="anomali",
        all_marketplace=False,
        src=None,
        dst=None,
        override=False,
        report_file=report_file,
        run_describe=True,
        use_llm_judge=False,
        use_batch_api=False,
    )


def test_cli_describe_regression_test_all_content_command(tmp_path: Path) -> None:
    report_file = tmp_path / "report.csv"
    with mock.patch("mp.describe.regression_test.typer_app.run_regression_test") as mock_run:
        result = runner.invoke(
            regression_app,
            [
                "all-content",
                "-a",
                "--report-file",
                str(report_file),
            ],
        )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    mock_run.assert_called_once_with(
        content_type="all-content",
        resource_names=None,
        all_marketplace=True,
        src=None,
        dst=None,
        override=False,
        report_file=report_file,
        run_describe=True,
        use_llm_judge=False,
        use_batch_api=False,
    )


def test_compare_yaml_dicts_with_llm_judge() -> None:
    baseline = {"ai_description": "First description text"}
    test_data = {"ai_description": "Contradictory new description text"}

    mock_verdict = JudgeVerdict(
        prompt_intent_analysis="Evaluate intent",
        field_1_core_claims=["Claim A"],
        field_2_core_claims=["Claim B"],
        missing_operational_facts=["Omitted rate limit"],
        comparison_reasoning="Contradictory information",
        verdict="NOT_EQUIVALENT",
        change_type="GENERATOR_REGRESSION",
    )
    mock_result = JudgeEvaluationResult(
        entry_path="ai_description",
        baseline_text=baseline["ai_description"],
        test_text=test_data["ai_description"],
        verdict=mock_verdict,
    )

    with mock.patch(
        "mp.describe.regression_test.comparator.run_judge_evaluation_sync",
        return_value=[mock_result],
    ) as mock_judge:
        issues = compare_yaml_dicts(
            baseline_data=baseline,
            test_data=test_data,
            path_of_files="base.yaml",
            baseline_file_str="base.yaml",
            test_file_str="test.yaml",
            use_llm_judge=True,
        )

    mock_judge.assert_called_once()
    assert len(issues) == 1
    assert issues[0].issue == "text semantic mismatch (GENERATOR_REGRESSION)"
    assert "Contradictory information" in issues[0].llm_input
    assert "Missing facts: Omitted rate limit" in issues[0].llm_input


def test_compare_yaml_dicts_reasoning_ignored_by_judge() -> None:
    baseline = {"reasoning": "Old classifier scratchpad reasoning"}
    test_data = {"reasoning": "New classifier scratchpad reasoning"}

    with mock.patch(
        "mp.describe.regression_test.comparator.run_judge_evaluation_sync"
    ) as mock_judge:
        issues = compare_yaml_dicts(
            baseline_data=baseline,
            test_data=test_data,
            path_of_files="base.yaml",
            baseline_file_str="base.yaml",
            test_file_str="test.yaml",
            use_llm_judge=True,
        )

    mock_judge.assert_not_called()
    assert len(issues) == 0


def test_cli_describe_regression_test_action_command_with_judge(tmp_path: Path) -> None:
    report_file = tmp_path / "report.csv"
    with mock.patch("mp.describe.regression_test.typer_app.run_regression_test") as mock_run:
        result = runner.invoke(
            regression_app,
            [
                "action",
                "-i",
                "anomali",
                "-j",
                "--report-file",
                str(report_file),
            ],
        )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    mock_run.assert_called_once_with(
        content_type="action",
        resource_names=None,
        integration="anomali",
        all_marketplace=False,
        src=None,
        dst=None,
        override=False,
        report_file=report_file,
        run_describe=True,
        use_llm_judge=True,
        use_batch_api=False,
    )


def test_cli_describe_regression_test_action_command_with_batch_api(tmp_path: Path) -> None:
    report_file = tmp_path / "report.csv"
    with mock.patch("mp.describe.regression_test.typer_app.run_regression_test") as mock_run:
        result = runner.invoke(
            regression_app,
            [
                "action",
                "-i",
                "anomali",
                "-j",
                "--use-batch-api",
                "--report-file",
                str(report_file),
            ],
        )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    mock_run.assert_called_once_with(
        content_type="action",
        resource_names=None,
        integration="anomali",
        all_marketplace=False,
        src=None,
        dst=None,
        override=False,
        report_file=report_file,
        run_describe=True,
        use_llm_judge=True,
        use_batch_api=True,
    )


def test_format_integration_and_component() -> None:
    path_action = (
        "/usr/local/google/home/siedovolosyi/repos/content-hub/content/"
        "response_integrations/third_party/community/duo/resources/ai/actions_ai_description.yaml"
    )
    int_name, comp_name = format_integration_and_component(path_action)
    assert int_name == "duo"
    assert comp_name == "action"

    path_conn = "/some/path/my_int/resources/ai/connectors_ai_description.yaml"
    int_name, comp_name = format_integration_and_component(path_conn)
    assert int_name == "my_int"
    assert comp_name == "connector"
