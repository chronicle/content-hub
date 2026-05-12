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
import requests


class WebhookManager:

    def __init__(self, base_url, token_id="", verify_ssl=True):
        self.base_url = base_url
        self.token_id = token_id
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update({"Content-Type": "application/json"})

    def get_request(self, sorting="newest"):
        url = f"{self.base_url}/token/{self.token_id}/requests?sorting={sorting}"
        response = self.session.get(url)
        return response

    def get_data(self, *args, **kwargs):
        response = self.get_request(*args, **kwargs)
        res = self._get_validated_response(response)
        data = res.get("data")
        return data

    def _get_validated_response(self, response):
        try:
            res_json = response.json()
        except Exception as _:
            raise Exception(response.content)
        try:
            response.raise_for_status()
        except Exception as _:
            raise Exception(res_json)
        return res_json
