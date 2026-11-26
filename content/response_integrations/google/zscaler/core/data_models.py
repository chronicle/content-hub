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

@dataclasses.dataclass(slots=True)
class IntegrationParameters:
    api_root: str
    login_id: str | None = None
    api_key: str | None = None
    password: str | None = None
    verify_ssl: bool = False
    client_id: str | None = None
    client_secret: str | None = None
    login_api_root: str | None = None
