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

from soar_sdk.SiemplifyAction import SiemplifyAction

from .datamodels import IntegrationParameters
from .GSuiteAuth import build_auth_manager
from .GSuiteManager import GSuiteManager


def create_api_client(soar_action: SiemplifyAction) -> GSuiteManager:
    auth_manager = build_auth_manager(soar_action)

    return GSuiteManager(
        auth_manager.prepare_session(),
        IntegrationParameters(siemplify_logger=soar_action.LOGGER),
    )
