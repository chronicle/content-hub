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
from TIPCommon.extraction import extract_configuration_param

import email
from email.header import decode_header

from .api_client import ProofPointPSApiClient
from .auth import AuthenticatedSession, SessionAuthenticationParameters
from .constants import PROVIDER


class BaseProofPointPSAction(Action, ABC):
    """Base action class for ProofPointPS integration."""

    def _init_api_clients(self) -> ProofPointPSApiClient:
        """Prepare and return the core ProofPointPS API client.

        Returns:
            The ProofPointPSApiClient.

        """
        server_address = extract_configuration_param(
            self.soar_action,
            provider_name=PROVIDER,
            param_name="Api Root",
            is_mandatory=True,
            print_value=True,
        )
        username = extract_configuration_param(
            self.soar_action,
            provider_name=PROVIDER,
            param_name="Username",
            is_mandatory=True,
        )
        password = extract_configuration_param(
            self.soar_action,
            provider_name=PROVIDER,
            param_name="Password",
            is_mandatory=True,
        )
        verify_ssl = extract_configuration_param(
            self.soar_action,
            provider_name=PROVIDER,
            param_name="Verify SSL",
            input_type=bool,
            print_value=True,
        )

        authenticator = AuthenticatedSession()
        auth_params = SessionAuthenticationParameters(
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )
        authenticator.authenticate_session(auth_params)
        authenticated_session = authenticator.session

        return ProofPointPSApiClient(
            server_address=server_address,
            authenticated_session=authenticated_session,
        )

    @property
    def result_value(self) -> bool:
        """Override the default result_value to be a boolean."""
        return self._result_value

    @result_value.setter
    def result_value(self, value: bool) -> None:
        self._result_value = value

    def _parse_email_details(self, raw_content: bytes, guid: str, folder: str) -> dict:
        """Parse raw email bytes to extract complete message details.

        Args:
            raw_content: Raw email bytes.
            guid: Message GUID.
            folder: Quarantine folder.

        Returns:
            A dict containing parsed message metadata.

        """
        def decode_mime_header(header_val: str | None) -> str:
            if not header_val:
                return ""
            try:
                decoded_parts = decode_header(header_val)
                result_parts = []
                for part, encoding in decoded_parts:
                    if isinstance(part, bytes):
                        result_parts.append(
                            part.decode(encoding or "utf-8", errors="replace")
                        )
                    else:
                        result_parts.append(str(part))
                return "".join(result_parts).strip()
            except Exception:
                return str(header_val).strip()

        try:
            msg = email.message_from_bytes(raw_content)
            return {
                "processingserver": "N/A",  # Not present in raw email
                "date": decode_mime_header(msg.get("Date")),
                "subject": decode_mime_header(msg.get("Subject")),
                "messageid": decode_mime_header(msg.get("Message-ID")),
                "folder": folder,
                "size": len(raw_content),
                "rcpts": [decode_mime_header(msg.get("To"))] if msg.get("To") else [],
                "from": decode_mime_header(msg.get("From")),
                "spamscore": 0,
                "guid": guid,
                "host_ip": "N/A",
                "localguid": guid,
                "dlpviolation": "Not Applicable",
                "messagestatus": []
            }
        except Exception:
            return {
                "guid": guid,
                "folder": folder,
                "subject": "Unknown",
                "size": len(raw_content)
            }

