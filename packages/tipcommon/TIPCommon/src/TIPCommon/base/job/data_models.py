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

from typing import Any

from ...data_models import JobParamType
from ...types import SingleJson


class JobParameter:
    """A general script parameter object.

    Attributes:
        full_dict (dict[str, Any]): The original dict received from the API.
        id (int | None): The parameter's ID.
        is_mandatory (bool):
            Whether the parameter is mandatory or not.
            (prioritized over 'value' in playbooks).
        name (str | None): The parameter's name.
        type (ActionParamType): The type of the parameter.
        value (Any):
            The default value of the parameter
            (prioritized over 'default_value' in manual actions).
    """

    def __init__(self, input_dict: SingleJson) -> None:
        self.full_dict: SingleJson = input_dict
        self.id_: int | None = input_dict.get("id")
        self.is_mandatory: bool = input_dict.get(
            "mandatory",
            input_dict.get("isMandatory", False),
        )
        self.name: str = input_dict.get(
            "displayName",
            input_dict.get("name", "No name found!"),
        )
        self.type_ = self._parse_job_param_type(input_dict.get("type", -1))
        self.value: Any = input_dict.get("value")

    def _parse_job_param_type(self, type_value: str | int) -> JobParamType:
        if isinstance(type_value, str):
            normalized = type_value.strip().upper()

            if normalized in ("INT"):
                return JobParamType.INTEGER
            if normalized in JobParamType.__members__:
                return JobParamType[normalized]
            return JobParamType.NULL

        elif isinstance(type_value, int):
            try:
                return JobParamType(type_value)
            except ValueError:
                return JobParamType.NULL

        return JobParamType.NULL
