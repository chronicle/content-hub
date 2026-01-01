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

from typing import TYPE_CHECKING, Annotated, Any, NotRequired, Self, TypedDict

import pydantic

import mp.core.constants
import mp.core.file_utils
import mp.core.utils
from mp.core.data_models.abc import ComponentMetadata

from .dynamic_results_metadata import (
    BuiltDynamicResultsMetadata,
    DynamicResultsMetadata,
    NonBuiltDynamicResultsMetadata,
)
from .parameter import (
    ActionParameter,
    BuiltActionParameter,
    NonBuiltActionParameter,
)

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.custom_types import JsonString

DEFAULT_SCRIPT_RESULT_NAME: str = "is_success"
DEFAULT_SIMULATION_DATA: str = '{"Entities": []}'


class BuiltActionMetadata(TypedDict):
    Description: str
    DynamicResultsMetadata: list[BuiltDynamicResultsMetadata]
    IntegrationIdentifier: str
    IsAsync: bool
    IsCustom: bool
    IsEnabled: bool
    Name: str
    Parameters: list[BuiltActionParameter]
    Creator: str
    ScriptResultName: str
    SimulationDataJson: NotRequired[str]
    DefaultResultValue: NotRequired[str | None]
    Version: float


class NonBuiltActionMetadata(TypedDict):
    description: str
    dynamic_results_metadata: list[NonBuiltDynamicResultsMetadata]
    integration_identifier: str
    is_async: NotRequired[bool]
    is_custom: NotRequired[bool]
    is_enabled: NotRequired[bool]
    name: str
    parameters: list[NonBuiltActionParameter]
    creator: NotRequired[str]
    script_result_name: NotRequired[str]
    simulation_data_json: NotRequired[str]
    default_result_value: NotRequired[str | None]
    version: NotRequired[float]


class ActionMetadata(ComponentMetadata[BuiltActionMetadata, NonBuiltActionMetadata]):
    file_name: str
    description: Annotated[
        str,
        pydantic.Field(max_length=mp.core.constants.LONG_DESCRIPTION_MAX_LENGTH),
    ]
    dynamic_results_metadata: list[DynamicResultsMetadata]
    integration_identifier: Annotated[
        str,
        pydantic.Field(
            max_length=mp.core.constants.DISPLAY_NAME_MAX_LENGTH,
            pattern=mp.core.constants.SCRIPT_IDENTIFIER_REGEX,
        ),
    ]
    is_async: bool
    is_custom: bool
    is_enabled: bool
    name: Annotated[
        str,
        pydantic.Field(
            max_length=mp.core.constants.DISPLAY_NAME_MAX_LENGTH,
            pattern=mp.core.constants.SCRIPT_DISPLAY_NAME_REGEX,
        ),
    ]
    parameters: Annotated[
        list[ActionParameter],
        pydantic.Field(max_length=mp.core.constants.MAX_PARAMETERS_LENGTH),
    ]
    default_result_value: str | None
    creator: str
    script_result_name: str
    simulation_data_json: str
    version: Annotated[
        pydantic.PositiveFloat,
        pydantic.Field(ge=mp.core.constants.MINIMUM_SCRIPT_VERSION),
    ]

    @classmethod
    def from_built_path(cls, path: Path) -> list[Self]:
        """Create based on the metadata files found in the built integration path.

        Args:
            path: the path to the built integration

        Returns:
            A list of `ActionMetadata` objects

        """
        meta_path: Path = path / mp.core.constants.OUT_ACTIONS_META_DIR
        if not meta_path.exists():
            return []

        return [
            cls._from_built_path(p)
            for p in meta_path.rglob(f"*{mp.core.constants.ACTIONS_META_SUFFIX}")
        ]

    @classmethod
    def from_non_built_path(cls, path: Path) -> list[Self]:
        """Create based on the metadata files found in the non-built-integration path.

        Args:
            path: the path to the non-built integration

        Returns:
            A list of `ActionMetadata` objects

        """
        meta_path: Path = path / mp.core.constants.ACTIONS_DIR
        if not meta_path.exists():
            return []

        metadata_objects: list[Self] = []
        for p in meta_path.rglob(f"*{mp.core.constants.DEF_FILE_SUFFIX}"):
            action_metadata_json: dict[str, Any] = mp.core.file_utils.load_yaml_file(p)
            drms_with_json_contents: list[NonBuiltDynamicResultsMetadata] = _load_json_examples(
                action_metadata_json["dynamic_results_metadata"], meta_path
            )
            action_metadata_json["dynamic_results_metadata"] = drms_with_json_contents
            metadata_object: Self = cls.from_non_built(p.stem, action_metadata_json)
            metadata_objects.append(metadata_object)

        return metadata_objects

    @classmethod
    def _from_built(cls, file_name: str, built: BuiltActionMetadata) -> Self:
        """Create the obj from a built action metadata dict.

        Args:
            file_name: The action's metadata file name
            built: the built dict

        Returns:
            An `ActionMetadata` object

        """
        version: float = built.get("Version", mp.core.constants.MINIMUM_SCRIPT_VERSION)
        version = max(version, mp.core.constants.MINIMUM_SCRIPT_VERSION)

        return cls(
            file_name=file_name,
            creator=built["Creator"],
            description=built["Description"],
            dynamic_results_metadata=[
                DynamicResultsMetadata.from_built(drm)
                for drm in built.get("DynamicResultsMetadata", []) or []
            ],
            integration_identifier=built["IntegrationIdentifier"],
            is_async=built.get("IsAsync", False),
            is_custom=built.get("IsCustom", False),
            is_enabled=built.get("IsEnabled", True),
            name=built["Name"],
            parameters=[ActionParameter.from_built(p) for p in built.get("Parameters", [])],
            script_result_name=(built.get("ScriptResultName") or DEFAULT_SCRIPT_RESULT_NAME),
            simulation_data_json=(built.get("SimulationDataJson") or DEFAULT_SIMULATION_DATA),
            default_result_value=built.get("DefaultResultValue"),
            version=version,
        )

    @classmethod
    def _from_non_built(cls, file_name: str, non_built: NonBuiltActionMetadata) -> ActionMetadata:
        """Create the obj from a non-built action metadata dict.

        Args:
            file_name: The action's metadata file name
            non_built: the non-built dict

        Returns:
            An `ActionMetadata` object

        """
        return cls(
            file_name=file_name,
            creator=non_built.get("creator", "admin"),
            description=non_built["description"],
            dynamic_results_metadata=[
                DynamicResultsMetadata.from_non_built(drm)
                for drm in non_built.get("dynamic_results_metadata", [])
            ],
            integration_identifier=non_built["integration_identifier"],
            is_async=non_built.get("is_async", False),
            is_custom=non_built.get("is_custom", False),
            is_enabled=non_built.get("is_enabled", True),
            name=non_built["name"],
            parameters=[ActionParameter.from_non_built(p) for p in non_built["parameters"]],
            script_result_name=non_built.get("script_result_name", DEFAULT_SCRIPT_RESULT_NAME),
            simulation_data_json=non_built.get(
                "simulation_data_json",
                DEFAULT_SIMULATION_DATA,
            ),
            default_result_value=non_built.get("default_result_value"),
            version=non_built.get("version", mp.core.constants.MINIMUM_SCRIPT_VERSION),
        )

    def to_built(self) -> BuiltActionMetadata:
        """Create a built action metadata dict.

        Returns:
            A built version of the action metadata dict

        """
        built: BuiltActionMetadata = BuiltActionMetadata(
            Creator=self.creator,
            Description=self.description,
            DynamicResultsMetadata=[m.to_built() for m in self.dynamic_results_metadata],
            IntegrationIdentifier=self.integration_identifier,
            IsAsync=self.is_async,
            IsCustom=self.is_custom,
            IsEnabled=self.is_enabled,
            Name=self.name,
            Parameters=[p.to_built() for p in self.parameters],
            ScriptResultName=self.script_result_name,
            SimulationDataJson=self.simulation_data_json,
            DefaultResultValue=self.default_result_value,
            Version=float(self.version),
        )
        mp.core.utils.remove_none_entries_from_mapping(built)
        return built

    def to_non_built(self) -> NonBuiltActionMetadata:
        """Create a non-built action metadata dict.

        Returns:
            A non-built version of the action metadata dict

        """
        self._change_result_example_fields_to_paths()
        non_built: NonBuiltActionMetadata = NonBuiltActionMetadata(
            name=self.name,
            description=self.description,
            integration_identifier=self.integration_identifier,
            parameters=[p.to_non_built() for p in self.parameters],
            dynamic_results_metadata=[m.to_non_built() for m in self.dynamic_results_metadata],
            default_result_value=self.default_result_value,
            creator=self.creator,
        )
        if self.is_async:
            non_built["is_async"] = self.is_async

        if self.simulation_data_json != DEFAULT_SIMULATION_DATA:
            non_built["simulation_data_json"] = self.simulation_data_json

        if self.script_result_name != DEFAULT_SCRIPT_RESULT_NAME:
            non_built["script_result_name"] = self.script_result_name

        mp.core.utils.remove_none_entries_from_mapping(non_built)
        return non_built

    def _change_result_example_fields_to_paths(self) -> None:
        for drm in self.dynamic_results_metadata:
            if not drm.result_example or drm.result_example == "{}":
                drm.result_example = None
                continue

            json_file_name: str = (
                f"{mp.core.utils.str_to_snake_case(self.name)}_{drm.result_name}_example.json"
            )
            json_file_path: str = f"{mp.core.constants.RESOURCES_DIR}/{json_file_name}"
            drm.result_example = json_file_path


def _load_json_examples(
    drms: list[NonBuiltDynamicResultsMetadata], actions_dir_path: Path
) -> list[NonBuiltDynamicResultsMetadata]:
    """Load JSON examples from files and return a new list of DRMs with their content.

    Returns:
        A list of non-built DRM dicts, with the json examples content.

    """
    loaded_drms: list[NonBuiltDynamicResultsMetadata] = []

    for drm in drms:
        example_path: str | None = drm.get("result_example_path")

        if not example_path:
            drm["result_example_path"] = "{}"
            continue

        json_filepath: Path = actions_dir_path.parent / example_path
        json_content: JsonString = mp.core.file_utils.read_and_validate_json_file(json_filepath)
        drm["result_example_path"] = json_content

        loaded_drms.append(drm)

    return loaded_drms
