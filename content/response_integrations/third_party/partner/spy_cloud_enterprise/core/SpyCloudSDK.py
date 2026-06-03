from __future__ import annotations

import time
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests

from .Constants import (
    ENDPOINT_BREACH_CATALOG,
    ENDPOINT_BREACH_DATA_WATCHLIST,
    ENDPOINT_COMPASS_DATA,
    ENDPOINT_PING,
)

DEFAULT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 4
DEFAULT_BACKOFF_SECONDS = 1.5
DEFAULT_RATE_LIMIT_WAIT_SECONDS = 3.0
DEFAULT_INTER_REQUEST_DELAY_SECONDS = 0.0

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class SpyCloudException(Exception):
    """
    General exception for SpyCloud
    """
    pass


class APIClient:
    """
    API handler class for making HTTP requests with configurable headers and base URL.
    Includes retry, backoff, timeout, and rate-limit handling.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        user_agent: str = "SpyCloud-SDK-Python/0.2.0",
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
        rate_limit_wait_seconds: float = DEFAULT_RATE_LIMIT_WAIT_SECONDS,
        inter_request_delay_seconds: float = DEFAULT_INTER_REQUEST_DELAY_SECONDS,
        verify_ssl: bool = True,
    ):
        if not api_key:
            raise ValueError("API key is required and cannot be empty")

        if not base_url:
            raise ValueError("Base URL is required and cannot be empty")

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.rate_limit_wait_seconds = rate_limit_wait_seconds
        self.inter_request_delay_seconds = inter_request_delay_seconds
        self.verify_ssl = verify_ssl

        self.session = requests.Session()
        self.session.verify = self.verify_ssl
        self._update_headers()

    def _update_headers(self) -> None:
        self.session.headers.update({
            "X-API-Key": self.api_key,
            "User-Agent": self.user_agent,
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

    def set_api_key(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("API key cannot be empty")

        self.api_key = api_key
        self._update_headers()

    def set_user_agent(self, user_agent: str) -> None:
        self.user_agent = user_agent
        self._update_headers()

    def set_base_url(self, base_url: str) -> None:
        if not base_url:
            raise ValueError("Base URL cannot be empty")

        self.base_url = base_url.rstrip("/")

    def _build_url(self, endpoint: str) -> str:
        return urljoin(self.base_url + "/", endpoint.lstrip("/"))

    def _safe_log(self, message: str) -> None:
        """
        Keep SDK logging concise and safe for connector output.
        """
        try:
            print(message)
        except Exception:
            pass

    def _get_retry_after_seconds(self, response: requests.Response) -> Optional[float]:
        """
        Parse Retry-After header if present.
        Supports either seconds or HTTP date.
        """
        retry_after = response.headers.get("Retry-After")
        if not retry_after:
            return None

        retry_after = retry_after.strip()

        try:
            seconds = float(retry_after)
            return max(0.0, seconds)
        except ValueError:
            pass

        try:
            retry_dt = parsedate_to_datetime(retry_after)
            if retry_dt is None:
                return None
            seconds = retry_dt.timestamp() - time.time()
            return max(0.0, seconds)
        except Exception:
            return None

    def _calculate_sleep_seconds(
        self,
        attempt_number: int,
        response: Optional[requests.Response] = None,
    ) -> float:
        """
        Determine how long to wait before a retry.
        """
        if response is not None and response.status_code == 429:
            retry_after_seconds = self._get_retry_after_seconds(response)
            if retry_after_seconds is not None:
                return max(self.rate_limit_wait_seconds, retry_after_seconds)
            return self.rate_limit_wait_seconds

        # Simple exponential backoff: base * 2^(attempt-1)
        return self.backoff_seconds * (2 ** max(0, attempt_number - 1))

    def _should_retry_response(self, response: requests.Response) -> bool:
        return response.status_code in RETRYABLE_STATUS_CODES

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> requests.Response:
        url = self._build_url(endpoint)

        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)

        request_timeout = kwargs.pop("timeout", self.timeout)

        last_exception: Optional[Exception] = None
        last_response: Optional[requests.Response] = None

        for attempt in range(1, self.max_retries + 2):
            try:
                if self.inter_request_delay_seconds > 0:
                    time.sleep(self.inter_request_delay_seconds)

                response = self.session.request(
                    method=method.upper(),
                    url=url,
                    json=data,
                    params=params,
                    headers=request_headers,
                    timeout=request_timeout,
                    **kwargs
                )

                last_response = response

                if not self._should_retry_response(response):
                    return response

                if attempt > self.max_retries:
                    return response

                sleep_seconds = self._calculate_sleep_seconds(
                    attempt_number=attempt,
                    response=response
                )
                self._safe_log(
                    f"Retrying SpyCloud API request after HTTP {response.status_code} "
                    f"(attempt {attempt}/{self.max_retries}). Sleeping {sleep_seconds:.1f}s."
                )
                time.sleep(sleep_seconds)

            except (requests.Timeout, requests.ConnectionError) as exc:
                last_exception = exc

                if attempt > self.max_retries:
                    break

                sleep_seconds = self._calculate_sleep_seconds(attempt_number=attempt)
                self._safe_log(
                    f"Retrying SpyCloud API request after {exc.__class__.__name__} "
                    f"(attempt {attempt}/{self.max_retries}). Sleeping {sleep_seconds:.1f}s."
                )
                time.sleep(sleep_seconds)

        if last_response is not None:
            return last_response

        raise SpyCloudException(
            f"Failed to call SpyCloud API after retries: {last_exception}"
        )

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> requests.Response:
        return self._make_request("GET", endpoint, params=params, headers=headers, **kwargs)

    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> requests.Response:
        return self._make_request("POST", endpoint, data=data, params=params, headers=headers, **kwargs)

    def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> requests.Response:
        return self._make_request("PUT", endpoint, data=data, params=params, headers=headers, **kwargs)

    def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> requests.Response:
        return self._make_request("DELETE", endpoint, params=params, headers=headers, **kwargs)

    def patch(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> requests.Response:
        return self._make_request("PATCH", endpoint, data=data, params=params, headers=headers, **kwargs)

    def validate_response(self, response: requests.Response, error_msg: str = "An error occurred") -> None:
        """
        Validate response and log relevant headers on HTTP errors.
        """
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            self._log_spycloud_headers(response)

            message = None
            body_text = None

            try:
                json_body = response.json()
                if isinstance(json_body, dict):
                    message = json_body.get("message") or json_body.get("error")
                body_text = str(json_body)
            except Exception:
                try:
                    body_text = response.text
                except Exception:
                    body_text = str(response.content)

            detail = message or body_text or "No response body returned"
            raise SpyCloudException(f"{error_msg}: {error} {detail}")

    def close(self) -> None:
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _log_spycloud_headers(self, response: requests.Response) -> None:
        """
        Print SpyCloud-specific response headers, including rate-limit hints if present.
        Only used on HTTP errors.
        """
        try:
            self._safe_log(f"HTTP Status: {response.status_code}")
            self._safe_log(f"Request URL: {response.request.url}")

            matched = False
            for key, value in response.headers.items():
                key_lower = key.lower()
                if (
                    "spycloud" in key_lower
                    or key_lower.startswith("x-")
                    or key_lower == "retry-after"
                ):
                    self._safe_log(f"Response Header -> {key}: {value}")
                    matched = True

            if not matched:
                self._safe_log("No SpyCloud-specific response headers were found.")
        except Exception as exc:
            self._safe_log(f"Failed to log headers: {exc}")


class BaseClient:
    """Small common base for clients."""

    def __init__(self, handler: APIClient):
        self._handler = handler

    def _build_date_params(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None,
        since_modification: Optional[str] = None,
        until_modification: Optional[str] = None,
        additional_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build parameters dictionary with optional publish-time and modification-time filters.

        since / until:
            Standard incremental publish-time window.

        since_modification / until_modification:
            Daily modified-record window used to catch records updated after initial publish,
            such as newly cracked passwords or modified records.
        """
        params: Dict[str, Any] = {}

        if since:
            params["since"] = since
        if until:
            params["until"] = until

        if since_modification:
            params["since_modification"] = since_modification
        if until_modification:
            params["until_modification"] = until_modification

        if additional_params:
            params.update(additional_params)

        return params

    def _paginate_results(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        err_msg: str = "Unable to get results"
    ) -> List[Dict[str, Any]]:
        """
        Paginate the results of a request.
        :param url (str): The url to send request to
        :param params (dict, optional): The params of the request
        :param err_msg (str): The message to display on error
        :return list: List of results
        """
        request_params = dict(params or {})
        results: List[Dict[str, Any]] = []

        while True:
            response = self._handler.get(url, params=request_params)
            self._handler.validate_response(response, err_msg)

            json_body = response.json() or {}
            page_results = json_body.get("results", []) or []
            results.extend(page_results)

            cursor = json_body.get("cursor")
            if not cursor:
                break

            request_params["cursor"] = cursor

        return results


class BreachCatalogClient(BaseClient):
    """Endpoints related to breach catalog."""

    def ping(self) -> bool:
        """Validate API connectivity/authentication with a lightweight catalog request."""
        response = self._handler.get(ENDPOINT_PING)
        self._handler.validate_response(
            response,
            "Unable to connect to SpyCloud breach catalog"
        )
        return True

    def catalog(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        params = self._build_date_params(since=since, until=until)
        return self._paginate_results(ENDPOINT_BREACH_CATALOG, params)


class BreachDataClient(BaseClient):
    """Endpoints related to breach data."""

    def watchlist(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None,
        since_modification: Optional[str] = None,
        until_modification: Optional[str] = None,
        severities: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        additional_params: Dict[str, Any] = {}

        if severities:
            additional_params["severity"] = ",".join(str(x) for x in severities)

        params = self._build_date_params(
            since=since,
            until=until,
            since_modification=since_modification,
            until_modification=until_modification,
            additional_params=additional_params
        )
        return self._paginate_results(ENDPOINT_BREACH_DATA_WATCHLIST, params)


class CompassClient(BaseClient):
    """Endpoints related to SpyCloud Compass."""

    @staticmethod
    def _date_only(value: Optional[str]) -> Optional[str]:
        """Normalize Compass date filters to YYYY-MM-DD."""
        if value in (None, ""):
            return value

        text = str(value).strip()
        if len(text) >= 10:
            return text[:10]
        return text

    def data(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        params = self._build_date_params(
            since=self._date_only(since),
            until=self._date_only(until),
        )
        return self._paginate_results(ENDPOINT_COMPASS_DATA, params)


class SpyCloudSDK:
    """Single SDK entrypoint. Expose per-entity clients as attributes."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.spycloud.io",
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
        rate_limit_wait_seconds: float = DEFAULT_RATE_LIMIT_WAIT_SECONDS,
        inter_request_delay_seconds: float = DEFAULT_INTER_REQUEST_DELAY_SECONDS,
        verify_ssl: bool = True,
    ):
        self._handler = APIClient(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            backoff_seconds=backoff_seconds,
            rate_limit_wait_seconds=rate_limit_wait_seconds,
            inter_request_delay_seconds=inter_request_delay_seconds,
            verify_ssl=verify_ssl,
        )
        self._clients = {
            "breach_data": BreachDataClient(self._handler),
            "breach_catalog": BreachCatalogClient(self._handler),
            "compass": CompassClient(self._handler)
        }

    @property
    def breach_data(self) -> BreachDataClient:
        return self._clients["breach_data"]

    @property
    def breach_catalog(self) -> BreachCatalogClient:
        return self._clients["breach_catalog"]

    @property
    def compass(self) -> CompassClient:
        return self._clients["compass"]

    def __getattr__(self, name: str):
        for client in self._clients.values():
            if hasattr(client, name):
                return getattr(client, name)
        raise AttributeError(f"{self.__class__.__name__!s} has no attribute {name!s}")