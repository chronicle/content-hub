from __future__ import annotations

from collections.abc import Generator
from itertools import islice
from typing import Any

import requests
from .constants import (
    ERROR_STATUS,
    MAX_CLIENTS_LIMIT_V1,
    MIN_RESULTS_LIMIT,
    V1_ENDPOINTS,
)
from .NetskopeTransformationalLayer import NetskopeTransformationalLayer
from .PaginationStrategy import V1SkipPaginationStrategy
from .utils import get_filtered_params
from .NetskopeAuth import NetskopeV1Auth


class NetskopeManagerError(Exception):
    pass


def validate_response(
    response: requests.Response, error_msg: str = "An error occurred"
) -> None:
    """Validate response.

    Args:
        response: The response to validate.
        error_msg: The error message.
    """
    try:
        response.raise_for_status()

        if response.json().get("status") == ERROR_STATUS:
            error_code = response.json().get("errorCode")
            errors = ",".join(response.json().get("errors", []))
            raise NetskopeManagerError(f"{error_msg}: {error_code} {errors}")

    except requests.HTTPError as error:
        raise NetskopeManagerError(
            f"{error_msg}: {error} - {error.response.content}"
        ) from error


class NetskopeManager:
    def __init__(self, api_root: str, api_token: str, verify_ssl: bool = False):
        """Initialize NetskopeManager.

        Args:
            api_root: Netskope api root URL.
            api_token: Authorization token.
            verify_ssl: Verify SSL.
        """
        self.api_root = api_root if api_root[-1:] == "/" else api_root + "/"
        self.api_token = api_token
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.auth = NetskopeV1Auth(api_token)
        self.parser = NetskopeTransformationalLayer()

    @property
    def endpoints(self) -> dict[str, str]:
        return V1_ENDPOINTS

    def test_connectivity(self) -> bool:
        """
        Test connectivity to Netskope.

        Returns:
            bool: True if succeed.
        """
        if self.api_token:
            next(self.get_clients(limit=MIN_RESULTS_LIMIT), None)
        return True

    def get_clients(
        self, query: str | None = None, limit: int | None = None
    ) -> Generator[dict[str, Any], None, None]:
        """Get clients info.

        Args:
            query: Filter on all entries.
            limit: Limit returned clients.

        Returns:
            Generator: The clients info.
        """
        url = f"{self.api_root}{self.endpoints['clients']}"
        api_limit = min(limit or MAX_CLIENTS_LIMIT_V1, MAX_CLIENTS_LIMIT_V1)
        params = get_filtered_params({"query": query})
        gen = self._paginate_results(
            url=url,
            params=params,
            error_msg="Unable to get clients",
            limit=api_limit,
        )

        for client in islice(gen, limit):
            yield self.parser.build_siemplify_client(client)

    def get_quarantined_files(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None,
        **_kwargs: Any,
    ) -> Generator[dict[str, Any], None, None]:
        """Get all quarantined results.

        Args:
            start_time: Get files last modified after this Unixtime.
            end_time: Get files last modified before this Unixtime.
            limit: Limit returned files.
            **_kwargs: Additional keyword arguments.

        Returns:
            Generator: The quarantined files.
        """
        url = f"{self.api_root}{self.endpoints['quarantine']}"
        params = {
            "op": "get-files",
            "starttime": start_time,
            "endtime": end_time,
        }

        params = get_filtered_params(params)
        response = self.session.get(url, params=params)
        validate_response(response, "Unable to get quarantined files")

        quarantines = response.json().get("data", {}).get("quarantined", [])

        def _get_files():
            for quarantine in quarantines:
                for quarantined_file in quarantine.get("files", []):
                    quarantined_file.update(
                        {
                            "quarantine_profile_id": quarantine.get(
                                "quarantine_profile_id"
                            ),
                            "quarantine_profile_name": quarantine.get(
                                "quarantine_profile_name"
                            ),
                        }
                    )
                    yield quarantined_file

        yield from islice(_get_files(), limit)

    def block_file(self, file_id: str, quarantine_profile_id: str) -> bool:
        """Block a file.

        Args:
            file_id: The id of the file.
            quarantine_profile_id: The id of the quarantine profile.

        Returns:
            bool: True if successful.
        """
        url = f"{self.api_root}{self.endpoints['quarantine']}"
        params = {
            "op": "take-action",
            "file_id": file_id,
            "quarantine_profile_id": quarantine_profile_id,
            "action": "block",
        }

        params = get_filtered_params(params)
        response = self.session.get(url, params=params)
        validate_response(response, "Unable to do action on quarantined file")

        return True

    def allow_file(self, file_id: str, quarantine_profile_id: str) -> bool:
        """Allow a file.

        Args:
            file_id: The id of the file.
            quarantine_profile_id: The id of the quarantine profile.

        Returns:
            bool: True if successful.
        """
        url = f"{self.api_root}{self.endpoints['quarantine']}"
        params = {
            "op": "take-action",
            "file_id": file_id,
            "quarantine_profile_id": quarantine_profile_id,
            "action": "allow",
        }

        params = get_filtered_params(params)
        response = self.session.get(url, params=params)
        validate_response(response, "Unable to do action on quarantined file")

        return True

    def download_file(self, file_id: str, quarantine_profile_id: str) -> bytes:
        """Download a quarantined file.

        Args:
            file_id: The id of the file.
            quarantine_profile_id: The id of the quarantine profile.

        Returns:
            bytes: The content of the file.
        """
        url = f"{self.api_root}{self.endpoints['quarantine']}"
        params = {
            "op": "download-url",
            "file_id": file_id,
            "quarantine_profile_id": quarantine_profile_id,
        }

        params = get_filtered_params(params)
        response = self.session.get(url, params=params)

        if response.history:
            download_url = response.url
            download_response = self.session.get(download_url)
            download_response.raise_for_status()
            return download_response.content

        raise NetskopeManagerError("Unable to download a quarantined file")

    def _paginate_results(
        self,
        url: str,
        params: dict[str, Any],
        limit: int,
        error_msg: str = "Unable to get results",
    ) -> Generator[dict[str, Any], None, None]:
        """Paginate results and yield items.

        Args:
            url: The url to get the results from.
            params: The params of the request.
            error_msg: The message to display on error.
            limit: The page size limit.

        Returns:
            Generator: The results.
        """
        strategy = V1SkipPaginationStrategy(limit=limit)
        current_params = {**params, **strategy.get_initial_state()}

        while True:
            response = self.session.get(url, params=current_params)
            validate_response(response, error_msg)

            resp_json: dict[str, Any] = response.json()
            data: list[dict[str, Any]] | None = resp_json.get("data")
            if not data:
                break

            for item in data:
                yield item

            if not strategy.has_next_page(len(data)):
                break

            strategy.update_next_page_token(response)
            current_params = {**params, **strategy.get_next_page_state()}
