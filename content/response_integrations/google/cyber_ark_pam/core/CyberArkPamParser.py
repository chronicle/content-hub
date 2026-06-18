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

from TIPCommon.types import SingleJson

from .datamodels import Account


class CyberArkPamParser:
    def build_account(self, account_json: SingleJson) -> Account:
        return Account(account_json)

    def build_accounts(self, json_response: SingleJson) -> list[Account]:
        accounts_json = json_response["value"]
        return [self.build_account(account_json) for account_json in accounts_json]
