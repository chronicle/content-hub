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

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING

from requests.adapters import HTTPAdapter
from urllib3.util import Retry

if TYPE_CHECKING:
    from collections.abc import Iterable

    from google.auth.transport.requests import AuthorizedSession

from .consts import (
    BETA_V1_VERSION,
    DEFAULT_API_ROOT,
    DEFAULT_V1_VERSION,
)
from .datamodels import Operation, PoliciesRequestQuery, Policy
from .utils import validate_response

URL_FORMAT = "{api_root}/{version}/policies"


class PoliciesApiResource:
    def __init__(
        self, session: AuthorizedSession, api_root: str = DEFAULT_API_ROOT, **kwargs: object
    ) -> None:
        """Initialize the PoliciesApiResource.

        Args:
            session: The authorized session for API requests.
            api_root: The root URL of the Cloud Identity API.
            **kwargs: Additional keyword arguments.

        """
        self._api_root = api_root
        self._session = session
        adapter = HTTPAdapter(
            max_retries=Retry(
                total=3,
                backoff_factor=0.1,
                status_forcelist=[HTTPStatus.TOO_MANY_REQUESTS.value],
                allowed_methods={"POST", "GET"},
            )
        )
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)
        self._logger = kwargs.get("logger", logging.getLogger(__name__))

    def _url(
        self, version: str = DEFAULT_V1_VERSION, policy_id: str | None = None
    ) -> str:
        url = URL_FORMAT.format(api_root=self._api_root, version=version)
        if policy_id:
            url += f"/{policy_id}"
        return url

    def list(self, query: PoliciesRequestQuery = None) -> Iterable[Policy]:
        """List policies.

        Args:
            query: A query object for filtering and pagination.

        Yields:
            Policy objects.

        """
        if not query:
            query = PoliciesRequestQuery(100)
        while True:
            self._logger.info("Fetching next policies page")
            response = self._session.get(self._url(), params=query.to_dict())
            validate_response(response, self.__class__.__name__)
            policies = [
                Policy.from_dict(policy)
                for policy in response.json().get("policies", [])
            ]
            self._logger.info("Fetched page of %s policies", len(policies))
            yield from policies
            next_page_token = response.json().get("nextPageToken")
            if next_page_token:
                query.page_token = next_page_token
            else:
                break

    def create(self, policy: Policy) -> Policy:
        """Create a policy.

        Args:
            policy: The policy to create.

        Returns:
            A Policy object representing the created policy.

        """
        response = self._session.post(
            self._url(version=BETA_V1_VERSION), json=policy.to_dict()
        )
        validate_response(response, self.__class__.__name__)
        result = Operation.from_dict(response.json()).validate()
        return Policy.from_dict(result.response)

    def patch(self, policy: Policy) -> Policy:
        """Update a policy.

        Args:
            policy: The policy with updated properties.

        Returns:
            A Policy object representing the updated policy.

        """
        response = self._session.patch(
            self._url(version=BETA_V1_VERSION, policy_id=policy.get_id()),
            json=policy.to_dict(),
        )
        validate_response(response, self.__class__.__name__)
        result = Operation.from_dict(response.json()).validate()
        return Policy.from_dict(result.response)

    def get(self, policy_id: str) -> Policy:
        """Retrieve a policy.

        Args:
            policy_id: The unique ID of the policy.

        Returns:
            A Policy object representing the policy.

        """
        response = self._session.get(self._url(policy_id=policy_id))
        validate_response(response, self.__class__.__name__)
        return Policy.from_dict(response.json())

    def delete(self, policy_id: str) -> Policy:
        """Delete a policy.

        Args:
            policy_id: The unique ID of the policy.

        Returns:
            A Policy object representing the deleted policy.

        """
        response = self._session.delete(
            self._url(version=BETA_V1_VERSION, policy_id=policy_id)
        )
        validate_response(response, self.__class__.__name__)
        result = Operation.from_dict(response.json()).validate()
        return Policy.from_dict(result.response)
