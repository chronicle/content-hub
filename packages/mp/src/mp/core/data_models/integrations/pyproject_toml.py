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

from typing import Annotated, Self, TypedDict, cast

import pydantic
import toml

import mp.core.constants
import mp.core.utils

from .integration_meta.metadata import PythonVersion


class PyProjectTomlFile(TypedDict):
    project: dict[str, str]


class PyProjectToml(pydantic.BaseModel):
    project: PyProjectAttrs

    @classmethod
    def model_load(cls, pyproject_toml: PyProjectTomlFile) -> Self:
        """Load and parse a pyproject.toml file to instantiate a class.

        Args:
            pyproject_toml: The loaded PyProjectToml dict

        Returns:
            An instance of the class initialized with the
            project details from the pyproject.toml file.

        """
        return cls(project=PyProjectAttrs.model_load(pyproject_toml["project"]))

    @classmethod
    def from_toml_str(cls, text: str) -> Self:
        """Load a toml string into a PyProjectToml object.

        Args:
            text: the string to parse into a PyProjectToml object.

        Returns:
            a `PyProjectToml` object.

        """
        pyproject_data: PyProjectTomlFile = cast("PyProjectTomlFile", toml.loads(text))
        return cls.model_load(pyproject_data)


class PyProjectAttrs(pydantic.BaseModel):
    requires_python: PythonVersion
    version: Annotated[pydantic.PositiveFloat, pydantic.Field(ge=1.0)]
    description: Annotated[
        str,
        pydantic.Field(max_length=mp.core.constants.LONG_DESCRIPTION_MAX_LENGTH),
    ]

    @classmethod
    def model_load(cls, project: dict[str, str]) -> PyProjectAttrs:
        """Load a project dictionary and initialize a PyProjectAttrs instance.

        Args:
            project: A dictionary containing project metadata, notably
                the required Python version under the key "requires-python", and
                additional keys such as "version" and "description" to initialize the
                instance attributes.

        Returns:
            An instance of PyProjectAttrs initialized with the parsed
            data from the provided project dictionary.

        """
        pyv: str = mp.core.utils.get_python_version_from_version_string(
            project["requires-python"],
        )
        return cls(
            requires_python=PythonVersion.from_string(pyv),
            version=float(project["version"]),
            description=project["description"],
        )
