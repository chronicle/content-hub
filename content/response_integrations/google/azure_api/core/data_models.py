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

from typing import TYPE_CHECKING
import re
import dataclasses

from TIPCommon.transformation import dict_to_flat

if TYPE_CHECKING:
    from typing import Any

    from TIPCommon.types import SingleJson


@dataclasses.dataclass(slots=True)
class IntegrationParameters:
    login_api_root: str
    api_root: str
    tenant_id: str
    client_id: str
    client_secret: str
    verify_ssl: bool
    scopes: list[str]
    refresh_token: str
    redirect_url: str


@dataclasses.dataclass(frozen=True)
class IntegrationPlaceholders:
    def apply_placeholders_on_dict(self, dict_: dict[str, Any]) -> dict[str, Any]:
        """Recursively apply placeholders to every value in the target object.

        Args:
            dict_: Dictionary to apply placeholders to

        Returns:
            dict[str, Any] | None: Dictionary with placeholders applied
        """
        for key, value in dict_.items():
            dict_[key] = self.apply_placeholders(value)

        return dict_

    def apply_placeholders_on_list(self, target: list[Any]) -> list[Any]:
        """Recursively apply placeholders to every value in the target object.

        Args:
            target: Dictionary to apply placeholders to

        Returns:
            list[str, Any] | None: Dictionary with placeholders applied
        """
        return [self.apply_placeholders(item) for item in target]

    def apply_placeholders_on_str(self, value: str) -> str:
        """Apply placeholders to a string.

        Args:
            value (str): String to apply placeholders to

        Returns:
            str: String with placeholders applied
        """
        for field in dataclasses.fields(self):
            field_value = getattr(self, field.name)
            if field_value is None:
                continue

            value = re.sub("{{" + field.name + "}}", field_value, value)
        return value

    def apply_placeholders(self, target: list[Any] | dict[str, Any] | str | None) -> Any:
        """Apply placeholders to a target project.

        Args:
            target (str): String to apply placeholders to

        Returns:
            str: String with placeholders applied
        """
        if target is None:
            return target

        if isinstance(target, str):
            return self.apply_placeholders_on_str(target)

        if isinstance(target, dict):
            return self.apply_placeholders_on_dict(target)

        if isinstance(target, list):
            return self.apply_placeholders_on_list(target)

        return target


@dataclasses.dataclass(frozen=True)
class BaseModel:
    raw_data: SingleJson

    def to_json(self) -> SingleJson:
        return dataclasses.asdict(self)

    def to_flat(self) -> dict[str, Any]:
        return dict_to_flat(self.to_json()["raw_data"])


@dataclasses.dataclass(frozen=True)
class BaseObject(BaseModel):
    """Class to create data model for Base Object"""

    @classmethod
    def from_json(cls, raw_data: SingleJson) -> BaseObject:
        """Create a BaseObject object from JSON data

        Args:
            raw_data (SingleJson): raw data to create BaseObject from

        Returns:
            BaseObject: Base object
        """
        return cls(raw_data=raw_data)


@dataclasses.dataclass(slots=True)
class ExecuteHTTPRequestParams:
    method: str
    url_path: str
    params: SingleJson | None = None
    headers: SingleJson | None = None
    cookies: SingleJson | None = None
    body_payload: str | None = None
    follow_redirects: bool = True
    timeout: int = 30
