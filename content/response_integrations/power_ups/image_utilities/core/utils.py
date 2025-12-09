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

from .exceptions import RemoteAgentRequiredError

if TYPE_CHECKING:
    from TIPCommon.types import ChronicleSOAR


def ensure_remote_agent(chronicle_soar: ChronicleSOAR, script_name: str) -> None:
    """Ensure the script is running on a Remote Agent.

    Args:
        chronicle_soar: The ChronicleSoar object.
        script_name: The name of the script/action.

    Raises:
        RemoteAgentRequiredError: If the script is not running on a Remote Agent.

    """
    error_message: str = f"{script_name} can only be executed on a Remote Agent."
    if not getattr(chronicle_soar, "is_remote", False):
        raise RemoteAgentRequiredError(error_message)
