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

from typing import TYPE_CHECKING, Annotated, Self, TypedDict

import pydantic

import mp.core.constants
import mp.core.data_models.abc

from .step import Step  # noqa: TC001

if TYPE_CHECKING:
    from pathlib import Path


class BuiltPlaybookMetadata(TypedDict):
    Identifier: str
    IsEnable: bool
    Version: float
    Name: str
    Description: str


class NonBuiltPlaybookMetadata(TypedDict):
    pass


class PlaybookMetadata(
    mp.core.data_models.abc.ComponentMetadata[BuiltPlaybookMetadata, NonBuiltPlaybookMetadata]
):
    identifier: Annotated[str, pydantic.Field(max_length=mp.core.constants.DISPLAY_NAME_MAX_LENGTH)]
    is_enable: bool
    version: Annotated[float, pydantic.Field(ge=0.0)]
    name: Annotated[
        str,
        pydantic.Field(
            max_length=mp.core.constants.DISPLAY_NAME_MAX_LENGTH,
            pattern=mp.core.constants.SCRIPT_DISPLAY_NAME_REGEX,
        ),
    ]
    steps: list[Step]

    @classmethod
    def from_built_path(cls, path: Path) -> list[Self]:
        pass

    @classmethod
    def from_non_built_path(cls, path: Path) -> list[Self]:
        pass

    @classmethod
    def _from_built(cls, file_name: str, built: BuiltPlaybookMetadata) -> Self:
        pass

    @classmethod
    def _from_non_built(cls, file_name: str, non_built: NonBuiltPlaybookMetadata) -> Self:
        pass

    def to_built(self) -> BuiltPlaybookMetadata:
        pass

    def to_non_built(self) -> NonBuiltPlaybookMetadata:
        pass
