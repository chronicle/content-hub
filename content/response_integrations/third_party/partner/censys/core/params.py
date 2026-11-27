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

import dataclasses


@dataclasses.dataclass(frozen=True, slots=True)
class IntegrationParams:
    """Censys integration configuration shared by every action.

    Attributes:
        use_oauth: True to authenticate with OAuth, False to use the API Key.
        api_key: Censys API Key; required when ``use_oauth`` is False.
        client_id: OAuth Client ID; required when ``use_oauth`` is True.
        client_secret: OAuth Client Secret; required when ``use_oauth`` is True.
        organization_id: Censys Organization ID.
        verify_ssl: Whether to verify SSL certificates.
    """

    organization_id: str
    verify_ssl: bool = True
    use_oauth: bool = False
    api_key: str = dataclasses.field(default="", repr=False)
    client_id: str = ""
    client_secret: str = dataclasses.field(default="", repr=False)
