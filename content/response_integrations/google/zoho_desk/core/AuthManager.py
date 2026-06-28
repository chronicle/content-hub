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

from TIPCommon.base.interfaces import Authable
from zoho_desk.core.datamodels import IntegrationParameters


class AuthenticateSession(Authable[IntegrationParameters]):

    def authenticate_session(self, params: IntegrationParameters) -> None:
        self.session.verify = params.verify_ssl
        self.session.headers.update(
            {"Authorization": f"Zoho-oauthtoken {params.oauth_token}"}
        )
