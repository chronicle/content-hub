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

import abc
import enum
import json
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Generic, Self, TypeVar

import pydantic
import yaml

import mp.core.utils

if TYPE_CHECKING:
    import pathlib


class RepresentableEnum(enum.Enum):
    @classmethod
    def from_string(cls, s: str, /) -> Self:
        """Create the enum object from a string.

        Args:
            s: the string representation of the enum object

        Returns:
            The corresponding enum member

        """
        str_to_enum: dict[str, Self] = {e.name.casefold(): e for e in cls}
        return str_to_enum[s.casefold()]

    def to_string(self) -> str:
        """Represent an enum member as a string.

        Returns:
            The string representation of the enum member

        """
        return self.name.casefold()


_BT = TypeVar("_BT", bound=Mapping[str, Any])
_NBT = TypeVar("_NBT", bound=Mapping[str, Any])


class Buildable(pydantic.BaseModel, abc.ABC, Generic[_BT, _NBT]):
    @classmethod
    @abc.abstractmethod
    def _from_built(cls, built: _BT) -> Self:
        """Create the object from a "built" typed dict.

        Args:
            built: the built typed dict object representation

        Returns:
            A new instance of the Buildable object

        """

    @classmethod
    @abc.abstractmethod
    def _from_non_built(cls, non_built: _NBT) -> Self:
        """Create the object from a "non-built" typed dict.

        Args:
            non_built: the non-built typed dict object representation

        Returns:
            A new instance of the Buildable object

        """

    @abc.abstractmethod
    def to_built(self) -> _BT:
        """Turn the buildable object into a "built" typed dict.

        Returns:
            The "built" typed dict representation of the object

        """

    @abc.abstractmethod
    def to_non_built(self) -> _NBT:
        """Turn the buildable object into a "non-built" typed dict.

        Returns:
            The "non-built" typed dict representation of the object

        """

    @classmethod
    def from_built(cls, built: _BT) -> Self:
        """Create the object from a "built" typed dict.

        Args:
            built: the built typed dict object representation

        Returns:
            A new instance of the Buildable object

        Raises:
            ValueError: when the built object failed to be loaded

        """
        try:
            metadata: Self = cls._from_built(built)
        except (KeyError, ValueError) as e:
            msg: str = f"Failed to load built\n{built}"
            raise ValueError(mp.core.utils.trim_values(msg)) from e
        else:
            return metadata

    @classmethod
    def from_non_built(cls, non_built: _NBT) -> Self:
        """Create the object from a "non-built" typed dict.

        Args:
            non_built: the non-built typed dict object representation

        Returns:
            A new instance of the Buildable object

        Raises:
            ValueError: when the non-built object failed to be loaded

        """
        try:
            metadata: Self = cls._from_non_built(non_built)
        except (KeyError, ValueError) as e:
            msg: str = f"Failed to load non-built\n{non_built}"
            raise ValueError(mp.core.utils.trim_values(msg)) from e
        else:
            return metadata


class BuildableScript(pydantic.BaseModel, abc.ABC, Generic[_BT, _NBT]):
    @classmethod
    @abc.abstractmethod
    def _from_built(cls, file_name: str, built: _BT) -> Self:
        """Create the object from a "built" typed dict.

        Args:
            file_name: the built component's file name
            built: the built typed dict object representation

        Returns:
            A new instance of the Buildable object

        """

    @classmethod
    @abc.abstractmethod
    def _from_non_built(cls, file_name: str, non_built: _NBT) -> Self:
        """Create the object from a "non-built" typed dict.

        Args:
            file_name: the built component's file name
            non_built: the non-built typed dict object representation

        Returns:
            A new instance of the Buildable object

        """

    @abc.abstractmethod
    def to_built(self) -> _BT:
        """Turn the buildable object into a "built" typed dict.

        Returns:
            The "built" typed dict representation of the object

        """

    @abc.abstractmethod
    def to_non_built(self) -> _NBT:
        """Turn the buildable object into a "non-built" typed dict.

        Returns:
            The "non-built" typed dict representation of the object

        """

    @classmethod
    def from_built(cls, file_name: str, built: _BT) -> Self:
        """Create the object from a "built" typed dict.

        Args:
            file_name: the built component's file name
            built: the built typed dict object representation

        Returns:
            A new instance of the Buildable object

        Raises:
            ValueError: when the built object failed to be loaded

        """
        try:
            metadata: Self = cls._from_built(file_name, built)
        except (KeyError, ValueError) as e:
            msg: str = f"Failed to load built\n{built}"
            raise ValueError(mp.core.utils.trim_values(msg)) from e
        else:
            return metadata

    @classmethod
    def from_non_built(cls, file_name: str, non_built: _NBT) -> Self:
        """Create the object from a "non-built" typed dict.

        Args:
            file_name: the built component's file name
            non_built: the non-built typed dict object representation

        Returns:
            A new instance of the Buildable object

        Raises:
            ValueError: when the non-built object failed to be loaded

        """
        try:
            metadata: Self = cls._from_non_built(file_name, non_built)
        except (KeyError, ValueError) as e:
            msg: str = f"Failed to load non-built\n{non_built}"
            raise ValueError(mp.core.utils.trim_values(msg)) from e
        else:
            return metadata


class ScriptMetadata(BuildableScript[_BT, _NBT], abc.ABC, Generic[_BT, _NBT]):
    @classmethod
    @abc.abstractmethod
    def from_built_integration_path(cls, path: pathlib.Path) -> list[Self]:
        """Create the script's metadata object from the built integration's path.

        Args:
            path: The path to the built metadata component

        Returns:
            A metadata object

        """

    @classmethod
    @abc.abstractmethod
    def from_non_built_integration_path(cls, path: pathlib.Path) -> list[Self]:
        """Create the script's metadata object from the non-built integration's path.

        Args:
            path: The path to the non-built metadata component

        Returns:
            A metadata object

        """

    @classmethod
    def _from_built_integration_path(cls, metadata_path: pathlib.Path) -> Self:
        """Create the script's metadata object from the built integration's path.

        Args:
            metadata_path: The path to the built metadata component

        Returns:
            A metadata object

        Raises:
            ValueError: when the built JSON failed to be loaded

        """
        built_content: str = metadata_path.read_text(encoding="utf-8")
        try:
            metadata_json: _BT = json.loads(built_content)
            built: Self = cls.from_built(metadata_path.stem, metadata_json)
        except (ValueError, json.JSONDecodeError) as e:
            msg: str = f"Failed to load json from {metadata_path}\n{built_content}"
            raise ValueError(mp.core.utils.trim_values(msg)) from e
        else:
            return built

    @classmethod
    def _from_non_built_integration_path(cls, metadata_path: pathlib.Path) -> Self:
        """Create the script's metadata object from the non-built integration's path.

        Args:
            metadata_path: The path to the non-built metadata component

        Returns:
            A metadata object

        Raises:
            ValueError: when the non-built YAML failed to be loaded

        """
        non_built_content: str = metadata_path.read_text(encoding="utf-8")
        try:
            metadata_json: _NBT = yaml.safe_load(non_built_content)
            non_built: Self = cls.from_non_built(metadata_path.stem, metadata_json)
        except (ValueError, yaml.YAMLError) as e:
            msg: str = f"Failed to load yaml from {metadata_path}\n{non_built_content}"
            raise ValueError(mp.core.utils.trim_values(msg)) from e
        else:
            return non_built


class SequentialMetadata(Buildable[_BT, _NBT], abc.ABC, Generic[_BT, _NBT]):
    @classmethod
    @abc.abstractmethod
    def from_built_integration_path(cls, path: pathlib.Path) -> list[Self]:
        """Create the script's metadata object from the built integration's path.

        Args:
            path: The path to the built metadata component

        Returns:
            A metadata object

        """

    @classmethod
    @abc.abstractmethod
    def from_non_built_integration_path(cls, path: pathlib.Path) -> list[Self]:
        """Create the script's metadata object from the non-built integration's path.

        Args:
            path: The path to the non-built metadata component

        Returns:
            A metadata object

        """

    @classmethod
    def _from_built_integration_path(cls, meta_path: pathlib.Path) -> list[Self]:
        """Create the script's metadata object from the built integration's path.

        Args:
            meta_path: The path to the built metadata component

        Returns:
            A metadata object

        Raises:
            ValueError: when the built JSON failed to be loaded

        """
        built: str = meta_path.read_text(encoding="utf-8")
        try:
            content: list[_BT] = json.loads(built)
            results: list[Self] = [cls.from_built(c) for c in content]
        except (ValueError, json.JSONDecodeError) as e:
            msg: str = f"Failed to load json from {meta_path}\n{built}"
            raise ValueError(mp.core.utils.trim_values(msg)) from e
        else:
            return results

    @classmethod
    def _from_non_built_integration_path(cls, meta_path: pathlib.Path) -> list[Self]:
        """Create the script's metadata object from the non-built integration's path.

        Args:
            meta_path: The path to the non-built metadata component

        Returns:
            A metadata object

        """
        non_built: str = meta_path.read_text(encoding="utf-8")
        return cls.from_non_built_str(non_built)

    @classmethod
    def from_non_built_str(cls, raw_text: str) -> list[Self]:
        """Create the script's metadata object from the non-built integration's raw text.

        Args:
            raw_text: The path to the built metadata component

        Returns:
            A metadata object

        Raises:
            ValueError: when the built JSON failed to be loaded

        """
        try:
            content: list[_NBT] = yaml.safe_load(raw_text)
            results: list[Self] = [cls.from_non_built(c) for c in content]
        except (ValueError, yaml.YAMLError) as e:
            msg: str = "Failed to load yaml."
            raise ValueError(mp.core.utils.trim_values(msg)) from e
        else:
            return results
