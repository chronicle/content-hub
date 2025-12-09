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

import base64
import json
import pathlib
from typing import TYPE_CHECKING, Annotated, NotRequired, Self, TypedDict

import pydantic
import yaml

import mp.core.constants
import mp.core.file_utils
import mp.core.utils
from mp.core.data_models.abc import RepresentableEnum, SingularComponentMetadata

from .feature_tags import BuiltFeatureTags, FeatureTags, NonBuiltFeatureTags
from .parameter import BuiltIntegrationParameter, IntegrationParameter, NonBuiltIntegrationParameter

if TYPE_CHECKING:
    from pathlib import Path

MINIMUM_SYSTEM_VERSION: float = 5.3


class PythonVersion(RepresentableEnum):
    PY_3_11 = 3

    @classmethod
    def from_string(cls, s: str, /) -> PythonVersion:
        """Create a PythonVersion from string representation.

        Returns:
            The PythonVersion object

        Raises:
            ValueError:
                When the python version doesn't match a valid version

        """
        str_to_enum: dict[str, PythonVersion] = {
            "3.11": cls.PY_3_11,
        }
        try:
            return str_to_enum[str(s)]
        except KeyError:
            msg: str = (
                f"Invalid python version for integrations: {s}"
                f"\nSupported versions: {', '.join(str_to_enum.keys())}"
            )
            raise ValueError(msg) from None

    def to_string(self) -> str:
        """PythonVersion's string representation.

        Returns:
            A string representation of the object

        Raises:
            ValueError:
                When the python version doesn't match a valid version

        """
        enum_to_str: dict[PythonVersion, str] = {
            PythonVersion.PY_3_11: "3.11",
        }
        try:
            return enum_to_str[self]
        except KeyError:
            msg: str = (
                f"Invalid python version for integrations: {self}"
                f"\nSupported versions: {', '.join(str(e.value) for e in enum_to_str)}"
            )
            raise ValueError(msg) from None


class BuiltIntegrationMetadata(TypedDict):
    Categories: list[str]
    Description: str
    FeatureTags: NotRequired[BuiltFeatureTags | None]
    DisplayName: str
    Identifier: str
    PythonVersion: int
    DocumentationLink: str | None
    ImageBase64: str | None
    IntegrationProperties: list[BuiltIntegrationParameter]
    ShouldInstalledInSystem: bool
    IsAvailableForCommunity: bool
    MarketingDisplayName: str
    MinimumSystemVersion: float
    SVGImage: str | None
    SvgImage: NotRequired[str | None]
    Version: float
    IsCustom: bool
    IsPowerUp: bool
    IsCertified: bool


class NonBuiltIntegrationMetadata(TypedDict):
    categories: list[str]
    description: NotRequired[str]
    feature_tags: NotRequired[NonBuiltFeatureTags | None]
    name: str
    identifier: str
    python_version: NotRequired[str]
    documentation_link: NotRequired[str | None]
    image_path: str | None
    parameters: list[NonBuiltIntegrationParameter]
    should_install_in_system: NotRequired[bool]
    svg_logo_path: str | None
    version: NotRequired[float]
    is_custom: NotRequired[bool]
    is_available_for_community: NotRequired[bool]
    is_powerup: NotRequired[bool]


class IntegrationMetadata(
    SingularComponentMetadata[BuiltIntegrationMetadata, NonBuiltIntegrationMetadata]
):
    categories: list[str]
    feature_tags: FeatureTags | None
    name: Annotated[
        str,
        pydantic.Field(
            max_length=mp.core.constants.DISPLAY_NAME_MAX_LENGTH,
            pattern=mp.core.constants.SCRIPT_DISPLAY_NAME_REGEX,
        ),
    ]
    identifier: Annotated[
        str,
        pydantic.Field(
            max_length=mp.core.constants.DISPLAY_NAME_MAX_LENGTH,
            pattern=mp.core.constants.SCRIPT_IDENTIFIER_REGEX,
        ),
    ]
    documentation_link: pydantic.HttpUrl | pydantic.FileUrl | None
    image_base64: pydantic.Base64Bytes | None
    parameters: Annotated[
        list[IntegrationParameter],
        pydantic.Field(max_length=mp.core.constants.MAX_PARAMETERS_LENGTH),
    ]
    python_version: PythonVersion = PythonVersion.PY_3_11
    description: Annotated[
        str,
        pydantic.Field(max_length=mp.core.constants.LONG_DESCRIPTION_MAX_LENGTH),
    ] = ""
    version: Annotated[
        pydantic.PositiveFloat,
        pydantic.Field(ge=mp.core.constants.MINIMUM_SCRIPT_VERSION),
    ] = mp.core.constants.MINIMUM_SCRIPT_VERSION
    should_install_in_system: bool = False
    svg_logo: str | None
    is_certified: bool = True
    is_custom: bool = False
    is_available_for_community: bool = True
    is_powerup: bool = False
    minimum_system_version: Annotated[
        pydantic.PositiveFloat,
        pydantic.Field(ge=MINIMUM_SYSTEM_VERSION),
    ] = MINIMUM_SYSTEM_VERSION

    @classmethod
    def from_built_path(cls, path: Path) -> Self:
        """Create IntegrationMetadata from a path of a "built" integration.

        Args:
            path: the path to the integration's "built" version

        Returns:
            An IntegrationMetadata object

        Raises:
            ValueError: when the "built" is failed to be loaded

        """
        metadata_file: str = mp.core.constants.INTEGRATION_DEF_FILE.format(path.name)
        metadata_path: Path = path / metadata_file
        built: str = metadata_path.read_text(encoding="utf-8")
        try:
            metadata_content: BuiltIntegrationMetadata = json.loads(built)
            metadata: Self = cls.from_built(metadata_path.name, metadata_content)
            metadata.is_certified = mp.core.file_utils.is_commercial_integration(path)
        except (ValueError, json.JSONDecodeError) as e:
            msg: str = f"Failed to load json from {metadata_path}\n{built}"
            raise ValueError(mp.core.utils.trim_values(msg)) from e
        else:
            return metadata

    @classmethod
    def from_non_built_path(cls, path: Path) -> Self:
        """Create IntegrationMetadata from a path of a "non-built" integration.

        Args:
            path: the path to the integration's "non-built" version

        Returns:
            An IntegrationMetadata object

        Raises:
            ValueError: when the "non-built" is failed to be loaded

        """
        metadata_path: Path = path / mp.core.constants.DEFINITION_FILE
        built: str = metadata_path.read_text(encoding="utf-8")
        try:
            metadata_content: NonBuiltIntegrationMetadata = yaml.safe_load(built)
            _read_image_files(metadata_content, path)
            metadata: Self = cls.from_non_built(metadata_path.name, metadata_content)
            metadata.is_certified = mp.core.file_utils.is_commercial_integration(path)
        except (ValueError, json.JSONDecodeError) as e:
            msg: str = f"Failed to load json from {metadata_path}\n{built}"
            raise ValueError(mp.core.utils.trim_values(msg)) from e
        else:
            return metadata

    @classmethod
    def _from_built(cls, _: str, built: BuiltIntegrationMetadata) -> Self:  # ty:ignore[invalid-method-override]
        feature_tags: FeatureTags | None = None
        raw_feature_tags: BuiltFeatureTags | None = built.get("FeatureTags")
        if raw_feature_tags is not None:
            feature_tags = FeatureTags.from_built(raw_feature_tags)

        image: str | bytes | None = built["ImageBase64"]
        if isinstance(image, str):
            image = image.encode()

        svg: str | None = built.get("SVGImage")
        if svg is None:
            svg = built["SvgImage"]

        return cls(
            categories=built["Categories"],
            description=built["Description"],
            feature_tags=feature_tags,
            name=built["DisplayName"],
            identifier=built["Identifier"],
            python_version=PythonVersion(built["PythonVersion"]),
            documentation_link=built["DocumentationLink"],
            image_base64=image,
            parameters=[IntegrationParameter.from_built(p) for p in built["IntegrationProperties"]],
            should_install_in_system=built["ShouldInstalledInSystem"],
            svg_logo=svg,
            version=built["Version"],
            is_custom=built.get("IsCustom", False),
            is_available_for_community=built.get("IsAvailableForCommunity", True),
            is_powerup=built.get("IsPowerUp", False),
        )

    @classmethod
    def _from_non_built(cls, _: str, non_built: NonBuiltIntegrationMetadata) -> Self:  # ty:ignore[invalid-method-override]
        feature_tags: FeatureTags | None = None
        raw_feature_tags: NonBuiltFeatureTags | None = non_built.get("feature_tags")
        if raw_feature_tags is not None:
            feature_tags = FeatureTags.from_non_built(raw_feature_tags)

        name: str = non_built["name"]
        svg: str | None = non_built.get("svg_logo_path")

        return cls(
            categories=non_built["categories"],
            feature_tags=feature_tags,
            name=name,
            identifier=non_built["identifier"],
            documentation_link=non_built.get("documentation_link"),
            description=non_built.get("description", ""),
            image_base64=non_built["image_path"],
            parameters=[IntegrationParameter.from_non_built(p) for p in non_built["parameters"]],
            should_install_in_system=non_built.get("should_install_in_system", False),
            is_custom=non_built.get("is_custom", False),
            svg_logo=svg,
            is_available_for_community=non_built.get(
                "is_available_for_community",
                True,
            ),
            is_powerup=non_built.get("is_powerup", False),
        )

    def to_built(self) -> BuiltIntegrationMetadata:
        """Create the "built" TypedDict version of the integration's metadata.

        Returns:
            The "built" TypedDict version of the integration's metadata.

        """
        built: BuiltIntegrationMetadata = BuiltIntegrationMetadata(
            Categories=self.categories,
            Description=self.description,
            DisplayName=self.name,
            DocumentationLink=(
                str(self.documentation_link) or None
                if self.documentation_link is not None
                else None
            ),
            FeatureTags=(self.feature_tags.to_built() if self.feature_tags is not None else None),
            Identifier=self.identifier,
            ImageBase64=(
                base64.b64encode(self.image_base64).decode()
                if self.image_base64 is not None
                else None
            ),
            IntegrationProperties=[p.to_built() for p in self.parameters],
            IsAvailableForCommunity=True,
            MarketingDisplayName=self.name,
            MinimumSystemVersion=float(self.minimum_system_version),
            PythonVersion=self.python_version.value,
            SVGImage=self.svg_logo,
            ShouldInstalledInSystem=self.should_install_in_system,
            Version=self.version,
            IsCustom=self.is_custom,
            IsPowerUp=self.is_powerup,
            IsCertified=self.is_certified,
        )
        mp.core.utils.remove_none_entries_from_mapping(built)
        return built

    def to_non_built(self) -> NonBuiltIntegrationMetadata:
        """Create the "non-built" TypedDict version of the integration's metadata.

        Returns:
            The "non-built" TypedDict version of the integration's metadata.

        """
        svg_path: Path = pathlib.Path(
            ".", mp.core.constants.RESOURCES_DIR, mp.core.constants.LOGO_FILE
        )
        image: Path = pathlib.Path(
            ".", mp.core.constants.RESOURCES_DIR, mp.core.constants.IMAGE_FILE
        )

        non_built: NonBuiltIntegrationMetadata = NonBuiltIntegrationMetadata(
            identifier=self.identifier,
            name=self.name,
            parameters=[p.to_non_built() for p in self.parameters],
            documentation_link=(
                str(self.documentation_link) if self.documentation_link is not None else None
            ),
            categories=self.categories,
            svg_logo_path=svg_path.as_posix() if self.svg_logo is not None else None,
            image_path=image.as_posix() if self.image_base64 is not None else None,
        )

        if self.feature_tags is not None:
            non_built["feature_tags"] = self.feature_tags.to_non_built()

        if self.should_install_in_system is True:
            non_built["should_install_in_system"] = self.should_install_in_system

        if self.is_available_for_community is False:
            non_built["is_available_for_community"] = self.is_available_for_community

        if self.is_powerup is True:
            non_built["is_powerup"] = self.is_powerup

        mp.core.utils.remove_none_entries_from_mapping(non_built)
        return non_built


def _read_image_files(metadata_content: NonBuiltIntegrationMetadata, path: Path) -> None:
    """Read image files and update the metadata dictionary in place.

    Args:
        metadata_content: The metadata content.
        path: The path to the integration.

    """
    if image_str := metadata_content.get("image_path"):
        full_path = path / image_str
        metadata_content["image_path"] = mp.core.file_utils.png_path_to_bytes(full_path)

    if svg_path_str := metadata_content.get("svg_logo_path"):
        full_path = path / svg_path_str
        metadata_content["svg_logo_path"] = mp.core.file_utils.svg_path_to_text(full_path)
