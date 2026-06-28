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

from palo_alto_cortex_xdr.core.auth import AuthenticatedSession
from palo_alto_cortex_xdr.core.utils import get_integration_parameters
from palo_alto_cortex_xdr.core.XDRManager import ApiParameters, XDRManager


if TYPE_CHECKING:
    import requests

    from TIPCommon.types import ChronicleSOAR

    from palo_alto_cortex_xdr.core.datamodels import IntegrationParameters


def create_api_client(soar_action: ChronicleSOAR) -> XDRManager:
    """Create XDRManager ApiManager client object.

    Args:
        soar_action (ChronicleSOAR): SiemplifyAction object.

    Returns:
        XDRManager: XDRManager object.
    """
    params: IntegrationParameters = get_integration_parameters(soar_action)
    authenticator: AuthenticatedSession[IntegrationParameters] = AuthenticatedSession()
    session: requests.Session = authenticator.authenticate_session(params)
    api_params: ApiParameters = ApiParameters(api_root=params.api_root)

    return XDRManager(
        session=session,
        api_params=api_params,
        logger=soar_action.LOGGER,
    )
