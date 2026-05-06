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

import urllib.parse

from .ObserveITConstants import GET, POST


class ObserveITEndpoints:
    @staticmethod
    def get_authorization_endpoint(api_root):
        # type: (str or unicode) -> (str or unicode, str or unicode)
        """Get method and endpoint to call with
        @param api_root: API Root
        @return: Method and Endpoint
        """
        return POST, urllib.parse.urljoin(api_root, "/v2/apis/auth/oauth/token")

    @staticmethod
    def get_test_connectivity_endpoint(api_root):
        # type: (str or unicode) -> (str or unicode, str or unicode)
        """Get method and endpoint to call with
        @param api_root: API Root
        @return: Method and Endpoint
        """
        return GET, urllib.parse.urljoin(
            api_root, "/v2/apis/report;realm=observeit/_health"
        )

    @staticmethod
    def get_alerts_endpoint(api_root):
        # type: (str or unicode) -> (str or unicode, str or unicode)
        """Get method and endpoint to call with
        @param api_root: API Root
        @return: Method and Endpoint
        """
        return GET, urllib.parse.urljoin(
            api_root, "/v2/apis/report;realm=observeit/reports/alert_v0/data"
        )
