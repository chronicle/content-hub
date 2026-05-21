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

API_ENDPOINTS = {"get_alerts": "{}/api/v1/alert"}


class CBResponseManager5_1(CBResponseManager):
    def __init__(self, *args, **kwargs):
        super(CBResponseManager5_1, self).__init__(*args, **kwargs)

    def get_alerts(self, query):
        """
        Get all alerts from CB Response
        :param query: {str} The query to filter te alerts by
        :return: {list} List of the alerts info (Alert)
        """
        url = API_ENDPOINTS["get_alerts"].format(self.api_root)
        params = {"q": query}
        alerts = self._paginate_results("GET", url, params=params)
        return [
            self.parser.build_siemplify_alert_obj(alert_json) for alert_json in alerts
        ]
