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

import datetime
import pathlib
import tempfile
import webbrowser
from typing import TYPE_CHECKING, Any, NamedTuple

import jinja2
from rich.console import Console

if TYPE_CHECKING:
    from pathlib import Path

    from mp.validate.data_models import ContentType, FullReport


class ReportStatistics(NamedTuple):
    groups_data: dict[str, Any]
    total_items: int
    total_fatal: int
    total_warn: int


class HtmlFormat:
    def __init__(self, validation_results: dict[ContentType, FullReport]) -> None:
        self.validation_results: dict[ContentType, FullReport] = validation_results
        self.console: Console = Console()

    def display(self) -> None:
        """Generate an HTML report for validation results."""
        try:
            html_content: str = self._generate_validation_report_html()

            temp_report_path: Path
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".html", encoding="utf-8"
            ) as temp_file:
                temp_file.write(html_content)
                temp_report_path: Path = pathlib.Path(temp_file.name)

            resolved_temp_path: Path = temp_report_path.resolve()
            self.console.print(f"📂 Report available at 👉: {resolved_temp_path.as_uri()}")
            webbrowser.open(resolved_temp_path.as_uri())

        except Exception as e:  # noqa: BLE001
            self.console.print(f"❌  Error generating report: {e.args}")

    def _generate_validation_report_html(
        self, template_name: str = "html_report/report.html"
    ) -> str:
        template_dir = pathlib.Path(__file__).parent.resolve() / "templates"
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            autoescape=jinja2.select_autoescape(["html"]),
        )

        report_statistics: ReportStatistics = self._get_report_statistics()

        return env.get_template(template_name).render(
            validation_groups=report_statistics.groups_data,
            total_integrations=report_statistics.total_items,
            total_fatal_issues=report_statistics.total_fatal,
            total_non_fatal_issues=report_statistics.total_warn,
            current_time=datetime.datetime.now(datetime.UTC)
            .astimezone()
            .strftime("%B %d, %Y at %I:%M %p %Z"),
            css_content=(template_dir / "static" / "style.css").read_text(encoding="utf-8-sig"),
            js_content=(template_dir / "static" / "script.js").read_text(encoding="utf-8-sig"),
        )

    def _get_report_statistics(self) -> ReportStatistics:
        groups_data = {}
        total_items = total_fatal = total_warn = 0

        for content_type, full_report in self.validation_results.items():
            all_reports = [
                report for reports in full_report.values() if reports for report in reports
            ]

            fatal = sum(len(r.validation_report.failed_fatal_validations) for r in all_reports)
            warn = sum(len(r.validation_report.failed_non_fatal_validations) for r in all_reports)

            groups_data[content_type.value] = {
                "reports_by_category": full_report,
                "total_items": len(all_reports),
                "total_fatal": fatal,
                "total_warn": warn,
            }
            total_items += len(all_reports)
            total_fatal += fatal
            total_warn += warn

        return ReportStatistics(groups_data, total_items, total_fatal, total_warn)
