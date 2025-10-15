"""Module defining custom types and dataclasses used throughout the application."""

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

import dataclasses
import enum
from collections.abc import Iterable, Mapping
from typing import Any, Generic, NamedTuple, TypeAlias, TypeVar

from . import constants

_T = TypeVar("_T", bound=Iterable[Any])


@dataclasses.dataclass(slots=True)
class Products(Generic[_T]):
    integrations: _T
    groups: _T


ActionName: TypeAlias = str
ConnectorName: TypeAlias = str
JsonString: TypeAlias = str
JobName: TypeAlias = str
WidgetName: TypeAlias = str
ManagerName: TypeAlias = str
YamlFileContent: TypeAlias = Mapping[str, Any]


class RepositoryType(enum.Enum):
    COMMUNITY = constants.COMMUNITY_DIR_NAME
    COMMERCIAL = constants.COMMERCIAL_DIR_NAME


class CheckOutputFormat(enum.Enum):
    CONCISE = "concise"
    FULL = "full"
    JSON = "json"
    JSON_LINES = "json-lines"
    JUNIT = "junit"
    GROUPED = "grouped"
    GITHUB = "github"
    GITLAB = "gitlab"
    PYLINT = "pylint"
    RD_JSON = "rdjson"
    AZURE = "azure"
    SARIF = "sarif"


class RuffParams(NamedTuple):
    output_format: CheckOutputFormat
    fix: bool
    unsafe_fixes: bool
