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

"""Data models for the Akeyless integration."""

from __future__ import annotations

import dataclasses

from .constants import DEFAULT_API_GATEWAY_URL


@dataclasses.dataclass(frozen=True, slots=True)
class AkeylessClientConfig:
    """Configuration parameters for the Akeyless API client."""

    access_id: str
    access_key: str
    api_gateway_url: str = DEFAULT_API_GATEWAY_URL
    verify_ssl: bool = True


@dataclasses.dataclass(frozen=True, slots=True)
class ComponentTarget:
    """Resolved SOAR component display name and identifier."""

    name: str
    identifier: str
