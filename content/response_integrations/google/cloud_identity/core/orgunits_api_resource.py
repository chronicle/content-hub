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
    from google.auth.transport.requests import AuthorizedSession

from .consts import (
    ADMIN_SDK_API_ROOT,
    DEFAULT_V1_VERSION,
    MY_CUSTOMER,
)
from .datamodels import OrgUnit
from .utils import validate_response

URL_FORMAT = "{api_root}/admin/directory/{version}/customer/{customer_id}/orgunits"


class OrgUnitsApiResource:
    def __init__(
        self, session: AuthorizedSession, api_root: str = ADMIN_SDK_API_ROOT, **kwargs: object
    ) -> None:
        """Initialize the OrgUnitsApiResource.

        Args:
            session: The authorized session for API requests.
            api_root: The root URL of the Admin SDK API.
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
        self,
        customer_id: str,
        version: str = DEFAULT_V1_VERSION,
        org_unit_path: str | None = None,
    ) -> str:
        url = URL_FORMAT.format(
            api_root=self._api_root, version=version, customer_id=customer_id
        )
        if org_unit_path:
            url += f"/{org_unit_path}"
        return url

    def list(
        self, customer_id: str = MY_CUSTOMER, org_unit_path: str | None = None
    ) -> OrgUnit:
        """List organizational units.

        Args:
            customer_id: The unique ID for the customer's Google Workspace account.
            org_unit_path: The full path of the organizational unit or its unique ID.

        Returns:
            An OrgUnit object containing the list of organizational units.

        """
        params = {"type": "ALL_INCLUDING_PARENT", "orgUnitPath": org_unit_path}
        response = self._session.get(self._url(customer_id=customer_id), params=params)
        validate_response(response, self.__class__.__name__)
        return OrgUnit.from_dict(response.json())

    def get(self, org_unit_path: str, customer_id: str = MY_CUSTOMER) -> OrgUnit:
        """Retrieve an organizational unit.

        Args:
            org_unit_path: The full path of the organizational unit or its unique ID.
            customer_id: The unique ID for the customer's Google Workspace account.

        Returns:
            An OrgUnit object representing the organizational unit.

        """
        response = self._session.get(
            self._url(customer_id=customer_id, org_unit_path=org_unit_path)
        )
        validate_response(response, self.__class__.__name__)
        return OrgUnit.from_dict(response.json())

    def insert(self, org_unit: OrgUnit, customer_id: str = MY_CUSTOMER) -> OrgUnit:
        """Create an organizational unit.

        Args:
            org_unit: The organizational unit to create.
            customer_id: The unique ID for the customer's Google Workspace account.

        Returns:
            An OrgUnit object representing the created organizational unit.

        """
        response = self._session.post(
            self._url(customer_id=customer_id), json=org_unit.to_dict()
        )
        validate_response(response, self.__class__.__name__)
        return OrgUnit.from_dict(response.json())

    def patch(
        self, org_unit_path: str, org_unit: OrgUnit, customer_id: str = MY_CUSTOMER
    ) -> OrgUnit:
        """Update an organizational unit. This method supports patch semantics.

        Args:
            org_unit_path: The full path of the organizational unit or its unique ID.
            org_unit: The organizational unit with updated properties.
            customer_id: The unique ID for the customer's Google Workspace account.

        Returns:
            An OrgUnit object representing the updated organizational unit.

        """
        response = self._session.patch(
            self._url(customer_id=customer_id, org_unit_path=org_unit_path),
            json=org_unit.to_dict(),
        )
        validate_response(response, self.__class__.__name__)
        return OrgUnit.from_dict(response.json())

    def update(
        self, org_unit_path: str, org_unit: OrgUnit, customer_id: str = MY_CUSTOMER
    ) -> OrgUnit:
        """Update an organizational unit.

        Args:
            org_unit_path: The full path of the organizational unit or its unique ID.
            org_unit: The organizational unit with updated properties.
            customer_id: The unique ID for the customer's Google Workspace account.

        Returns:
            An OrgUnit object representing the updated organizational unit.

        """
        response = self._session.put(
            self._url(customer_id=customer_id, org_unit_path=org_unit_path),
            json=org_unit.to_dict(),
        )
        validate_response(response, self.__class__.__name__)
        return OrgUnit.from_dict(response.json())

    def delete(self, org_unit_path: str, customer_id: str = MY_CUSTOMER) -> None:
        """Delete an organizational unit.

        Args:
            org_unit_path: The full path of the organizational unit or its unique ID.
            customer_id: The unique ID for the customer's Google Workspace account.

        """
        response = self._session.delete(
            self._url(customer_id=customer_id, org_unit_path=org_unit_path)
        )
        validate_response(response, self.__class__.__name__)
