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
from .CBResponseManager import CBResponseManager

API_ENDPOINTS = {
    "create_alert_for_watchlist": "{}/api/v1/watchlist/{}/action_type/alert"
}


class CBResponseManager6_3(CBResponseManager):
    def __init__(self, *args, **kwargs):
        super(CBResponseManager6_3, self).__init__(*args, **kwargs)

    def create_alert_action_for_watchlist(self, watchlist_id):
        """
        Create an alert action for watchlist
        :param watchlist_id: {int} watchlist ID
        :return:
        """
        url = API_ENDPOINTS["create_alert_for_watchlist"].format(
            self.api_root, watchlist_id
        )
        body = {"enabled": True}
        response = self.session.put(url, json=body)
        return self.validate_response(response)
