from __future__ import annotations

import json
import time

import dateparser
import requests
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

BASE_URL = "https://api.logz.io/"
SEARCH_LOGS_API_SUFFIX = "v1/search"
DEFAULT_PAGE_SIZE = 25
MIN_PAGE_SIZE = 1
MAX_PAGE_SIZE = 1000

"""
If this action succeeds, it will return a json in the following format:
{
    "results": [
        # logs
    ]
}
"""


@output_handler
def main():
    siemplify = SiemplifyAction()
    status = EXECUTION_STATE_FAILED  # default. will be changed only if logs retrieved and parsed to json successfully.
    num_logs = 0
    logzio_token = siemplify.extract_configuration_param(
        "Logzio",
        "logzio_operations_token",
        default_value="-",
        is_mandatory=True,
    )
    if logzio_token == "-" or logzio_token == "":
        siemplify.LOGGER.error("Error occurred: no Logzio API token! Exiting.")
        raise ValueError
    logzio_region = siemplify.extract_configuration_param(
        "Logzio",
        "logzio_region",
        default_value="",
    )
    query = siemplify.extract_action_param(
        "query",
        input_type=str,
        is_mandatory=False,
        default_value="*",
    )
    size = get_validated_size(siemplify)
    from_time = get_time_in_unix(siemplify, "from_time")
    to_time = get_time_in_unix(siemplify, "to_time")
    logs_response = execute_logzio_api(
        siemplify,
        logzio_token,
        logzio_region,
        query,
        size,
        from_time,
        to_time,
    )
    if logs_response is not None:
        num_logs = len(logs_response["hits"]["hits"])
        logs_json = get_logs_values(logs_response["hits"]["hits"])
        if logs_json is not None:
            siemplify.LOGGER.info(
                f"Retrieved {len(logs_response['hits']['hits'])} logs that match the query",
            )
            siemplify.result.add_result_json(logs_json)
            status = EXECUTION_STATE_COMPLETED

    output_message = get_output_msg(status, num_logs)
    is_success = status == EXECUTION_STATE_COMPLETED
    siemplify.end(output_message, is_success, status)


def execute_logzio_api(
    siemplify,
    api_token,
    logzio_region,
    query,
    size,
    from_time,
    to_time,
):
    """Sends request to Logz.io and returnes the response, if applicable"""
    try:
        new_request = create_request_body_obj(query, size, from_time, to_time)
        new_logs = search_logs(api_token, new_request, logzio_region, siemplify)
        return new_logs
    except Exception as e:
        siemplify.LOGGER.error(f"Error occurred while searching for logs: {e}")
        return None


def create_request_body_obj(query, size, from_time, to_time):
    """Creates request body to send to Logz.io API"""
    request_body = {
        "query": {"bool": {"must": [{"query_string": {"query": query}}]}},
        "size": size,
    }

    if from_time is not None or to_time is not None:
        time_filter = {}
        if from_time is not None:
            time_filter["from"] = from_time
            time_filter["include_lower"] = True
        if to_time is not None:
            time_filter["to"] = to_time
            time_filter["include_upper"] = True
        request_body["query"]["bool"]["must"].append(
            {"range": {"@timestamp": time_filter}},
        )

    return request_body


def search_logs(api_token, req_body, region, siemplify):
    """Returnes from Logz.io all the logs that match the query.
    If error occured or no results found, returnes None
    """
    headers = {"Content-Type": "application/json", "X-API-TOKEN": api_token}

    url = get_logzio_api_endpoint(
        siemplify,
        region,
    )  # get_base_api_url(region) + SEARCH_LOGS_API_SUFFIX
    siemplify.LOGGER.info(f"api url: {url}")
    try:
        body = json.dumps(req_body)
        siemplify.LOGGER.info(f"Searching logs that match query: {body}")
        response = requests.post(url, headers=headers, data=body, timeout=5)
        siemplify.LOGGER.info(f"Status code from Logz.io: {response.status_code}")
        if response.status_code == 200:
            logs_response = json.loads(response.content)
            if logs_response["hits"]["total"] >= 0:
                return logs_response
            return None
        siemplify.LOGGER.warning(f"API request returned {response.status_code}")
    except Exception as e:
        siemplify.LOGGER.error(
            f"Error occurred while searching & fetching logs from Logz.io:\n{e}",
        )
        return None


def get_base_api_url(region):
    """Returnes API url, in accordance to user's input"""
    if region == "us" or region == "" or region == "-":
        return BASE_URL
    return BASE_URL.replace("api.", f"api-{region}.")


def get_output_msg(status, num_logs):
    """Returnes the output message in accordance to the script status"""
    if status == EXECUTION_STATE_COMPLETED:
        if num_logs == 0:
            return "API call ended successfully with no logs to match the query"
        return f"Retrieved successfully {num_logs} logs that triggered the alert"
    return "Failed to retrieve logs. Please check the script's logs to see what went wrong..."


def get_validated_size(siemplify):
    """Validates and returnes the size param for the query.
    If value is not valid reverts to default size.
    """
    size = siemplify.extract_action_param("size", input_type=str, is_mandatory=False)
    if size is None or size == "":
        siemplify.LOGGER.info(f"No size entered. Using default value: {MAX_PAGE_SIZE}")
        return MAX_PAGE_SIZE
    try:
        size_num = int(size)
        if size_num <= 0 or size_num > MAX_PAGE_SIZE:
            siemplify.LOGGER.warning(
                f"Size should be between 1 and {MAX_PAGE_SIZE}. Reverting to default value: {MAX_PAGE_SIZE}",
            )
            return MAX_PAGE_SIZE
        return size_num
    except Exception as e:
        siemplify.LOGGER.warning(f"{e}\n Reverting to default value {MAX_PAGE_SIZE}")
        return MAX_PAGE_SIZE


def get_time_in_unix(siemplify, param_name):
    """Converts the time the user inserts to unix time"""
    time_input = siemplify.extract_action_param(param_name)
    if time_input is not None and time_input != "":
        if time_input.isdigit():
            return time_input
        try:
            date_time_obj = dateparser.parse(
                time_input,
                settings={"TIMEZONE": "UTC"},
            )
            parsed_time = int(time.mktime(date_time_obj.timetuple())) * 1000
            if parsed_time is None:
                siemplify.LOGGER.warning(
                    f"Couldn't parse {param_name}. Reverting to default time",
                )
            return parsed_time
        except Exception as e:
            siemplify.LOGGER.warning(
                f"Error occurred while parsing {param_name}: {e}\n Reverting to default time",
            )
            return None
    return time_input


def get_logs_values(logs):
    """Extracts the logs from the Logz.io API response, and formats
    them for the output json.
    """
    logs_results = {"results": []}
    for log in logs:
        logs_results["results"].append(log["_source"])

    if len(logs_results) > 0:
        return json.dumps(logs_results)
    return None


def get_logzio_api_endpoint(siemplify, region):
    """Returns the endpoint of Logz.io API.
    Prioritizing a custom endoint, if entered.
    If not, falling back to the regaular enspoints, based on the logzio_region (defaults to us).
    """
    custom_endpoint = siemplify.extract_configuration_param(
        "Logzio",
        "logzio_custom_endpoint",
        is_mandatory=False,
        default_value="",
    )
    if custom_endpoint is not None and custom_endpoint != "":
        siemplify.LOGGER.info(f"Using custom endpoint: {custom_endpoint}")
        return custom_endpoint + SEARCH_LOGS_API_SUFFIX
    return get_base_api_url(region) + SEARCH_LOGS_API_SUFFIX


if __name__ == "__main__":
    main()
