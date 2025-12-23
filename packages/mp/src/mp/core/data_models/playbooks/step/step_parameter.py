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

from typing import Annotated, NotRequired, Self, TypedDict

import pydantic

import mp.core.constants
from mp.core.data_models.abc import Buildable


class BuiltStepParameter(TypedDict):
    ParentStepIdentifier: str
    ParentWorkflowIdentifier: str
    Name: str
    Value: str | None


class NonBuiltStepParameter(TypedDict):
    step_id: str
    playbook_id: str
    name: str
    value: NotRequired[str | None]


class StepParameter(Buildable[BuiltStepParameter, NonBuiltStepParameter]):
    step_id: str
    playbook_id: str
    name: Annotated[
        str,
        pydantic.Field(
            max_length=mp.core.constants.PARAM_NAME_MAX_LENGTH,
            pattern=mp.core.constants.PARAM_DISPLAY_NAME_REGEX,
        ),
    ]
    value: str | None = None

    @classmethod
    def _from_built(cls, built: BuiltStepParameter) -> Self:
        """Create the obj from a built action param dict.

        Args:
            built: the built dict

        Returns:
            An `ActionParameter` object

        """
        return cls(
            step_id=built["ParentStepIdentifier"],
            playbook_id=built["ParentWorkflowIdentifier"],
            name=built["Name"],
            value=built["Value"],
        )

    @classmethod
    def _from_non_built(cls, non_built: NonBuiltStepParameter) -> Self:
        """Create the obj from a non-built action param dict.

        Args:
            non_built: the non-built dict

        Returns:
            An `ActionParameter` object

        """
        return cls(
            step_id=non_built["step_id"],
            playbook_id=non_built["playbook_id"],
            name=non_built["name"],
            value=non_built.get("value"),
        )

    def to_built(self) -> BuiltStepParameter:
        """Convert the StepParameter to its "built" representation.

        Returns:
            A BuiltStepParameter dictionary.

        """
        return BuiltStepParameter(
            ParentStepIdentifier=self.step_id,
            ParentWorkflowIdentifier=self.playbook_id,
            Name=self.name,
            Value=self.value,
        )

    def to_non_built(self) -> NonBuiltStepParameter:
        """Convert the StepParameter to its "non-built" representation.

        Returns:
            A NonBuiltStepParameter dictionary.

        """
        non_built: NonBuiltStepParameter = NonBuiltStepParameter(
            step_id=self.step_id,
            playbook_id=self.playbook_id,
            name=self.name,
            value=self.value,
        )
        return non_built
