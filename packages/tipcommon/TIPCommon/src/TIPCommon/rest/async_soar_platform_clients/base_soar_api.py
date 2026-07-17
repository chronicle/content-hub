# Copyright 2025 Google LLC
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

from TIPCommon.data_models import Container
from TIPCommon.rest.custom_types import HttpMethod

if TYPE_CHECKING:
    import httpx

    from TIPCommon.rest.async_soar_platform_clients.secops_soar import AsyncChronicleSOAR
    from TIPCommon.types import SingleJson


class BaseAsyncSoarApi:
    """Base asynchronous API client for Chronicle SOAR.
    Uses AsyncChronicleSOAR for transport and logging.
    """

    def __init__(self, async_sdk: AsyncChronicleSOAR) -> None:
        self.async_sdk = async_sdk
        self.client = async_sdk.client
        self.logger = async_sdk.logger
        self.params = Container()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        *,
        params: SingleJson | None = None,
        payload: SingleJson | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Make an asynchronous HTTP request to the SOAR API.

        Args:
            method (str): HTTP method (e.g., 'GET', 'POST').
            endpoint (str): API endpoint.
            params (SingleJson | None): Query parameters. Defaults to None.
            payload (SingleJson | None): Request body. Defaults to None.
            headers (dict[str, str] | None): Headers. Defaults to None.

        Returns:
            httpx.Response: The HTTP response object.

        Raises:
            httpx.HTTPStatusError: If the request returns an unsuccessful status code.

        """
        self.logger.info(f"Calling SOAR API (async): {method} {self.async_sdk.api_root}/{endpoint}")

        response: httpx.Response = await self.client.request(
            method,
            endpoint,
            params=params,
            json=payload,
            headers=headers,
        )

        self.logger.info(f"SOAR API response (async): {method} {endpoint} (status={response.status_code})")

        response.raise_for_status()

        return response

    async def get(
        self,
        endpoint: str,
        params: SingleJson | None = None,
    ) -> httpx.Response:
        """Make an asynchronous GET request to the SOAR API.

        Args:
            endpoint (str): API endpoint.
            params (SingleJson | None): Query parameters. Defaults to None.

        Returns:
            httpx.Response: The HTTP response object.

        Raises:
            httpx.HTTPStatusError: If the API request fails.

        """
        return await self._make_request(HttpMethod.GET.value, endpoint, params=params)

    async def post(
        self,
        endpoint: str,
        payload: SingleJson | None = None,
    ) -> httpx.Response:
        """Make an asynchronous POST request to the SOAR API.

        Args:
            endpoint (str): API endpoint.
            payload (SingleJson | None): Request body. Defaults to None.

        Returns:
            httpx.Response: The HTTP response object.

        Raises:
            httpx.HTTPStatusError: If the API request fails.

        """
        return await self._make_request(HttpMethod.POST.value, endpoint, payload=payload)

    async def patch(
        self,
        endpoint: str,
        payload: SingleJson | None = None,
        params: SingleJson | None = None,
    ) -> httpx.Response:
        """Make an asynchronous PATCH request to the SOAR API.

        Args:
            endpoint (str): API endpoint.
            payload (SingleJson | None): Request body. Defaults to None.
            params (SingleJson | None): Query parameters. Defaults to None.

        Returns:
            httpx.Response: The HTTP response object.

        Raises:
            httpx.HTTPStatusError: If the API request fails.

        """
        return await self._make_request(
            HttpMethod.PATCH.value,
            endpoint,
            payload=payload,
            params=params,
        )

    async def put(
        self,
        endpoint: str,
        payload: SingleJson | None = None,
        params: SingleJson | None = None,
    ) -> httpx.Response:
        """Make an asynchronous PUT request to the SOAR API.

        Args:
            endpoint: API endpoint.
            payload: Request body. Defaults to None.
            params: Query parameters. Defaults to None.

        Returns:
            The HTTP response object.

        Raises:
            httpx.HTTPStatusError: If the API request fails.

        """
        return await self._make_request(
            HttpMethod.PUT.value,
            endpoint,
            payload=payload,
            params=params,
        )

    async def delete(self, endpoint: str) -> httpx.Response:
        """Make an asynchronous DELETE request to the SOAR API.

        Args:
            endpoint (str): API endpoint.

        Returns:
            httpx.Response: The HTTP response object.

        Raises:
            httpx.HTTPStatusError: If the API request fails.

        """
        return await self._make_request(HttpMethod.DELETE.value, endpoint)

    async def _paginate_results(
        self,
        initial_endpoint: str,
        root_response_key: str,
    ) -> list[SingleJson]:
        """Handles paginated API requests, managing tokens and aggregating results.

        Avoids infinite loops by using a controlled loop condition.

        Args:
            initial_endpoint (str): The initial API endpoint to fetch data from.
            root_response_key (str): The key in the response JSON where records are
                stored.

        Returns:
            list[SingleJson]: A list of all records retrieved across paginated
            responses.

        """
        all_records = []
        next_token = None
        current_endpoint = initial_endpoint

        while True if next_token is None else bool(next_token):
            separator = "&" if "?" in current_endpoint else "?"
            endpoint_with_token = (
                f"{current_endpoint}{separator}pageToken={next_token}"
                if next_token
                else current_endpoint
            )

            try:
                response = await self.get(endpoint_with_token)
                response_data = response.json()
            except Exception as e:
                self.logger.error(f"Failed to fetch page: {e}")
                break

            current_records = response_data.get(root_response_key, [])
            all_records.extend(current_records)

            next_token = response_data.get("nextPageToken")
            if not next_token:
                break

        return all_records
