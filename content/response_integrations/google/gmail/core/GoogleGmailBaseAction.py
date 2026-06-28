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

from abc import ABC, abstractmethod
import json
import sys
from typing import Never

import asyncio

from soar_sdk import SiemplifyUtils
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.smp_time import unix_now
from TIPCommon.validation import ParameterValidator

from gmail.core.GoogleGmailAuth import build_auth_manager
from gmail.core.GoogleGmailApiManager import GoogleGmailApiManager
from gmail.core.GoogleGmailConsts import (
    DEFAULT_MAILBOX,
    GLOBAL_TIMEOUT_THRESHOLD_IN_MIN,
    INTEGRATION_IDENTIFIER,
)


class GoogleGmailBaseAction(Action, ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fix_sdk_stdout()

    @property
    def async_action_timeout(self) -> float:
        return (
            (self.soar_action.async_total_duration_deadline - unix_now())
            / NUM_OF_MILLI_IN_SEC -
            GLOBAL_TIMEOUT_THRESHOLD_IN_MIN * 60
        )

    def is_approaching_async_timeout(self) -> bool:
        """Determine whether action approaches asynchronous timeout."""
        return (
            unix_now() + GLOBAL_TIMEOUT_THRESHOLD_IN_MIN * 60 * NUM_OF_MILLI_IN_SEC >
            self.soar_action.async_total_duration_deadline
        )

    def _init_api_clients(
            self,
            user_email_address: str | None = None
    ) -> GoogleGmailApiManager:
        """Init Google Gmail Api Manager.

        Args:
            user_email_address: Email address to use for authentication.
                if not specified, will use the one from integration config

        Returns:
            Google Gmail Api Manager
        """
        if user_email_address is None or user_email_address == DEFAULT_MAILBOX:
            user_email_address = self.params.default_mailbox

        auth_manager = build_auth_manager(self.soar_action, user_email_address)
        return GoogleGmailApiManager(auth_manager.prepare_session())

    def _extract_action_parameters(self) -> None:
        self.params.default_mailbox = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Default Mailbox"
        )

    def _validate_params(self) -> None:
        validator = ParameterValidator(self.soar_action)
        self.params.default_mailbox = validator.validate_email(
            "Default Mailbox",
            self.params.default_mailbox
        )

    def _perform_action(self, _=None) -> None:
        _loop = asyncio.get_event_loop()
        _loop.run_until_complete(
            asyncio.ensure_future(
                self._perform_action_async()
            )
        )

    @abstractmethod
    async def _perform_action_async(self):
        pass

    def _fix_sdk_stdout(self) -> None:
        def end_script() -> Never:
            # pylint: disable=protected-access
            output_object = self.soar_action._build_output_object()
            SiemplifyUtils.resume_stdout()
            sys.stdout.write(json.dumps(output_object))
            sys.exit(0)

        self.soar_action.end_script = end_script
