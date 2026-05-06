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

"""ThreatConnect V3 request authenticators."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from urllib.parse import urlparse

import requests
from requests.auth import AuthBase


class ThreatConnectV3Auth(AuthBase):
    """ThreatConnect V3 HMAC-SHA256 Request Authenticator."""

    def __init__(self, api_access_id: str, api_secret_key: str) -> None:
        self.api_access_id = api_access_id
        self.api_secret_key = api_secret_key

    def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
        """Sign the outgoing PreparedRequest using custom ThreatConnect HMAC signature.

        Returns:
            requests.PreparedRequest: The signed prepared request.

        """
        timestamp = str(int(time.time()))
        url_str = r.url.decode("utf-8") if isinstance(r.url, bytes) else (r.url or "")
        parsed_url = urlparse(url_str)
        path = parsed_url.path
        if parsed_url.query:
            path = f"{path}?{parsed_url.query}"

        method = (r.method or "GET").upper()
        signature_string = f"{path}:{method}:{timestamp}"

        hmac_obj = hmac.new(
            self.api_secret_key.encode("utf-8"),
            signature_string.encode("utf-8"),
            hashlib.sha256,
        )
        signature = base64.b64encode(hmac_obj.digest()).decode("utf-8")

        r.headers["Authorization"] = f"TC {self.api_access_id}:{signature}"
        r.headers["Timestamp"] = timestamp

        return r


class AuthenticatedSession(requests.Session):
    """Requests Session configured with ThreatConnect V3 Auth."""

    def __init__(self, api_access_id: str, api_secret_key: str) -> None:
        super().__init__()
        self.auth = ThreatConnectV3Auth(api_access_id, api_secret_key)
