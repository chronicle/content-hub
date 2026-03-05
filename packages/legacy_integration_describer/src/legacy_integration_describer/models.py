from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    """Configures the overall execution context storing directory and processing paths."""

    inputs_dir: Path
    outputs_dir: Path
    repos_config: list[tuple[Path, str]]


@dataclass(frozen=True)
class IntegrationRequest:
    """Represents a specific integration request gathered from partner input CSVs."""

    identifier: str
    version: str


@dataclass(frozen=True)
class IntegrationResult:
    """Represents the parsed outputs created by MP describing generated definitions."""

    integration_name: str
    action_name: str
    description: str
    categories: str
    entity_usage: str

    def to_row(self) -> dict[str, str]:
        """Convert object natively to string.

        Returns:
            dict[str, str]: String mappings natively resolving CSV columns.

        """
        return {
            "Integration Name": self.integration_name,
            "Action Name": self.action_name,
            "AI Description": self.description,
            "AI Categories": self.categories,
            "Entity Usage": self.entity_usage,
        }
