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

"""Get Secret Value action for retrieving secrets from Akeyless Security."""

from __future__ import annotations

from TIPCommon.extraction import extract_action_param

from ..core.base_action import AkeylessAction
from ..core.constants import (
    DEFAULT_SECRET_VERSION,
    GET_SECRET_VALUE_SCRIPT_NAME,
    INTEGRATION_NAME,
    SECRET_NAME_PARAM,
)
from ..core.utils import mask_id, resolve_secret_and_version


class GetSecretValueAction(AkeylessAction):
    """Action to fetch a secret value from Akeyless Security and return it to SOAR.

    Attributes:
        secret_name: Resolved secret identifier in Akeyless.
        secret_version: Resolved secret version (defaults to 'latest').

    """

    def __init__(self) -> None:
        """Initialize the Get Secret Value action."""
        super().__init__(GET_SECRET_VALUE_SCRIPT_NAME)
        self.error_output_message: str = (
            f"Error executing action '{GET_SECRET_VALUE_SCRIPT_NAME}'."
        )
        self.secret_name: str = ""
        self.secret_version: str = DEFAULT_SECRET_VERSION

    def _extract_action_parameters(self) -> None:
        """Extract action parameters from the SOAR action context."""
        self.params.secret_name = extract_action_param(
            self.soar_action,
            param_name=SECRET_NAME_PARAM,
            is_mandatory=True,
            print_value=True,
        )

    def _validate_params(self) -> None:
        """Validate and parse the Secret Name parameter into secret ID and version."""
        self.secret_name, self.secret_version = resolve_secret_and_version(
            self.params.secret_name
        )

    def _perform_action(self, _: object = None) -> None:
        """Fetch the requested secret version from Akeyless and populate SOAR results."""
        masked_name = mask_id(self.secret_name)
        self.logger.info(
            f"Fetching secret '{masked_name}' (version: '{self.secret_version}') "
            f"from {INTEGRATION_NAME}."
        )
        self.error_output_message = (
            f"Failed to retrieve secret '{self.secret_name}' "
            f"(version: '{self.secret_version}') from {INTEGRATION_NAME}."
        )

        secret_value: str = self.akeyless_client.get_secret_value(
            secret_id=self.secret_name,
            version_id=self.secret_version,
        )

        self.logger.info(
            f"Successfully retrieved secret '{masked_name}' "
            f"(version: '{self.secret_version}')."
        )
        self.json_results = {
            "secret_name": self.secret_name,
            "version": self.secret_version,
            "secret_value": secret_value,
        }
        self.output_message = (
            f"Successfully retrieved secret '{self.secret_name}' "
            f"(version: '{self.secret_version}') from {INTEGRATION_NAME}."
        )
        self.result_value = True


def main() -> None:
    """Run the Get Secret Value action."""
    GetSecretValueAction().run()


if __name__ == "__main__":
    main()
