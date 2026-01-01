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

from typing import Self, TypedDict

from mp.core.data_models.abc import Buildable, RepresentableEnum


class PlaybookAccessLevel(RepresentableEnum):
    """Represents the access level for a playbook."""

    NO_ACCESS = 0
    VIEW = 1
    EDIT = 2


class BuiltAccessPermission(TypedDict):
    WorkflowOriginalIdentifier: str
    User: str
    AccessLevel: int


class NonBuiltAccessPermission(TypedDict):
    playbook_id: str
    user: str
    access_level: str


class AccessPermission(Buildable[BuiltAccessPermission, NonBuiltAccessPermission]):
    playbook_id: str
    user: str
    access_level: PlaybookAccessLevel

    @classmethod
    def _from_built(cls, built: BuiltAccessPermission) -> Self:
        return cls(
            playbook_id=built["WorkflowOriginalIdentifier"],
            user=built["User"],
            access_level=PlaybookAccessLevel(int(built["AccessLevel"])),
        )

    @classmethod
    def _from_non_built(cls, non_built: NonBuiltAccessPermission) -> Self:
        return cls(
            playbook_id=non_built["playbook_id"],
            user=non_built["user"],
            access_level=PlaybookAccessLevel.from_string(non_built["access_level"]),
        )

    def to_built(self) -> BuiltAccessPermission:
        """Convert the AccessPermission to its "built" representation.

        Returns:
            A BuiltAccessPermission dictionary.

        """
        return BuiltAccessPermission(
            WorkflowOriginalIdentifier=self.playbook_id,
            User=self.user,
            AccessLevel=self.access_level.value,
        )

    def to_non_built(self) -> NonBuiltAccessPermission:
        """Convert the AccessPermission to its "non-built" representation.

        Returns:
            A NonBuiltAccessPermission dictionary.

        """
        return NonBuiltAccessPermission(
            playbook_id=self.playbook_id,
            user=self.user,
            access_level=self.access_level.to_string(),
        )
