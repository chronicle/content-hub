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

from typing import TYPE_CHECKING, Annotated, NotRequired, Self, TypedDict

import pydantic

import mp.core.constants
from mp.core.data_models.abc import ComponentMetadata

from .parameter import BuiltJobParameter, JobParameter, NonBuiltJobParameter

if TYPE_CHECKING:
    from pathlib import Path

DEFAULT_RUNTIME_INTERVAL: int = 900


class BuiltJobMetadata(TypedDict):
    Creator: str
    Description: str
    Integration: str
    IsCustom: bool
    IsEnabled: bool
    Name: str
    Parameters: list[BuiltJobParameter]
    RunIntervalInSeconds: int
    Version: float


class NonBuiltJobMetadata(TypedDict):
    creator: str
    description: str
    integration: str
    is_custom: NotRequired[bool]
    is_enabled: NotRequired[bool]
    name: str
    parameters: list[NonBuiltJobParameter]
    run_interval_in_seconds: NotRequired[int]
    version: NotRequired[float]


class JobMetadata(ComponentMetadata[BuiltJobMetadata, NonBuiltJobMetadata]):
    file_name: str
    creator: str
    description: Annotated[
        str,
        pydantic.Field(max_length=mp.core.constants.LONG_DESCRIPTION_MAX_LENGTH),
    ]
    integration: Annotated[
        str,
        pydantic.Field(
            max_length=mp.core.constants.DISPLAY_NAME_MAX_LENGTH,
            pattern=mp.core.constants.SCRIPT_IDENTIFIER_REGEX,
        ),
    ]
    is_custom: bool = False
    is_enabled: bool = True
    name: Annotated[
        str,
        pydantic.Field(
            max_length=mp.core.constants.DISPLAY_NAME_MAX_LENGTH,
            pattern=mp.core.constants.SCRIPT_DISPLAY_NAME_REGEX,
        ),
    ]
    parameters: Annotated[
        list[JobParameter],
        pydantic.Field(max_length=mp.core.constants.MAX_PARAMETERS_LENGTH),
    ]
    run_interval_in_seconds: int
    version: Annotated[
        pydantic.PositiveFloat,
        pydantic.Field(ge=mp.core.constants.MINIMUM_SCRIPT_VERSION),
    ]

    @classmethod
    def from_built_path(cls, path: Path) -> list[Self]:
        """Create based on the metadata files found in the 'built' integration path.

        Args:
            path: the path to the built integration

        Returns:
            A list of `JobMetadata` objects

        """
        meta_path: Path = path / mp.core.constants.OUT_JOBS_META_DIR
        if not meta_path.exists():
            return []

        return [
            cls._from_built_path(p)
            for p in meta_path.rglob(f"*{mp.core.constants.JOBS_META_SUFFIX}")
        ]

    @classmethod
    def from_non_built_path(cls, path: Path) -> list[Self]:
        """Create based on the metadata files found in the non-built-integration path.

        Args:
            path: the path to the non-built integration

        Returns:
            A list of `JobMetadata` objects

        """
        meta_path: Path = path / mp.core.constants.JOBS_DIR
        if not meta_path.exists():
            return []

        return [
            cls._from_non_built_path(p)
            for p in meta_path.rglob(f"*{mp.core.constants.DEF_FILE_SUFFIX}")
        ]

    @classmethod
    def _from_built(cls, file_name: str, built: BuiltJobMetadata) -> Self:
        return cls(
            file_name=file_name,
            creator=built["Creator"],
            description=built["Description"],
            integration=built["Integration"],
            is_custom=built.get("IsCustom", False),
            is_enabled=built.get("IsEnabled", True),
            name=built["Name"],
            parameters=[JobParameter.from_built(param) for param in built["Parameters"]],
            run_interval_in_seconds=built["RunIntervalInSeconds"],
            version=built.get("Version", mp.core.constants.MINIMUM_SCRIPT_VERSION),
        )

    @classmethod
    def _from_non_built(cls, file_name: str, non_built: NonBuiltJobMetadata) -> Self:
        return cls(
            file_name=file_name,
            creator=non_built["creator"],
            description=non_built["description"],
            integration=non_built["integration"],
            is_custom=non_built.get("is_custom", False),
            is_enabled=non_built.get("is_enabled", True),
            name=non_built["name"],
            parameters=[JobParameter.from_non_built(param) for param in non_built["parameters"]],
            run_interval_in_seconds=non_built.get(
                "run_interval_in_seconds",
                DEFAULT_RUNTIME_INTERVAL,
            ),
            version=non_built.get("version", mp.core.constants.MINIMUM_SCRIPT_VERSION),
        )

    def to_built(self) -> BuiltJobMetadata:
        """Create a built job metadata dict.

        Returns:
            A built version of the job metadata dict

        """
        return BuiltJobMetadata(
            Creator=self.creator,
            Description=self.description,
            Integration=self.integration,
            IsCustom=self.is_custom,
            IsEnabled=self.is_enabled,
            Name=self.name,
            Parameters=[param.to_built() for param in self.parameters],
            RunIntervalInSeconds=self.run_interval_in_seconds,
            Version=float(self.version),
        )

    def to_non_built(self) -> NonBuiltJobMetadata:
        """Create a non-built job metadata dict.

        Returns:
            A non-built version of the job metadata dict

        """
        non_built: NonBuiltJobMetadata = NonBuiltJobMetadata(
            name=self.name,
            parameters=[param.to_non_built() for param in self.parameters],
            description=self.description,
            integration=self.integration,
            creator=self.creator,
        )

        if self.run_interval_in_seconds != DEFAULT_RUNTIME_INTERVAL:
            non_built["run_interval_in_seconds"] = self.run_interval_in_seconds

        return non_built
