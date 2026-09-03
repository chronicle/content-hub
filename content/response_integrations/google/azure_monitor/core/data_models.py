# Copyright 2026 Google LLC
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

import re
from dataclasses import dataclass, field, fields, make_dataclass
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Type, Self

    from TIPCommon.types import SingleJson


@dataclass(slots=True)
class IntegrationParameters:
    login_api_root: str
    api_root: str
    tenant_id: str
    client_id: str
    client_secret: str
    workspace_id: str
    verify_ssl: bool


def to_snake_case(name: str) -> str:
    """Convert PascalCase or camelCase to snake_case."""
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return name.lower()


@dataclass(slots=True)
class AzureLogEntry:
    """Dynamic model for a single row from Azure Monitor logs."""

    data: SingleJson = field(default_factory=dict)

    @classmethod
    def from_json(cls, table_json: SingleJson) -> list[Self]:
        """Create list of AzureLogEntry (with dynamic fields) from JSON response.

        Args:
            table_json (SingleJson): JSON response from Azure Monitor logs.

        Returns:
            list[Self]: List of AzureLogEntry objects.
        """
        entries: list[Self] = []

        for table in table_json.get("tables", []):
            columns = [col["name"] for col in table.get("columns", [])]
            snake_columns = [to_snake_case(col) for col in columns]
            rows = table.get("rows", [])

            dynamic_entry = make_dataclass(
                "DynamicAzureLogEntry",
                [(col, Any, field(default=None)) for col in snake_columns],
                bases=(cls,),
                slots=True,
            )

            for row in rows:
                data = dict(zip(snake_columns, row))
                entries.append(dynamic_entry(**data))

        return entries

    def to_json(self) -> SingleJson:
        """Convert AzureLogEntry (including dynamic subclass) to JSON.

        Returns:
            SingleJson: JSON representation of AzureLogEntry.
        """
        result: SingleJson = {}
        for f in fields(self):
            if f.name == "data":
                continue

            value = getattr(self, f.name)
            pascal_name = "".join(part.capitalize() for part in f.name.split("_"))
            result[pascal_name] = value

        return result
