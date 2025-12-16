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

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, NotRequired, Self, TypedDict

import pydantic

import mp.core.constants
import mp.core.utils
from mp.core.data_models.abc import SequentialMetadata

if TYPE_CHECKING:
    from pathlib import Path


def convert_epoch_to_iso(epoch_timestamp: int) -> str:
    """Convert an epoch timestamp into a UTC ISO 8601 formatted string.

    Args:
        epoch_timestamp: The number of seconds since 1970-01-01 00:00:00 UTC.

    Returns:
        A string in the format 'YYYY-MM-DD'.

    """
    dt_object: datetime = datetime.fromtimestamp(epoch_timestamp, tz=UTC)
    return dt_object.strftime("%Y-%m-%d")


def convert_iso_to_epoch(iso_timestamp: str) -> int:
    """Convert a 'YYYY-MM-DD' formatted string into an epoch timestamp.

    This represents the start of the day (00:00:00) in UTC.

    Args:
        iso_timestamp : A string in the format 'YYYY-MM-DD'.

    Returns:
        The epoch time

    Raises:
        ValueError: If the iso_timestamp is not in 'YYYY-MM-DD' format.

    """
    try:
        dt_object: datetime = datetime.strptime(iso_timestamp, "%Y-%m-%d")  # noqa: DTZ007
        # Make it timezone-aware (UTC) to the beginning of the day before getting the epoch time
        dt_object = dt_object.replace(tzinfo=UTC)
        return int(dt_object.timestamp())
    except Exception as e:
        msg = f"Invalid date format for '{iso_timestamp}'. The expected format is 'YYYY-MM-DD'."
        raise ValueError(msg) from e


class BuiltReleaseNote(TypedDict):
    ChangeDescription: str
    Deprecated: bool
    New: bool
    ItemName: str
    ItemType: str
    PublishTime: int | None
    Regressive: bool
    Removed: bool
    TicketNumber: str | None
    IntroducedInIntegrationVersion: float


class NonBuiltReleaseNote(TypedDict):
    description: str
    deprecated: NotRequired[bool]
    integration_version: float
    item_name: str
    item_type: str
    publish_time: NotRequired[str | None]
    regressive: NotRequired[bool]
    removed: NotRequired[bool]
    ticket_number: NotRequired[str | None]
    new: NotRequired[bool]


class ReleaseNote(SequentialMetadata[BuiltReleaseNote, NonBuiltReleaseNote]):
    description: Annotated[
        str,
        pydantic.Field(max_length=mp.core.constants.LONG_DESCRIPTION_MAX_LENGTH),
    ]
    deprecated: bool = False
    new: bool = False
    item_name: str
    item_type: str
    publish_time: int | None
    regressive: bool = False
    removed: bool = False
    ticket: str | None
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
            A sequence of `ReleaseNote` objects

        """
        rn_path: Path = path / mp.core.constants.RN_JSON_FILE
        if not rn_path.exists():
            return []

        return cls._from_built_path(rn_path)

    @classmethod
    def from_non_built_path(cls, path: Path) -> list[Self]:
        """Create based on the metadata files found in the non-built-integration path.

        Args:
            path: the path to the non-built integration

        Returns:
            A sequence of `ReleaseNote` objects

        """
        rn_path: Path = path / mp.core.constants.RELEASE_NOTES_FILE
        if not rn_path.exists():
            return []

        return cls._from_non_built_path(rn_path)

    @classmethod
    def _from_built(cls, built: BuiltReleaseNote) -> Self:
        return cls(
            description=built["ChangeDescription"],
            deprecated=built["Deprecated"],
            version=built["IntroducedInIntegrationVersion"],
            item_name=built["ItemName"],
            item_type=built["ItemType"],
            new=built["New"],
            regressive=built["Regressive"],
            removed=built["Removed"],
            ticket=built["TicketNumber"],
            publish_time=built.get("PublishTime"),
        )

    @classmethod
    def _from_non_built(cls, non_built: NonBuiltReleaseNote) -> Self:
        publish_time = non_built.get("publish_time")

        return cls(
            description=non_built["description"],
            deprecated=non_built.get("deprecated", False),
            version=non_built["integration_version"],
            item_name=non_built["item_name"],
            item_type=non_built["item_type"],
            new=non_built.get("new", False),
            regressive=non_built.get("regressive", False),
            removed=non_built.get("removed", False),
            ticket=non_built.get("ticket_number"),
            publish_time=convert_iso_to_epoch(publish_time) if publish_time is not None else None,
        )

    def to_built(self) -> BuiltReleaseNote:
        """Create a built release note metadata dict.

        Returns:
            A built version of the release note metadata dict

        """
        return BuiltReleaseNote(
            ChangeDescription=self.description,
            Deprecated=self.deprecated,
            IntroducedInIntegrationVersion=float(self.version),
            ItemName=self.item_name,
            ItemType=self.item_type,
            New=self.new,
            Regressive=self.regressive,
            Removed=self.removed,
            TicketNumber=self.ticket,
            PublishTime=self.publish_time,
        )

    def to_non_built(self) -> NonBuiltReleaseNote:
        """Create a non-built release note metadata dict.

        Returns:
            A non-built version of the release note metadata dict

        """
        non_built: NonBuiltReleaseNote = NonBuiltReleaseNote(
            description=self.description,
            integration_version=float(self.version),
            item_name=self.item_name,
            item_type=self.item_type,
            publish_time=convert_epoch_to_iso(self.publish_time)
            if self.publish_time is not None
            else None,
            ticket_number=self.ticket,
            new=self.new,
            regressive=self.regressive,
            deprecated=self.deprecated,
            removed=self.removed,
        )
        mp.core.utils.remove_none_entries_from_mapping(non_built)
        return non_built
