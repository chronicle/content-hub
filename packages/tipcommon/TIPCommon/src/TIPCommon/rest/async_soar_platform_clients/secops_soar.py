# Copyright 2025 Google LLC
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

from typing import TYPE_CHECKING

import httpx

from TIPCommon.utils import get_sdk_api_uri
from TIPCommon.rest.async_soar_platform_clients.constants import (
    HTTP_CONNECT_TIMEOUT_SECONDS,
    HTTP_MAX_CONNECTIONS,
    HTTP_MAX_KEEP_ALIVE_CONNECTIONS,
    HTTP_POOL_TIMEOUT_SECONDS,
    HTTP_READ_TIMEOUT_SECONDS,
    HTTP_WRITE_TIMEOUT_SECONDS,
)

if TYPE_CHECKING:
    from TIPCommon.types import ChronicleSOAR


class AsyncChronicleSOAR:
    """
    Async wrapper around existing ChronicleSOAR SDK object.
    Owns transport, headers, SSL, logging.
    """

    def __init__(self, chronicle_soar: ChronicleSOAR) -> None:
        self.api_root = get_sdk_api_uri(chronicle_soar).rstrip("/")
        self.logger = chronicle_soar.LOGGER
        self.headers = {
            "AppKey": getattr(chronicle_soar, "api_key", ""),
        }
        self.client = httpx.AsyncClient(
            base_url=self.api_root,
            headers=self.headers,
            verify=getattr(chronicle_soar.session, "verify", True),
            timeout=httpx.Timeout(
                connect=HTTP_CONNECT_TIMEOUT_SECONDS,
                read=HTTP_READ_TIMEOUT_SECONDS,
                write=HTTP_WRITE_TIMEOUT_SECONDS,
                pool=HTTP_POOL_TIMEOUT_SECONDS,
            ),
            limits=httpx.Limits(
                max_keepalive_connections=HTTP_MAX_KEEP_ALIVE_CONNECTIONS,
                max_connections=HTTP_MAX_CONNECTIONS,
            ),
        )

    async def close(self) -> None:
        await self.client.aclose()
