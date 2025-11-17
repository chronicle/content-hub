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
    from mp.validate.data_models import FullReport, ValidationResults


class CliDisplay:
    def __init__(self, validation_results: FullReport) -> None:
        self.validation_results: FullReport = validation_results
        self.console: Console = Console()

    def display(self) -> None:
        """Display the validation result in the cli."""
        if self._is_results_empty():
            self.console.print("[bold green]All Validations Passed\n[/bold green]")

        display_categories: list[str] = ["Pre-Build", "Build", "Post-Build"]

        for category in display_categories:
            validation_results: list[ValidationResults] = self.validation_results.get(category)
            if not validation_results:
                continue

            self.console.print(
                f"[bold underline blue]\n{category} Validations\n[/bold underline blue]"
            )
            for integration_result in validation_results:
                self.console.print(_build_table(integration_result), "\n")

    def _is_results_empty(self) -> bool:
        return not any(
            integration_result for integration_result in self.validation_results.values()
        )


def _build_table(integration_result: ValidationResults) -> Table:
    table = Table(
        title=f"🧩  {integration_result.integration_name}",
        title_style="bold",
        show_lines=True,
        box=box.ROUNDED,
    )
    table.add_column("Validation Name", style="red")
    table.add_column("Validation Details", style="yellow")
    for validation in integration_result.validation_report.failed_non_fatal_validations:
        table.add_row(validation.validation_name, validation.info)

    for validation in integration_result.validation_report.failed_fatal_validations:
        table.add_row(validation.validation_name, validation.info)

    return table
