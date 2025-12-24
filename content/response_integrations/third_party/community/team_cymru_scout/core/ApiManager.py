from __future__ import annotations

import json
import time

import requests

from .constants import (
    ACCOUNT_USAGE_ENDPOINT,
    BACKOFF_FACTOR,
    BASE_URL,
    ERRORS,
    INTEGRATION_NAME,
    IP_DETAILS_ENDPOINT,
    LIST_IPS_ENDPOINT,
    MAX_PAGE_SIZE,
    MAX_RETRY_COUNT,
    SCOUT_SEARCH_ENDPOINT,
)
from .validator import validate_and_generate_optional_params


class ApiManager:
    def __init__(
        self,
        auth_type,
        api_key,
        username,
        password,
        siemplify_logger,
        verify_ssl,
    ):
        self.auth_type = auth_type
        self.api_key = api_key
        self.username = username
        self.password = password
        self.logger = siemplify_logger

        self.session = requests.Session()
        self.session.verify = verify_ssl

        if auth_type is True:
            # check for empty api key
            if not api_key:
                raise Exception(ERRORS["API"]["EMPTY_API_KEY"])
            self.session.headers["Authorization"] = f"Token {api_key}"
        else:
            # check for empty username and password
            if not username or not password:
                raise Exception(ERRORS["API"]["EMPTY_UNAME_PASS"])
            self.session.auth = (username, password)

    def _process_api_error_response(self, response_json):
        output = []

        for field, details in list(response_json.get("inputs", {}).items()):
            field_value = details.get("value", "")
            field_errors = details.get("errors", "")

            if field_errors:
                error_messages = ", ".join(field_errors)
                output.append(f"  - {field}: '{field_value}' - {error_messages}")

        print("API response:\n" + json.dumps(response_json, indent=2))
        if output:
            return "Errors encountered:\n" + "\n".join(output) + "\n"
        return "Something went wrong."

    def call_api(self, endpoint, query_params=None):
        status = False
        return_value = ""
        retry = False

        if query_params is None:
            query_params = {}

        self.logger.info(
            f"Calling {INTEGRATION_NAME} endpoint: {BASE_URL + endpoint} with params: {query_params}",
        )

        response = self.session.get(BASE_URL + endpoint, params=query_params)
        status_code = response.status_code

        if status_code == 200:
            status = True
            return_value = response.json()
        elif status_code == 401:
            return_value = ERRORS["API"]["INVALID_UNAME_PASS"]
            if self.auth_type is True:
                return_value = ERRORS["API"]["INVALID_API_KEY"]
        elif status_code == 429 or status_code >= 500:
            return_value = ERRORS["API"]["RETRY"].format(status_code)
            retry = True
        elif status_code >= 400:
            try:
                return_value = f"{status_code}: {self._process_api_error_response(response.json())}"
            except json.JSONDecodeError as json_err:
                print(f"Error: {json_err!s} {status_code}: {response.text}")
                return_value = f"{status_code}: Something went wrong."

        return status, return_value, retry

    def call_api_with_retry(self, endpoint, query_params=None):
        if query_params is None:
            query_params = {}

        for retry_count in range(MAX_RETRY_COUNT + 1):
            status, response, retry = self.call_api(endpoint, query_params)
            if not retry:
                return status, response

            if retry_count == MAX_RETRY_COUNT:
                break

            time_to_sleep = (retry_count + 1) * BACKOFF_FACTOR
            self.logger.info(
                f"Failed to call: {endpoint} with params: {query_params}. Retry count: {retry_count + 1}. "
                f"Retrying after {time_to_sleep} seconds.",
            )

            time.sleep(time_to_sleep)

        error = ERRORS["API"]["MAX_RETRIES"].format(MAX_RETRY_COUNT, response)
        return status, error

    def api_usage(self):
        return self.call_api_with_retry(ACCOUNT_USAGE_ENDPOINT)

    def get_ip_details(self, ip_address, params):
        ip_endpoint = IP_DETAILS_ENDPOINT.format(ip_address)
        return self.call_api_with_retry(ip_endpoint, query_params=params)

    def scout_search(self, query, start_date, end_date, days, size):
        if not query:
            return False, "Query parameter must be provided for Scout Search"

        # Validate and generate the additional optional query parameters
        is_valid, params_response = validate_and_generate_optional_params(
            start_date,
            end_date,
            days,
            size,
            max_size=MAX_PAGE_SIZE["SCOUT_SEARCH"],
        )
        if not is_valid:
            return False, params_response

        params_response["query"] = query
        return self.call_api_with_retry(
            SCOUT_SEARCH_ENDPOINT,
            query_params=params_response,
        )

    def list_ips_summary(self, ips):
        return self.call_api_with_retry(
            LIST_IPS_ENDPOINT,
            query_params={"ips": ",".join(ips)},
        )
