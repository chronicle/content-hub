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

from typing import Any

from TIPCommon.types import SingleJson
from sysdig_secure.core import SysdigSecureDatamodels as datamodels


def build_base_object(raw_data: SingleJson) -> datamodels.BaseObject:
    """Build BaseObject from JSON data

    Args:
        raw_data (SingleJson): raw JSON data

    Returns:
        datamodels.BaseObject: BaseObject
    """
    return datamodels.BaseObject.from_json(raw_data=raw_data)


def build_event_objects(raw_data: dict[str, Any]) -> list[datamodels.Event]:
    """Build list of Event dataclasses

    Args:
        raw_data (dict[str, Any]): raw data dict

    Returns:
        list[datamodels.Event]: list of Event dataclass
    """

    return [
        datamodels.Event.from_json(raw_data=item)
        for item in raw_data.get("data", [])
    ]
