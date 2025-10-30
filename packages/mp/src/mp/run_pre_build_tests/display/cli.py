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

from rich import box
from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from mp.run_pre_build_tests.process_test_output import IntegrationTestResults


class CliDisplay:
    def __init__(self, tests_report: list[IntegrationTestResults]) -> None:
        self.tests_report: list[IntegrationTestResults] = tests_report
        self.console: Console = Console()

    def display(self) -> None:
        """Display the test results in the cli."""
        if not self.tests_report:
            self.console.print("[bold green]All Tests Passed\n[/bold green]")

        for integration_report in self.tests_report:
            self.console.print(_build_table(integration_report), "\n")


def _build_table(integration_report: IntegrationTestResults) -> Table:
    table: Table = Table(
        title=f"🧩 {integration_report.integration_name}",
        title_style="bold",
        show_lines=True,
        box=box.ROUNDED,
    )
    table.add_column("Test Name", style="yellow")
    if integration_report.failed_tests > 0:
        table.add_row("❌  Failed Tests:", style="red")
        for test_issue in integration_report.failed_tests_summary:
            table.add_row(test_issue.test_name)

    if integration_report.skipped_tests > 0:
        table.add_row("⏭️  Skipped Tests:", style="red")
        for test_issue in integration_report.skipped_tests_summary:
            table.add_row(test_issue.test_name)

    return table
