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
from typing import TYPE_CHECKING

import jinja2
from rich.console import Console

if TYPE_CHECKING:
    from pathlib import Path

    from jinja2 import Environment, Template

    from mp.run_pre_build_tests.process_test_output import IntegrationTestResults


class HtmlFormat:
    def __init__(self, integration_results_list: list[IntegrationTestResults]) -> None:
        self.integration_results_list: list[IntegrationTestResults] = integration_results_list
        self.console: Console = Console()

    def display(self) -> None:
        """Generate an HTML report for integration test results."""
        try:
            html_content: str = self._generate_validation_report_html()

            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".html", encoding="utf-8"
            ) as temp_file:
                temp_file.write(html_content)
                report_path: Path = pathlib.Path(temp_file.name)

            resolved_path: Path = report_path.resolve()
            self.console.print(f"📂 Report available at 👉: {resolved_path.as_uri()}")
            webbrowser.open(resolved_path.as_uri())

        except Exception as e:  # noqa: BLE001
            self.console.print(f"❌ Error generating report: {e}")

    def _generate_validation_report_html(
        self,
        template_name: str = "html_report/report.html",
    ) -> str:
        template_dir: Path = pathlib.Path(__file__).parent.resolve() / "templates"
        env: Environment = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            autoescape=jinja2.select_autoescape(["html"]),
        )
        template: Template = env.get_template(template_name)

        css_file_path: Path = template_dir / "static" / "style.css"
        js_file_path: Path = template_dir / "static" / "script.js"

        css_content: str = css_file_path.read_text(encoding="utf-8-sig")
        js_content: str = js_file_path.read_text(encoding="utf-8-sig")

        all_results: list[IntegrationTestResults] = self.integration_results_list

        total_integrations: int = len(all_results)
        total_failed_tests: int = sum(r.failed_tests for r in all_results)
        total_skipped_tests: int = sum(r.skipped_tests for r in all_results)

        current_time_aware: datetime.datetime = datetime.datetime.now().astimezone()

        context = {
            "integration_results_list": all_results,
            "total_integrations": total_integrations,
            "total_skipped_tests": total_skipped_tests,
            "total_failed_tests": total_failed_tests,
            "current_time": current_time_aware.strftime("%B %d, %Y at %I:%M %p %Z"),
            "css_content": css_content,
            "js_content": js_content,
        }
        return template.render(context)
