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

from .api_manager import GoogleCloudIdentityApiManager
from .authentication_manager import AuthManager
from .utils import IntegrationParameters

if TYPE_CHECKING:
    from .action_wrapper import ActionContext


def build_auth_manager(context: ActionContext) -> AuthManager:
    """Build an authentication manager from the action context.

    Args:
        context: The action context containing integration parameters.

    Returns:
        An instance of AuthManager.

    """
    params = IntegrationParameters(context)
    return AuthManager(
        service_account_creds=params.service_account_json,
        workload_identity_email=params.workload_identity_email,
        delegated_email=params.delegated_email,
        verify_ssl=params.verify_ssl,
    )


def build_api_manager(context: ActionContext) -> GoogleCloudIdentityApiManager:
    """Build a Google Cloud Identity API manager from the action context.

    Args:
        context: The action context.

    Returns:
        An instance of GoogleCloudIdentityApiManager.

    """
    auth_manager = build_auth_manager(context)
    return GoogleCloudIdentityApiManager(
        session=auth_manager.prepare_session(), logger=context.get_logger()
    )
