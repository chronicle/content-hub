# Copyright 2026 Google LLC
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

from dataclasses import dataclass
from typing import TYPE_CHECKING

from TIPCommon.transformation import dict_to_flat

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


class BaseModel:
    """Base model class representing structured API response data."""

    def __init__(self, raw_data: SingleJson) -> None:
        """Initialize the model with raw JSON data."""
        self.raw_data = raw_data

    def to_json(self) -> SingleJson:
        """Return the raw JSON representation of the model.

        Returns:
            The raw JSON data dictionary.

        """
        return self.raw_data

    def to_flat(self) -> SingleJson:
        """Return a flattened JSON representation of the model.

        Returns:
            A flattened JSON data dictionary.

        """
        return dict_to_flat(self.to_json())

    def to_csv(self) -> SingleJson:
        """Return a flat JSON representation suitable for CSV conversion.

        Returns:
            A flat JSON data dictionary.

        """
        return self.to_flat()


class Account(BaseModel):
    """Account data model class."""

    def to_csv(self) -> SingleJson:
        """Return a filtered flat JSON representation of account data suitable for CSV.

        Returns:
            A filtered flat JSON data dictionary.

        """
        flat_dict = self.to_flat()
        return {
            "Id": flat_dict.get("id"),
            "Safe Name": flat_dict.get("safeName"),
            "User Name": flat_dict.get("userName"),
            "Secret Type": flat_dict.get("secretType"),
        }


@dataclass
class IntegrationParameters:
    """Integration parameters for CyberArk PAM."""

    api_root: str
    username: str
    password: str
    verify_ssl: bool
    ca_certificate: str | None
    client_certificate: str | None
    client_certificate_passphrase: str | None


@dataclass
class ListAccountsQuery:
    """Query parameters for listing accounts in CyberArk PAM."""

    search: str | None = None
    searchType: str | None = None  # ruff:ignore[mixed-case-variable-in-class-scope]
    offset: int | None = None
    limit: int | None = None
    filter: str | None = None
    savedfilter: str | None = None

    def as_query(self) -> SingleJson:
        """Convert the dataclass into a query parameters dictionary.

        Returns:
            A dictionary containing not-None query parameters.

        """
        return {key: value for key, value in self.__dict__.items() if value is not None}
