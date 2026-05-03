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
from urllib.parse import urljoin


class IronportEndpoints:
    headers = {"Content-Type": "application/json"}
    api_host_format = "esa/api/v2.0/"

    @staticmethod
    def get_login(api_root):
        return urljoin(api_root, "login")

    @staticmethod
    def get_messages(api_root):
        return urljoin(api_root, "message-tracking/messages")

    @staticmethod
    def get_reports(api_root, report_type):
        return urljoin(api_root, f"reporting/{report_type}")
