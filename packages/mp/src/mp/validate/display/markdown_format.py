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

import itertools
import pathlib
from typing import TYPE_CHECKING

from rich.console import Console

from .constants import ICON_MAP

if TYPE_CHECKING:
    from pathlib import Path

    from mp.validate.data_models import ContentType, FullReport, ValidationReport, ValidationResults


class MarkdownFormat:
    def __init__(self, validation_results: dict[ContentType, FullReport]) -> None:
        self.validation_results = validation_results
        self.console: Console = Console()

    def display(self) -> None:
        """Generate a Markdown file with validation report tables."""
        try:
            markdown_content_list: list[str] = ["# Validation Report\n\n"]

            for content_type, full_report in self.validation_results.items():
                if not _has_issues_to_display(full_report):
                    continue

                icon = ICON_MAP[content_type.value]

                summary_header = f"<summary><strong>{icon} {content_type.value}s</strong></summary>"
                markdown_content_list.append(f"<details>\n{summary_header}\n\n")

                for stage_name, results_list in full_report.items():
                    markdown_content_list.extend(_generate_stage_content(stage_name, results_list))

                markdown_content_list.append("</details>\n\n")

            markdown_content: str = "".join(markdown_content_list)
            _save_report_file(markdown_content, output_filename="validation_report.md")

        except Exception as e:  # noqa: BLE001
            self.console.print(f"❌ Error generating report: {e}")


def _has_issues_to_display(full_report: FullReport) -> bool:
    return any(_should_display_stage(results_list) for results_list in full_report.values())


def _should_display_stage(results_list: list[ValidationResults] | None) -> bool:
    if not results_list:
        return False

    for validation_result in results_list:
        report: ValidationReport = validation_result.validation_report
        if report.failed_fatal_validations or report.failed_non_fatal_validations:
            return True

    return False


def _generate_stage_content(
    stage_name: str, results_list: list[ValidationResults] | None
) -> list[str]:
    content: list[str] = []
    if not _should_display_stage(results_list):
        return content

    content.append(f"<details>\n<summary>{stage_name} Stage</summary>\n\n")

    if results_list:
        for validation_result in results_list:
            table_data = _get_integration_validation_data(validation_result)

            if table_data:
                content.extend(
                    _format_table(table_data, validation_result.validation_report.content_name)
                )

    content.append("</details>\n\n")
    return content


def _get_integration_validation_data(validation_result: ValidationResults) -> list[list[str]]:
    return [
        [f"⚠️ {issue.validation_name}", issue.info]
        for issue in itertools.chain(
            validation_result.validation_report.failed_fatal_validations,
            validation_result.validation_report.failed_non_fatal_validations,
        )
    ]


def _format_table(table_data: list[list[str]], integration_name: str) -> list[str]:
    markdown_lines: list[str] = [f"#### {integration_name}\n\n"]

    headers: list[str] = ["Validation Name", "Details"]
    markdown_lines.extend([
        "| " + " | ".join(headers) + " |\n",
        "|" + "---|".join(["-" * len(h) for h in headers]) + "|\n",
    ])

    for validation_name, validation_details in table_data:
        formated_details: str = validation_details.replace("\n", " ").replace("|", "\\|")
        markdown_lines.append(f"| {validation_name} | {formated_details} |\n")

    markdown_lines.append("\n")
    return markdown_lines


def _save_report_file(markdown_content_str: str, output_filename: str) -> None:
    output_dir: Path = pathlib.Path("./artifacts")
    output_dir.mkdir(exist_ok=True)
    report_path: Path = output_dir / output_filename
    report_path.write_text(markdown_content_str, encoding="utf-8")
