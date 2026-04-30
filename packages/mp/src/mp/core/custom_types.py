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

import enum
from collections.abc import Mapping
from typing import Any, NamedTuple, ParamSpec, TypeAlias

from . import constants

P = ParamSpec("P")


ActionName: TypeAlias = str
ConnectorName: TypeAlias = str
JsonString: TypeAlias = str
JobName: TypeAlias = str
WidgetName: TypeAlias = str
ManagerName: TypeAlias = str
YamlFileContent: TypeAlias = Mapping[str, Any]


class RepositoryType(enum.Enum):
    THIRD_PARTY = constants.THIRD_PARTY_REPO_NAME
    COMMERCIAL = constants.COMMERCIAL_REPO_NAME
    PLAYBOOKS = constants.PLAYBOOKS_DIR_NAME
    ALL_CONTENT = "all_content"
    CUSTOM = "custom"


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
