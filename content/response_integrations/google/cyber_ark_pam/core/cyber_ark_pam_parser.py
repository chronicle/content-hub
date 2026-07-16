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

from typing import TYPE_CHECKING, Any

from .datamodels import Account

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


class CyberArkPamParser:
    """CyberArk PAM Response Parser."""

    @staticmethod
    def build_account(account_json: SingleJson) -> Account:
        """Build an Account object from raw JSON.

        Returns:
            The parsed Account data model object.

        """
        return Account(account_json)

    @staticmethod
    def build_accounts(json_response: SingleJson) -> list[Account]:
        """Build a list of Account objects from raw JSON response.

        Returns:
            A list of parsed Account data model objects.

        """
        accounts_json = json_response["value"]

        return [
            CyberArkPamParser.build_account(account_json)
            for account_json in accounts_json
        ]

    @staticmethod
    def build_versions(json_response: SingleJson | list[Any]) -> list[Any]:
        """Build a list of version objects/values from raw JSON response.

        Returns:
            A list of secret versions.

        """
        if isinstance(json_response, dict) and "value" in json_response:
            return json_response["value"]
        if isinstance(json_response, list):
            return json_response

        return [json_response]
