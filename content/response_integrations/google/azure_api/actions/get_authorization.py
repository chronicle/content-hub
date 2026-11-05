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
from urllib.parse import urlencode

from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import string_to_multi_value

from ..core.api_utils import get_full_url
from ..core.auth import build_auth_params
from ..core.base_action import BaseAction
from ..core.constants import (
    AUTH_URL_GENERATED_MESSAGE,
    BROWSE_AUTH_LINK_MESSAGE,
    GET_AUTHORIZATION_SCRIPT_NAME,
    INTEGRATION_IDENTIFIER,
    PARAM_OAUTH_SCOPES,
    RESPONSE_MODE_QUERY,
    RESPONSE_TYPE_CODE,
)

if TYPE_CHECKING:
    from typing import Never


class GetAuthorizationAction(BaseAction):
    def __init__(self) -> None:
        super().__init__(GET_AUTHORIZATION_SCRIPT_NAME)
        self.identifier = INTEGRATION_IDENTIFIER
        self.result_value = True

    def _extract_action_parameters(self) -> None:
        """Extract action parameters."""
        self.params.oauth_scopes = string_to_multi_value(
            extract_action_param(
                self.soar_action,
                param_name=PARAM_OAUTH_SCOPES,
                is_mandatory=True,
                print_value=True,
            ),
            only_unique=True,
        )
        self.params.auth_params = build_auth_params(self.soar_action)

    def _validate_params(self) -> None:
        """Validate parameters."""

    def _init_api_clients(self):
        """Initialize API clients."""

    def _get_authorization_url(self) -> str:
        root_url: str = get_full_url(
            api_root=self.params.auth_params.login_api_root,
            endpoint_id="authorize_url",
            tenant_id=self.params.auth_params.tenant_id,
        )
        scope: str = " ".join(self.params.oauth_scopes)
        params: dict[str, str] = {
            "client_id": self.params.auth_params.client_id,
            "redirect_uri": self.params.auth_params.redirect_url,
            "response_type": RESPONSE_TYPE_CODE,
            "response_mode": RESPONSE_MODE_QUERY,
            "scope": f"{scope}",
        }
        return f"{root_url}?{urlencode(params)}"

    def _perform_action(self, _: Never) -> None:
        authorization_url: str = self._get_authorization_url()
        self.logger.info(f"Generated authorization URL: {authorization_url}")
        self.soar_action.result.add_link(BROWSE_AUTH_LINK_MESSAGE, authorization_url)
        self.output_message = AUTH_URL_GENERATED_MESSAGE


def main() -> None:
    action = GetAuthorizationAction()
    action.run()


if __name__ == "__main__":
    main()
