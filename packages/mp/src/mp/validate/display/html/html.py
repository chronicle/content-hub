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
from typing import TYPE_CHECKING, Any

import jinja2
from rich.console import Console

if TYPE_CHECKING:
    from pathlib import Path

    from jinja2 import Environment, Template

    from mp.validate.data_models import ContentType, FullReport, ValidationResults


class HtmlFormat:
    def __init__(self, validation_results: dict[ContentType, FullReport]) -> None:
        self.validation_results = validation_results
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

    def _generate_validation_report_html(  # noqa: PLR0914
        self, template_name: str = "html_report/report.html"
    ) -> str:
        script_dir: Path = pathlib.Path(__file__).parent.resolve()
        template_dir: Path = script_dir / "templates"
        env: Environment = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            autoescape=jinja2.select_autoescape(["html"]),
        )
        template: Template = env.get_template(template_name)

        css_file_path: Path = template_dir / "static" / "style.css"
        js_file_path: Path = template_dir / "static" / "script.js"

        css_content: str = css_file_path.read_text(encoding="utf-8-sig")
        js_content: str = js_file_path.read_text(encoding="utf-8-sig")

        groups_data = {}
        total_items_all = 0
        total_fatal_all = 0
        total_warn_all = 0

        for content_type, full_report in self.validation_results.items():
            all_reports: list[ValidationResults] = [
                report
                for reports_list in full_report.values()
                if reports_list is not None
                for report in reports_list
            ]

            fatal_count = sum(
                len(r.validation_report.failed_fatal_validations) for r in all_reports
            )
            warn_count = sum(
                len(r.validation_report.failed_non_fatal_validations) for r in all_reports
            )

            group_name = content_type.value

            groups_data[group_name] = {
                "reports_by_category": full_report,
                "total_items": len(all_reports),
                "total_fatal": fatal_count,
                "total_warn": warn_count,
            }

            total_items_all += len(all_reports)
            total_fatal_all += fatal_count
            total_warn_all += warn_count

        current_time_aware: datetime.datetime = datetime.datetime.now(datetime.UTC).astimezone()

        context: dict[str, Any] = {
            "validation_groups": groups_data,
            "total_integrations": total_items_all,
            "total_fatal_issues": total_fatal_all,
            "total_non_fatal_issues": total_warn_all,
            "current_time": current_time_aware.strftime("%B %d, %Y at %I:%M %p %Z"),
            "css_content": css_content,
            "js_content": js_content,
        }
        return template.render(context)
