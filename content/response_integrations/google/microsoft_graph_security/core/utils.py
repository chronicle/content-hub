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

from dataclasses import dataclass

from TIPCommon.types import ChronicleSOAR
from microsoft_graph_security.core import constants
from microsoft_graph_security.core.MicrosoftGraphSecurityManager import (
    MicrosoftGraphSecurityManager,
    MicrosoftGraphSecurityManagerV2,
)


@dataclass(slots=True)
class GraphSecurityManagerConfig:
    client_id: str
    secret_id: str
    certificate_path: str
    certificate_password: str
    tenant: str
    verify_ssl: bool
    chronicle_soar: ChronicleSOAR
    api_root: str = constants.DEFAULT_API_ROOT
    login_api_root: str = constants.DEFAULT_LOGIN_API_ROOT


def init_graph_security_manager(
    config: GraphSecurityManagerConfig,
    use_v2_api: bool,
) -> MicrosoftGraphSecurityManager | MicrosoftGraphSecurityManagerV2:
    """Returns the correct Microsoft Graph Security Manager based on API version.
    Args:
        config(GraphSecurityManagerConfig): Configuration params.
        use_v2_api(bool): If true, alerts V2 API is used.

    Returns:
        MicrosoftGraphSecurityManager | MicrosoftGraphSecurityManagerV2: Microsoft Graph
        Security Manager.
    """
    manager_class = (
        MicrosoftGraphSecurityManagerV2 if use_v2_api else MicrosoftGraphSecurityManager
    )
    return manager_class(
        client_id=config.client_id,
        client_secret=config.secret_id,
        certificate_path=config.certificate_path,
        certificate_password=config.certificate_password,
        tenant=config.tenant,
        verify_ssl=config.verify_ssl,
        api_root=config.api_root,
        login_api_root=config.login_api_root,
        siemplify=config.chronicle_soar,
    )
