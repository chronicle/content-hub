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
from rich.rule import Rule
from rich.table import Table

from .constants import ICON_MAP

if TYPE_CHECKING:
    from mp.validate.data_models import ContentType, FullReport, ValidationResults


class CliDisplay:
    def __init__(self, validation_results: dict[ContentType, FullReport]) -> None:
        self.validation_results: dict[ContentType, FullReport] = validation_results
        self.console: Console = Console()

    def display(self) -> None:
        """Display the validation results in the CLI."""
        if self._is_all_empty():
            self.console.print("[bold green]All Validations Passed\n[/bold green]")
            return

        display_categories: list[str] = ["Pre-Build", "Build", "Post-Build"]

        for content_type, full_report in self.validation_results.items():
            if not any(full_report.values()):
                continue

            icon = ICON_MAP[content_type.value]

            self.console.print(Rule(f"[bold magenta]{icon} {content_type.value} Validations"))

            for category in display_categories:
                stage_results: list[ValidationResults] | None = full_report.get(category)
                if not stage_results:
                    continue

                self.console.print(f"[bold underline blue]\n{category} Stage[/bold underline blue]")
                for integration_result in stage_results:
                    self.console.print(_build_table(integration_result), "\n")

            self.console.print("\n")

    def _is_all_empty(self) -> bool:
        for full_report in self.validation_results.values():
            if any(full_report.values()):
                return False
        return True


def _build_table(integration_result: ValidationResults) -> Table:
    table = Table(
        title=f"  {integration_result.integration_name}",
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
