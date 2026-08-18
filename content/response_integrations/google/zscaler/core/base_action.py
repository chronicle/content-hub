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

from abc import ABC

from TIPCommon.base.action import Action

from TIPCommon.transformation import string_to_multi_value
from ..core.auth import (
    AuthenticatedSession,
    SessionAuthenticationParameters,
    build_auth_params,
)
from ..core.data_models import IntegrationParameters
from ..core.exceptions import ZscalerException
from ..core.utils import is_valid_ip
from ..core.ZscalerManager import ZscalerManager


class ZscalerBaseAction(Action, ABC):
    """Base action class for Zscaler integration."""

    def _validate_ioc(self, item: str) -> str | None:
        """Validate an IOC item (IP or URL)."""
        item = item.strip()
        if not item:
            return None

        try:
            return (
                item
                if is_valid_ip(item)
                else self.api_client.validate_and_extract_url(item.lower())
            )
        except ZscalerException as e:
            self.logger.error(f"Failed to process IOC {item}: {str(e)}")
            return None

    def _process_iocs_parameter(self) -> None:
        """Process IOCs parameter."""
        if self.params.iocs:
            for item in string_to_multi_value(self.params.iocs):
                processed_item = self._validate_ioc(item)
                if processed_item:
                    self._items_to_process.add(processed_item)
                    self.successful_entities.append(item)
                else:
                    self.failed_entities.append(item)

    def _init_api_clients(self) -> ZscalerManager:
        """Initialize ZscalerManager."""
        auth_params: IntegrationParameters = build_auth_params(self.soar_action)
        authenticated_session: AuthenticatedSession = AuthenticatedSession()
        auth_session_params: SessionAuthenticationParameters = (
            SessionAuthenticationParameters(
                api_root=auth_params.api_root,
                login_id=auth_params.login_id,
                api_key=auth_params.api_key,
                password=auth_params.password,
                verify_ssl=auth_params.verify_ssl,
                client_id=auth_params.client_id,
                client_secret=auth_params.client_secret,
                login_api_root=auth_params.login_api_root,
            )
        )
        authenticated_session.authenticate_session(
            auth_session_params, self.soar_action.LOGGER
        )
        return ZscalerManager(
            authenticated_session=authenticated_session,
            configuration=auth_params,
            logger=self.logger,
        )
