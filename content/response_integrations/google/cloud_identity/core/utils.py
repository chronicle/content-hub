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

from http import HTTPStatus
from typing import TYPE_CHECKING

from .exceptions import (
    GoogleCloudIdentityApiEntityNotFoundException,
    GoogleCloudIdentityApiException,
)

if TYPE_CHECKING:
    import requests

    from .action_wrapper import ActionContext


class IntegrationParameters:
    """A data class for holding integration parameters."""

    def __init__(self, context: ActionContext) -> None:
        """Initialize the IntegrationParameters.

        Args:
            context: The action context containing integration parameters.

        """
        # Integration configuration
        self.service_account_json = context.integration_parameters.get(
            "Service Account JSON File Content"
        )
        self.verify_ssl = context.integration_parameters.get("Verify SSL")
        self.workload_identity_email = context.integration_parameters.get(
            "Workload Identity Email"
        )
        self.delegated_email = context.integration_parameters.get("Delegated Email")

    def as_dict(self) -> dict[str, object]:
        """Return the parameters as a dictionary.

        Returns:
            A dictionary representation of the parameters.

        """
        return {
            "service_account_json": self.service_account_json,
            "verify_ssl": self.verify_ssl,
            "workload_identity_email": self.workload_identity_email,
            "delegated_email": self.delegated_email,
        }


def validate_response(response: requests.Response, api_name: str) -> None:
    """Validate a response from the Google Cloud Identity API.

    Args:
        response: The response to validate.
        api_name: The name of the API that was called.

    Raises:
        GoogleCloudIdentityApiEntityNotFoundException: If the entity was not found.
        GoogleCloudIdentityApiException: For other API errors.

    """
    if response.status_code == HTTPStatus.NOT_FOUND:
        msg = f"{api_name} entity not found: {response.json()}"
        raise GoogleCloudIdentityApiEntityNotFoundException(msg)

    try:
        response.raise_for_status()
    except Exception as e:
        msg = f"{api_name} failed reason: {e}, {response.json()}"
        raise GoogleCloudIdentityApiException(msg) from e

    # Validation for modification calls results
    if response.json().get("done") is False:
        msg = f"{api_name} did not finish request: {response.json()}"
        raise GoogleCloudIdentityApiException(msg)
