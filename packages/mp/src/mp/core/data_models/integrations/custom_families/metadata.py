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
from typing import TYPE_CHECKING, Annotated, Self, TypedDict

import pydantic

import mp.core.constants
from mp.core.data_models.abc import SequentialMetadata

from .rule import BuiltCustomFamilyRule, CustomFamilyRule, NonBuiltCustomFamilyRule

if TYPE_CHECKING:
    from pathlib import Path


class BuiltCustomFamily(TypedDict):
    Family: str
    Description: str
    ImageBase64: str
    IsCustom: bool
    Rules: list[BuiltCustomFamilyRule]


class NonBuiltCustomFamily(TypedDict):
    family: str
    description: str
    image_base64: str
    is_custom: bool
    rules: list[NonBuiltCustomFamilyRule]


class CustomFamily(SequentialMetadata[BuiltCustomFamily, NonBuiltCustomFamily]):
    family: str
    description: Annotated[
        str,
        pydantic.Field(max_length=mp.core.constants.LONG_DESCRIPTION_MAX_LENGTH),
    ]
    image_base64: pydantic.Base64Bytes
    is_custom: bool
    rules: list[CustomFamilyRule]

    @classmethod
    def from_built_path(cls, path: Path) -> list[Self]:
        """Create based on the metadata files found in the 'built' integration path.

        Args:
            path: the path to the built integration

        Returns:
            A list of `CustomFamily` objects

        """
        meta_path: Path = (
            path
            / mp.core.constants.OUT_CUSTOM_FAMILIES_DIR
            / mp.core.constants.OUT_CUSTOM_FAMILIES_FILE
        )
        if not meta_path.exists():
            return []

        return cls._from_built_path(meta_path)

    @classmethod
    def from_non_built_path(cls, path: Path) -> list[Self]:
        """Create based on the metadata files found in the non-built-integration path.

        Args:
            path: the path to the non-built integration

        Returns:
            A list of `CustomFamily` objects

        """
        meta_path: Path = path / mp.core.constants.CUSTOM_FAMILIES_FILE
        if not meta_path.exists():
            return []

        return cls._from_non_built_path(meta_path)

    @classmethod
    def _from_built(cls, built: BuiltCustomFamily) -> Self:
        return cls(
            family=built["Family"],
            description=built["Description"],
            image_base64=built["ImageBase64"],  # ty:ignore[invalid-argument-type]
            is_custom=built.get("IsCustom", False),
            rules=[CustomFamilyRule.from_built(rule) for rule in built["Rules"]],
        )

    @classmethod
    def _from_non_built(cls, non_built: NonBuiltCustomFamily) -> Self:
        return cls(
            family=non_built["family"],
            description=non_built["description"],
            image_base64=non_built["image_base64"],  # ty:ignore[invalid-argument-type]
            is_custom=non_built.get("is_custom", False),
            rules=[CustomFamilyRule.from_non_built(rule) for rule in non_built["rules"]],
        )

    def to_built(self) -> BuiltCustomFamily:
        """Create a built custom family metadata dict.

        Returns:
            A built version of the custom family metadata dict

        """
        return BuiltCustomFamily(
            Family=self.family,
            Description=self.description,
            ImageBase64=base64.b64encode(self.image_base64).decode(),
            IsCustom=self.is_custom,
            Rules=[rule.to_built() for rule in self.rules],
        )

    def to_non_built(self) -> NonBuiltCustomFamily:
        """Create a non-built custom family metadata dict.

        Returns:
            A non-built version of the custom family metadata dict

        """
        return NonBuiltCustomFamily(
            family=self.family,
            description=self.description,
            image_base64=base64.b64encode(self.image_base64).decode(),
            is_custom=self.is_custom,
            rules=[rule.to_non_built() for rule in self.rules],
        )
