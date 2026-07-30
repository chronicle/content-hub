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

"""Module for comparing YAML metadata files for regression testing."""

from __future__ import annotations

import csv
import dataclasses
import pathlib  # ruff:ignore[typing-only-standard-library-import]
from typing import cast

import yaml

from .judge import TextCandidate, run_judge_evaluation_sync


@dataclasses.dataclass
class RegressionIssue:
    """Dataclass representing a regression issue found during comparison."""

    path_of_files: str
    baseline_file: str
    test_file: str
    entry: str
    issue: str
    llm_input: str


def compare_yaml_files(  # ruff:ignore[too-many-arguments]
    baseline_path: pathlib.Path,
    test_path: pathlib.Path,
    path_of_files: str | None = None,
    *,
    use_llm_judge: bool = False,
    use_batch_api: bool = False,
    target_entries: set[str] | None = None,
) -> list[RegressionIssue]:
    """Compare baseline and test YAML files and return a list of regression issues.

    Args:
        baseline_path: Path to the baseline YAML file.
        test_path: Path to the test YAML file.
        path_of_files: Display path of files (defaults to baseline_path relative path).
        use_llm_judge: Whether to use Gemini Judge to evaluate text field equivalence.
        use_batch_api: Whether to use Google GenAI Batch API for LLM Judge evaluation.
        target_entries: Optional set of top-level keys (e.g. action names) to restrict comparison to.

    Returns:
        list[RegressionIssue]: List of identified regression issues.

    """
    rel_path: str = path_of_files or str(baseline_path)

    if not baseline_path.exists():
        if test_path.exists():
            return [
                RegressionIssue(
                    path_of_files=rel_path,
                    baseline_file=str(baseline_path),
                    test_file=str(test_path),
                    entry="<file>",
                    issue="baseline file missing",
                    llm_input=f"Baseline file {baseline_path} does not exist",
                )
            ]
        return []

    if not test_path.exists():
        return [
            RegressionIssue(
                path_of_files=rel_path,
                baseline_file=str(baseline_path),
                test_file=str(test_path),
                entry="<file>",
                issue="test file missing",
                llm_input=f"Test file {test_path} does not exist",
            )
        ]

    try:
        with baseline_path.open("r", encoding="utf-8") as f:
            baseline_data: object = yaml.safe_load(f) or {}
    except Exception as e:  # ruff:ignore[blind-except]
        return [
            RegressionIssue(
                path_of_files=rel_path,
                baseline_file=str(baseline_path),
                test_file=str(test_path),
                entry="<file>",
                issue="failed to parse baseline yaml",
                llm_input=str(e),
            )
        ]

    try:
        with test_path.open("r", encoding="utf-8") as f:
            test_data: object = yaml.safe_load(f) or {}
    except Exception as e:  # ruff:ignore[blind-except]
        return [
            RegressionIssue(
                path_of_files=rel_path,
                baseline_file=str(baseline_path),
                test_file=str(test_path),
                entry="<file>",
                issue="failed to parse test yaml",
                llm_input=str(e),
            )
        ]

    if target_entries and isinstance(baseline_data, dict) and isinstance(test_data, dict):
        baseline_data = {k: v for k, v in baseline_data.items() if k in target_entries}
        test_data = {k: v for k, v in test_data.items() if k in target_entries}

    return compare_yaml_dicts(
        baseline_data=baseline_data,
        test_data=test_data,
        path_of_files=rel_path,
        baseline_file_str=str(baseline_path),
        test_file_str=str(test_path),
        use_llm_judge=use_llm_judge,
        use_batch_api=use_batch_api,
    )


def compare_yaml_dicts(  # ruff:ignore[complex-structure,too-many-arguments]
    baseline_data: object,
    test_data: object,
    path_of_files: str,
    baseline_file_str: str,
    test_file_str: str,
    *,
    use_llm_judge: bool = False,
    use_batch_api: bool = False,
) -> list[RegressionIssue]:
    """Recursively compare baseline and test dictionary structures.

    Args:
        baseline_data: Parsed baseline data structure.
        test_data: Parsed test data structure.
        path_of_files: Display path for files.
        baseline_file_str: Baseline file path string.
        test_file_str: Test file path string.
        use_llm_judge: Whether to use Gemini Judge to evaluate text field equivalence.
        use_batch_api: Whether to use Google GenAI Batch API for LLM Judge.

    Returns:
        list[RegressionIssue]: List of regression issues found.

    """
    issues: list[RegressionIssue] = []
    text_candidates: list[TextCandidate] = []

    def _recurse(  # ruff:ignore[complex-structure]
        b_val: object, t_val: object, key_path: list[str], parent_context: dict[str, object] | None
    ) -> None:
        entry_str: str = " -> ".join(key_path)

        # 1. Compare booleans
        if isinstance(b_val, bool) or isinstance(t_val, bool):
            if isinstance(b_val, bool) and isinstance(t_val, bool):
                if b_val is True and t_val is False:
                    reasoning_text: str = _extract_reasoning(parent_context)
                    issues.append(
                        RegressionIssue(
                            path_of_files=path_of_files,
                            baseline_file=baseline_file_str,
                            test_file=test_file_str,
                            entry=entry_str,
                            issue="marked as a regression for manual checking",
                            llm_input=reasoning_text or f"Baseline: {b_val} | Test: {t_val}",
                        )
                    )
                elif b_val is False and t_val is True:
                    reasoning_text = _extract_reasoning(parent_context)
                    issues.append(
                        RegressionIssue(
                            path_of_files=path_of_files,
                            baseline_file=baseline_file_str,
                            test_file=test_file_str,
                            entry=entry_str,
                            issue="might be a regression",
                            llm_input=reasoning_text or f"Baseline: {b_val} | Test: {t_val}",
                        )
                    )
            else:
                issues.append(
                    RegressionIssue(
                        path_of_files=path_of_files,
                        baseline_file=baseline_file_str,
                        test_file=test_file_str,
                        entry=entry_str,
                        issue="type mismatch (boolean vs non-boolean)",
                        llm_input=f"Baseline: {b_val} | Test: {t_val}",
                    )
                )
            return

        # 2. Compare dicts
        if isinstance(b_val, dict) and isinstance(t_val, dict):
            b_dict = cast("dict[str, object]", b_val)
            t_dict = cast("dict[str, object]", t_val)
            all_keys: set[str] = set(b_dict.keys()) | set(t_dict.keys())
            for k in sorted(all_keys):
                if k in b_dict and k in t_dict:
                    _recurse(b_dict[k], t_dict[k], [*key_path, k], b_dict)
                elif k in b_dict:
                    issue_msg = (
                        "marked as a regression for manual checking (action missing in test)"
                        if len(key_path) == 0
                        else "marked as a regression for manual checking (field missing in test)"
                    )
                    issues.append(
                        RegressionIssue(
                            path_of_files=path_of_files,
                            baseline_file=baseline_file_str,
                            test_file=test_file_str,
                            entry=" -> ".join([*key_path, k]),
                            issue=issue_msg,
                            llm_input=f"Baseline: {b_dict[k]} | Test: <missing>",
                        )
                    )
                elif len(key_path) == 0:
                    # New top-level action added in code that was missing in baseline
                    issues.append(
                        RegressionIssue(
                            path_of_files=path_of_files,
                            baseline_file=baseline_file_str,
                            test_file=test_file_str,
                            entry=k,
                            issue="action missing in baseline (needs mp describe)",
                            llm_input=f"Baseline: <missing> | Test: {t_dict[k]}",
                        )
                    )
            return

        # 3. Compare text fields using LLM as a Judge if requested
        if use_llm_judge and isinstance(b_val, str) and isinstance(t_val, str):
            if b_val != t_val and len(key_path) > 0 and key_path[-1] in {
                "ai_description",
                "ai_short_description",
                "parameters_description",
                "reasoning",
            }:
                text_candidates.append(
                    TextCandidate(
                        entry_path=entry_str,
                        baseline_text=b_val,
                        test_text=t_val,
                    )
                )
            return

    _recurse(baseline_data, test_data, [], None)

    if use_llm_judge and text_candidates:
        judge_results = run_judge_evaluation_sync(text_candidates, use_batch=use_batch_api)
        issues.extend(
            RegressionIssue(
                path_of_files=path_of_files,
                baseline_file=baseline_file_str,
                test_file=test_file_str,
                entry=res.entry_path,
                issue="text semantic mismatch (NOT_EQUIVALENT)",
                llm_input=f"Reasoning: {res.verdict.comparison_reasoning}",
            )
            for res in judge_results
            if res.verdict.verdict == "NOT_EQUIVALENT"
        )

    return issues


def _extract_reasoning(context: dict[str, object] | None) -> str:
    """Extract reasoning text from dictionary context if present.

    Args:
        context: Parent section dictionary context.

    Returns:
        str: Extracted reasoning text or empty string.

    """
    if not context or not isinstance(context, dict):
        return ""
    reasoning = context.get("reasoning")
    if reasoning:
        return str(reasoning)
    return ""


def write_regression_report_csv(issues: list[RegressionIssue], report_file: pathlib.Path) -> None:
    """Write list of regression issues to a CSV report file.

    Args:
        issues: List of regression issues.
        report_file: Destination CSV path.

    """
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with report_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Path_of_files", "BaselineFile", "TestFile", "Entry", "issue", "LLM Input"])
        for item in issues:
            writer.writerow([
                item.path_of_files,
                item.baseline_file,
                item.test_file,
                item.entry,
                item.issue,
                item.llm_input,
            ])
