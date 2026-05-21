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
class IronportRequestData:
    @staticmethod
    def get_token_request_data(username, password):
        payload = {"data": {"userName": username, "passphrase": password}}

        params = {}
        return payload, params

    @staticmethod
    def get_messages_request_data(start_date, end_date, offset=0, limit=None):
        payload = {}

        params = {
            "searchOption": "messages",
            "startDate": start_date,
            "endDate": end_date,
            "offset": offset,
        }

        if limit:
            params["limit"] = limit

        return payload, params

    @staticmethod
    def get_reports_request_data(start_date, end_date, device_type, query_type):
        payload = {}

        params = {
            "startDate": start_date,
            "endDate": end_date,
            "device_type": device_type,
            "query_type": query_type,
        }

        return payload, params
