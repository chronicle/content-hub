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

from typing import TYPE_CHECKING

from ..core.data_models import AzureLogEntry

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


def parse_azure_monitor_response(response_json: SingleJson) -> list[AzureLogEntry]:
    """Parse Azure Monitor API response into list of JSON entries.
    Args:
        response_json (dict): Raw response from Azure Monitor API.

    Returns:
        list[AzureLogEntry]: Transformed list of entries.
    """
    return list(AzureLogEntry.from_json(response_json))
