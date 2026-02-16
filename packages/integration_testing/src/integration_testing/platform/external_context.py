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

import dataclasses
from typing import TYPE_CHECKING, Generic, TypeVar

from TIPCommon.data_models import DatabaseContextType
from TIPCommon.utils import none_to_default_value

if TYPE_CHECKING:
    from collections.abc import Sequence

    from TIPCommon.types import SingleJson

_T = TypeVar("_T")

_KEY_GROUP_SEPARATOR: str = "␝"


class MockExternalContext(Generic[_T]):
    __slots__: tuple[str] = ("_rows",)

    def __init__(self, rows: list[ExternalContextRow[_T]] | None = None) -> None:
        rows: list[ExternalContextRow[_T]] = none_to_default_value(rows, [])
        self._rows: SingleJson = {
            _create_key(r.context_type, r.identifier, r.property_key): r.property_value
            for r in rows
        }

    def __contains__(self, item: _T) -> bool:
        return (
            self.has_row(item)
            if isinstance(item, ExternalContextRow | ExternalContextRowKey)
            else False
        )

    def __repr__(self) -> str:
        return f"{MockExternalContext.__name__}(_rows={self._rows})"

    @property
    def number_of_rows(self) -> int:
        return len(self._rows)

    def has_row(self, row: ExternalContextRow[_T] | ExternalContextRowKey) -> bool:
        """Check whether a row is in the context.

        Args:
            row: A ExternalContextRow object

        Returns:
            True if the row exists in the context else False

        """
        key: str = _create_key(row.context_type, row.identifier, row.property_key)
        if isinstance(row, ExternalContextRow):
            return key in self._rows and self._rows[key] == row.property_value

        if isinstance(row, ExternalContextRowKey):
            return key in self._rows

        msg: str = (
            "Row type must be either ExternalContextRow or ExternalContextRowKey, "
            f"but received {type(row)}"
        )
        raise TypeError(msg)

    def get_row_value(
        self,
        context_type: DatabaseContextType,
        identifier: str,
        property_key: str,
    ) -> _T | None:
        """Get a specific row property value.

        Args:
            context_type: The context type of the row
            identifier: The identifier of the row
            property_key: The property key of the row

        Returns:
            The property value of the row from the external context.
            If the value cannot be found, it returns None

        """
        key: str = _create_key(context_type, identifier, property_key)
        return self._rows.get(key)

    def set_row_value(
        self,
        context_type: DatabaseContextType,
        identifier: str,
        property_key: str,
        property_value: _T,
    ) -> None:
        """Set specific row property value.

        Args:
            context_type: The context type of the row to set
            identifier: The identifier of the row to set
            property_key: The property key of the row to set
            property_value: The property value of the row to set

        """
        key: str = _create_key(context_type, identifier, property_key)
        self._rows[key] = property_value

    def delete_row(
        self,
        context_type: DatabaseContextType,
        identifier: str,
        property_key: str,
    ) -> None:
        """Delete a row from the external context.

        Args:
            context_type: The context type of the row to delete
            identifier: The identifier of the row to delete
            property_key: The property key of the row to delete

        Raises:
            ValueError: If the row cannot be found

        """
        key: str = _create_key(context_type, identifier, property_key)

        if key not in self._rows:
            msg: str = (
                "Could not find a value in the external context using the provided parameters"
            )
            raise ValueError(msg)

        del self._rows[key]

    def set_rows(self, rows: Sequence[ExternalContextRow[_T]]) -> MockExternalContext:
        """Set a list of rows in the context.

        Args:
            rows: The rows to set

        Returns:
            Self

        """
        self._rows.update(
            {
                _create_key(
                    r.context_type,
                    r.identifier,
                    r.property_key,
                ): r.property_value
                for r in rows
            },
        )

        return self

    def delete_rows(
        self,
        rows: Sequence[ExternalContextRow[_T] | ExternalContextRowKey],
    ) -> MockExternalContext:
        """Delete multiple rows from the external context.

        Args:
            rows: The rows to delete

        Raises:
            ValueError: If any of the rows cannot be found.
                Found rows are still deleted.

        Returns:
            Self

        """
        not_found_rows: list[ExternalContextRow[_T] | ExternalContextRowKey] = []
        for row in rows:
            key: str = _create_key(row.context_type, row.identifier, row.property_key)

            if key not in self._rows:
                not_found_rows.append(row)
                continue

            del self._rows[key]

        if not_found_rows:
            msg: str = (
                "Could not find a value in the external context for the following "
                f"rows: {', '.join(map(str, not_found_rows))}"
            )
            raise ValueError(msg)

        return self

    def drop(self) -> MockExternalContext[_T]:
        """Drop the entire context (clean it).

        Returns:
            Self

        """
        self._rows.clear()

        return self


def _create_key(context_type: int | DatabaseContextType, identifier: str, property_key: str) -> str:
    if isinstance(context_type, DatabaseContextType):
        context_type: int = context_type.value

    keys: tuple[int, str, str] = (context_type, identifier, property_key)
    return _KEY_GROUP_SEPARATOR.join(map(str, keys))


@dataclasses.dataclass(frozen=True, slots=True)
class ExternalContextRow(Generic[_T]):
    context_type: DatabaseContextType
    identifier: str
    property_key: str
    property_value: _T


@dataclasses.dataclass(frozen=True, slots=True)
class ExternalContextRowKey:
    context_type: DatabaseContextType
    identifier: str
    property_key: str
