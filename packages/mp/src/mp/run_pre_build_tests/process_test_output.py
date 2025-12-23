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

import dataclasses
import json
import pathlib
from typing import TYPE_CHECKING, Any, NamedTuple

import rich

from mp.core.unix import NonFatalCommandError
from mp.validate.pre_build_validation.integrations.required_dependencies_validation import (
    RequiredDevDependenciesValidation,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestIssue(NamedTuple):
    test_name: str
    stack_trace: str


@dataclasses.dataclass(slots=True)
class IntegrationTestResults:
    integration_name: str
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    failed_tests_summary: list[TestIssue] = dataclasses.field(default_factory=list)
    skipped_tests_summary: list[TestIssue] = dataclasses.field(default_factory=list)


def process_pytest_json_report(
    integration_name: str,
    json_report_path: Path,
) -> IntegrationTestResults | None:
    """Process parsed JSON report data from pytest-json and return an IntegrationTestResults object.

    Args:
        integration_name: The name of the integration being tested.
        json_report_path: The path to the pytest JSON report file.

    Returns:
        An IntegrationTestResults object containing extracted information about
        test counts, and details of failed tests.

    """
    try:
        with pathlib.Path.open(json_report_path, encoding="utf-8") as f:
            report_data: dict[str, Any] = json.load(f)

        json_report_path.unlink(missing_ok=True)

    except FileNotFoundError:
        return _get_fnf_test_results(integration_name, json_report_path)

    except json.JSONDecodeError as e:
        rich.print(
            f"[bold red]Error:[/bold red] Failed to decode JSON report at {json_report_path}: {e}"
        )
        json_report_path.unlink(missing_ok=True)
        return None

    integration_results = IntegrationTestResults(integration_name=integration_name)

    summary: dict = report_data.get("summary", {})
    integration_results.skipped_tests = summary.get("skipped", 0)
    integration_results.passed_tests = summary.get("passed", 0)

    issue: TestIssue
    for test_item in report_data.get("tests", []):
        outcome = test_item.get("outcome")
        if outcome == "failed":
            issue = _extract_failed_test_issue(test_item)
            integration_results.failed_tests_summary.append(issue)
        elif outcome == "skipped":
            issue = _extract_skipped_test_issue(test_item)
            integration_results.skipped_tests_summary.append(issue)

    integration_results.failed_tests = len(integration_results.failed_tests_summary)

    return integration_results


def _extract_failed_test_issue(test_item: dict) -> TestIssue:
    test_name: str = test_item.get("nodeid", "N/A")
    call_info: dict[str, Any] = test_item.get("call", {})
    full_stack_trace: str = "No stack trace available"

    longrepr = call_info.get("longrepr")
    if isinstance(longrepr, str):
        full_stack_trace = longrepr

    elif isinstance(longrepr, dict):
        if "reprtraceback" in longrepr and "content" in longrepr["reprtraceback"]:
            full_stack_trace = longrepr["reprtraceback"]["content"]

        elif "sections" in longrepr:
            for section in longrepr["sections"]:
                if section[0].startswith("____ "):
                    full_stack_trace = section[1]
                    break

    return TestIssue(test_name=test_name, stack_trace=full_stack_trace)


def _extract_skipped_test_issue(test_item: dict) -> TestIssue:
    test_name: str = test_item.get("nodeid", "N/A")
    skip_reason: str = test_item.get("was_skipped", "Unknown reason").strip()

    if not skip_reason or skip_reason == "Unknown reason":
        call_info: dict[str, Any] = test_item.get("call", {})
        longrepr: str = call_info.get("longrepr")
        if isinstance(longrepr, str):
            skip_reason = longrepr.splitlines()[0] if longrepr else "No specific reason found."

        elif isinstance(longrepr, dict) and "reprcrash" in longrepr:
            skip_reason = longrepr["reprcrash"].get("message", "No specific reason found.")

        elif isinstance(longrepr, dict) and "sections" in longrepr:
            for section in longrepr["sections"]:
                if "skip" in section[0].lower() or "skipped" in section[0].lower():
                    skip_reason = section[1].splitlines()[0] if section[1] else skip_reason
                    break

    return TestIssue(test_name=test_name, stack_trace=skip_reason)


def _get_fnf_test_results(
    integration_name: str,
    json_report_path: Path,
) -> IntegrationTestResults | None:
    rich.print(f"[bold red]Error:[/bold red] JSON report not found at {json_report_path}")
    try:
        RequiredDevDependenciesValidation.run(json_report_path.parent)
    except NonFatalCommandError as e:
        error_msg: str = f"{e}"
        result: IntegrationTestResults = IntegrationTestResults(integration_name=integration_name)
        result.failed_tests_summary.append(
            TestIssue(test_name="Missing Dependencies", stack_trace=error_msg)
        )
        result.failed_tests += 1
        return result

    return None
