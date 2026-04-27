from __future__ import annotations

import datetime
from itertools import chain, islice
from collections.abc import Generator
from typing import Any

import requests

from .constants import (
    DEFAULT_TIME_WINDOW_SECONDS,
    MAX_CLIENTS_LIMIT_V2,
    MAX_EVENTS_LIMIT_V2,
    MIN_RESULTS_LIMIT,
    QUARANTINE_MAX_LIMIT,
    TYPES,
    V2_ENDPOINTS,
)
from .datamodels import Client
from .exceptions import NetskopeAlreadyProcessedError
from .exceptions import NetskopeManagerV2Error
from .NetskopeAuth import NetskopeV2BearerAuth, NetskopeV2OAuth
from .PaginationStrategy import V2OffsetPaginationStrategy
from .utils import get_filtered_params


def validate_response(
    response: requests.Response, error_msg: str = "An error occurred"
) -> None:
    """Validate the HTTP response and raise an error if needed.

    Args:
        response (requests.Response): The HTTP response to validate.
        error_msg (str): The error message to use if validation fails.
            Defaults to "An error occurred".

    Raises:
        NetskopeManagerV2Error: If the response is not valid.
    """
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        raise NetskopeManagerV2Error(
            f"{error_msg}: {error} - {error.response.content}"
        ) from error


class NetskopeManagerV2:
    def __init__(
        self,
        api_root: str,
        v2_api_token: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        verify_ssl: bool = False,
    ) -> None:
        """Initialize NetskopeManagerV2.

        Args:
            api_root (str): The root URL of the Netskope API.
            v2_api_token (str | None): The V2 API token. Defaults to None.
            client_id (str | None): The OAuth client ID. Defaults to None.
            client_secret (str | None): The OAuth client secret. Defaults to None.
            verify_ssl (bool): Whether to verify SSL certificates. Defaults to False.
        """
        self.api_root: str = api_root if api_root[-1:] == "/" else api_root + "/"
        self.session: requests.Session = requests.session()
        self.session.verify = verify_ssl
        if client_id and client_secret:
            self.session.auth = NetskopeV2OAuth(
                self.api_root, client_id, client_secret, verify_ssl
            )
        elif v2_api_token:
            self.session.auth = NetskopeV2BearerAuth(v2_api_token)
        else:
            raise NetskopeManagerV2Error(
                "Missing required authentication parameters "
                "(either client_id/client_secret or v2_api_token)"
            )

    @property
    def endpoints(self) -> dict[str, str]:
        return V2_ENDPOINTS

    def test_connectivity(self) -> bool:
        """Test connectivity to Netskope API.

        Returns:
            bool: True if connectivity is successful.
        """
        start_time: int = (
            int(datetime.datetime.now().timestamp()) - DEFAULT_TIME_WINDOW_SECONDS
        )
        end_time: int = int(datetime.datetime.now().timestamp())
        next(
            self.get_alerts(
                start_time=start_time,
                end_time=end_time,
                limit=MIN_RESULTS_LIMIT,
            ),
            None,
        )
        return True

    def get_events(
        self,
        query: str | None = None,
        alert_type: str | None = None,
        timeperiod: int | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Fetch events from Netskope.

        Args:
            query (str | None): The query to filter events. Defaults to None.
            alert_type (str | None): The type of events (page, application,
                audit, infrastructure). Defaults to None.
            timeperiod (int | None): The time period in seconds. Defaults to None.
            start_time (int | None): The start time timestamp. Defaults to None.
            end_time (int | None): The end time timestamp. Defaults to None.
            limit (int | None): The maximum number of events to fetch. Defaults to None.

        Yields:
            dict[str, Any]: The event data.
        """
        endpoint_key = alert_type if alert_type in TYPES else "page"
        url: str = f"{self.api_root}{self.endpoints[endpoint_key]}"

        api_limit = min(limit or MAX_EVENTS_LIMIT_V2, MAX_EVENTS_LIMIT_V2)
        params = get_filtered_params(
            {
                "query": query,
                "starttime": start_time,
                "endtime": end_time,
                "timeperiod": timeperiod,
            }
        )
        gen = self._paginate_results(
            url=url,
            params=params,
            error_msg="Unable to get events",
            limit=api_limit,
        )

        yield from islice(gen, limit)

    def get_all_events(
        self,
        query: str | None = None,
        timeperiod: int | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None,
        logger: Any = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Fetch all events across all types.

        Args:
            query (str | None): The query to filter events. Defaults to None.
            timeperiod (int | None): The time period in seconds. Defaults to None.
            start_time (int | None): The start time timestamp. Defaults to None.
            end_time (int | None): The end time timestamp. Defaults to None.
            limit (int | None): The maximum number of events to fetch. Defaults to None.
            logger (Any): Logger instance to print progress. Defaults to None.

        Yields:
            dict[str, Any]: The event data.
        """
        if logger:
            logger.info("Fetching events across all types")

        events_gen = chain.from_iterable(
            self.get_events(
                query=query,
                alert_type=alt_type,
                timeperiod=timeperiod,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
            )
            for alt_type in TYPES
        )

        yield from islice(events_gen, limit)

    def get_alerts(
        self,
        query: str | None = None,
        alert_type: str | None = None,
        acked: bool | None = None,
        timeperiod: int | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
        insertion_start_time: int | None = None,
        insertion_end_time: int | None = None,
        limit: int | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Fetch alerts from Netskope.

        Args:
            query (str | None): The query to filter alerts. Defaults to None.
            alert_type (str | None): The type of alerts. Defaults to None.
            acked (bool | None): Whether alerts are acknowledged. Defaults to None.
            timeperiod (int | None): The time period in seconds. Defaults to None.
            start_time (int | None): The start time timestamp. Defaults to None.
            end_time (int | None): The end time timestamp. Defaults to None.
            insertion_start_time (int | None): The insertion start time
                timestamp. Defaults to None.
            insertion_end_time (int | None): The insertion end time
                timestamp. Defaults to None.
            limit (int | None): The maximum number of alerts to fetch. Defaults to None.

        Yields:
            dict[str, Any]: The alert data.
        """
        api_limit = min(limit or MAX_EVENTS_LIMIT_V2, MAX_EVENTS_LIMIT_V2)
        url: str = f"{self.api_root}{self.endpoints['alert']}"
        params = get_filtered_params(
            {
                "query": query,
                "type": alert_type,
                "acked": acked,
                "timeperiod": timeperiod,
                "starttime": start_time,
                "insertionstarttime": insertion_start_time,
                "insertionendtime": insertion_end_time,
                "endtime": end_time,
            }
        )
        gen = self._paginate_results(
            url=url,
            params=params,
            error_msg="Unable to get alerts",
            limit=api_limit,
        )

        yield from islice(gen, limit)

    def get_clients(
        self, query: str | None = None, limit: int | None = None
    ) -> Generator[Client, None, None]:
        """Fetch clients from Netskope.

        Args:
            query (str | None): The query to filter clients. Defaults to None.
            limit (int | None): The maximum number of clients to fetch.
                Defaults to None.

        Yields:
            Client: The client data object.
        """
        api_limit = min(limit or MAX_CLIENTS_LIMIT_V2, MAX_CLIENTS_LIMIT_V2)
        url: str = f"{self.api_root}{self.endpoints['clients']}"
        params = get_filtered_params({"query": query})
        clients_gen = self._paginate_results(
            url=url,
            params=params,
            error_msg="Unable to get clients",
            limit=api_limit,
        )

        for client in islice(clients_gen, limit):

            user_info = client.get("user_info") or {}
            username = user_info.get("username")
            yield Client(
                raw_data=client,
                device_id=client.get("device_id") or client.get("_id"),
                os=(client.get("host_info") or {}).get("os"),
                users=[username] if username else [],
            )

    def get_quarantined_files(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Fetch quarantined files from Netskope.

        Args:
            start_time (int | None): The start time timestamp. Defaults to None.
            end_time (int | None): The end time timestamp. Defaults to None.
            limit (int | None): The maximum number of files to fetch. Defaults to None.

        Yields:
            dict[str, Any]: The file data.
        """
        if start_time and not end_time:
            end_time = int(datetime.datetime.now().timestamp())
        if end_time and not start_time:
            start_time = end_time - DEFAULT_TIME_WINDOW_SECONDS

        api_limit = min(limit or QUARANTINE_MAX_LIMIT, QUARANTINE_MAX_LIMIT)
        url: str = f"{self.api_root}{self.endpoints['quarantine']}"
        params = get_filtered_params(
            {
                "starttime": start_time,
                "endtime": end_time,
            }
        )
        gen = self._paginate_results(
            url=url,
            params=params,
            key="quarantineIncidents",
            error_msg="Unable to get quarantined files",
            limit=api_limit,
        )

        yield from islice(gen, limit)

    def block_file(self, file_id: str) -> bool:
        """Block a file by ID.

        Args:
            file_id (str): The ID of the file to block.

        Returns:
            bool: True if successful.
        """
        url: str = f"{self.api_root}{self.endpoints['quarantine_block']}".format(
            file_id=file_id
        )
        response = self.session.post(url, json={})
        if response.status_code == 409:
            try:
                resp_json = response.json()
                if (
                    resp_json.get("error")
                    == "quarantine incident was already processed"
                ):
                    raise NetskopeAlreadyProcessedError(
                        "quarantine incident was already processed"
                    )
            except ValueError:
                pass
        validate_response(response, "Unable to block file")
        return True

    def allow_file(self, file_id: str) -> bool:
        """Allow a file by ID.

        Args:
            file_id (str): The ID of the file to allow.

        Returns:
            bool: True if successful.
        """
        url: str = f"{self.api_root}{self.endpoints['quarantine_restore']}".format(
            file_id=file_id
        )
        response = self.session.post(url, json={})
        if response.status_code == 409:
            try:
                resp_json = response.json()
                if (
                    resp_json.get("error")
                    == "quarantine incident was already processed"
                ):
                    raise NetskopeAlreadyProcessedError(
                        "quarantine incident was already processed"
                    )
            except ValueError:
                pass
        validate_response(response, "Unable to allow file")
        return True

    def download_file(self, app: str, instance: str, file_id: str) -> bytes:
        """Download a file from CASB.

        Args:
            app (str): The app name.
            instance (str): The instance name.
            file_id (str): The file ID.

        Returns:
            bytes: The file content.
        """
        url: str = f"{self.api_root}{self.endpoints['download_casb_file']}".format(
            app=app, instance=instance, file_id=file_id
        )
        response = self.session.get(url)
        validate_response(response, "Unable to download file")
        return response.content

    def _paginate_results(
        self,
        url: str,
        params: dict[str, Any],
        limit: int,
        json_body: dict[str, Any] | None = None,
        key: str = "result",
        error_msg: str = "Unable to get results",
        method: str = "GET",
    ) -> Generator[dict[str, Any], None, None]:
        """Paginate results from Netskope V2 API.

        Args:
            url (str): The URL to request.
            params (dict[str, Any]): The query parameters.
            limit (int): The page size limit.
            json_body (dict[str, Any] | None): The JSON body for POST requests.
            key (str): The key in the JSON response containing the results.
                Defaults to "result".
            error_msg (str): The error message to use if request fails.
                Defaults to "Unable to get results".
            method (str): HTTP method to use (GET or POST). Defaults to "GET".

        Yields:
            dict[str, Any]: The item data.
        """
        strategy = V2OffsetPaginationStrategy(limit=limit)
        current_params = {**params, **strategy.get_initial_state()}

        while True:
            response = self.session.request(
                method=method.upper(),
                url=url,
                params=current_params,
                json=json_body,
            )

            validate_response(response, error_msg)
            resp_json: dict[str, Any] = response.json()

            res_data: Any = resp_json.get(key)
            ok_status: Any = resp_json.get("ok")
            if isinstance(res_data, str) and ok_status == 0:
                raise NetskopeManagerV2Error(f"{error_msg}: {res_data}")

            data: list[dict[str, Any]] | None = resp_json.get(key)
            if not data:
                break

            for item in data:
                yield item

            if not strategy.has_next_page(len(data)):
                break

            strategy.update_next_page_token(response)
            current_params = {**params, **strategy.get_next_page_state()}

    def get_url_list_data(self, name: str) -> dict[str, Any]:
        """Get data for a specific URL list by name.

        Args:
            name (str): The name of the URL list.

        Returns:
            dict[str, Any]: The URL list data.

        Raises:
            NetskopeManagerV2Error: If the URL list is not found.
        """
        url: str = f"{self.api_root}{self.endpoints['url_list']}"
        response = self.session.get(url)
        validate_response(response, "Unable to get URL lists")
        data = response.json()
        for item in data:
            if item.get("name") == name:
                return item
        raise NetskopeManagerV2Error(f"URL List '{name}' not found.")

    def add_entities_to_url_list(
        self, list_id: int, list_type: str, entities: list[str]
    ) -> tuple[list[str], list[str], dict[str, Any] | None]:
        """Add entities to a URL list.

        Args:
            list_id (int): The ID of the URL list.
            list_type (str): The type of the list (e.g., 'url').
            entities (list[str]): The entities to add.

        Returns:
            tuple[list[str], list[str], dict[str, Any] | None]: A tuple containing:
                - List of successful entities.
                - List of failed entities.
                - The last HTTP response data if any.
        """
        successful_entities, failed_entities, last_response = [], [], None
        for entity in entities:
            try:
                response = self._append_to_url_list(list_id, list_type, [entity])
                successful_entities.append(entity)
                last_response = response
            except NetskopeManagerV2Error:
                failed_entities.append(entity)
        return successful_entities, failed_entities, last_response

    def _append_to_url_list(
        self, list_id: int, list_type: str, entities: list[str]
    ) -> dict[str, Any]:
        """Append entities to a URL list.

        Args:
            list_id (int): The ID of the URL list.
            list_type (str): The type of the list.
            entities (list[str]): The entities to append.

        Returns:
            dict[str, Any]: The JSON response from the API.
        """
        endpoint = self.endpoints["url_list_append"].format(list_id=list_id)
        url: str = f"{self.api_root}{endpoint}"
        payload: dict[str, Any] = {"data": {"type": list_type, "urls": entities}}
        response = self.session.request("PATCH", url, json=payload)
        validate_response(response, f"Unable to append entities to list {list_id}")
        return response.json()

    def deploy_url_list_changes(self) -> dict[str, Any]:
        """Deploy changes to URL lists.

        Returns:
            dict[str, Any]: The JSON response from the API.
        """
        url: str = f"{self.api_root}{self.endpoints['url_list_deploy']}"
        response = self.session.post(url)
        validate_response(response, "Unable to deploy URL list changes")
        return response.json()
