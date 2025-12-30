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

import pathlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from mp.run_pre_build_tests.process_test_output import IntegrationTestResults, TestIssue


class MarkdownFormat:
    def __init__(self, test_results: list[IntegrationTestResults]) -> None:
        self.results: list[IntegrationTestResults] = test_results
        self._report_lines: list[str] = []

    def display(self) -> None:
        """Generate and saves the test report in Markdown format."""
        self._report_lines.append("")
        for integration_result in self.results:
            self._report_lines.append(f"<h2>🧩   {integration_result.integration_name}</h2>")
            self._report_lines.append("")
            self._format_summary_table(integration_result)

            self._format_issues("Failed Tests", integration_result.failed_tests_summary, "❌")
            self._format_issues("Skipped Tests", integration_result.skipped_tests_summary, "⏭️")

            self._report_lines.append("")
            self._report_lines.append("")
            self._report_lines.append("")

        report_content = "\n".join(self._report_lines)

        _save_report_file(report_content, output_filename="test_report.md")

    def _format_summary_table(self, result: IntegrationTestResults) -> None:
        self._report_lines.append("| ✅ Passed | ❌ Failed | ⏭️ Skipped |")
        self._report_lines.append("|:---------:|:--------:|:----------:|")
        self._report_lines.append(
            f"| {result.passed_tests} | {result.failed_tests} | {result.skipped_tests} |"
        )
        self._report_lines.append("")

    def _format_issues(self, title: str, issues: list[TestIssue], emoji: str) -> None:
        if not issues:
            return

        self._report_lines.append(f"### {emoji}   {title}")
        for issue in issues:
            self._report_lines.append("<details>")
            self._report_lines.append(f"<summary>{issue.test_name}</summary>\n")
            self._report_lines.append("```")
            self._report_lines.append(issue.stack_trace)
            self._report_lines.append("```")
            self._report_lines.append("</details>")

        self._report_lines.append("")


def _save_report_file(markdown_content_str: str, output_filename: str) -> None:
    output_dir: Path = pathlib.Path("./artifacts")
    output_dir.mkdir(exist_ok=True)
    report_path: Path = output_dir / output_filename
    report_path.write_text(markdown_content_str, encoding="utf-8")
