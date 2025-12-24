from __future__ import annotations

from datetime import UTC, datetime, timedelta

from TIPCommon.transformation import construct_csv

from .constants import ERRORS, INTEGRATION_NAME, MAX_END_TO_START_DIFF_DAYS


def default_end_date():
    """Returns the current datetime object in UTC timezone as the default end date

    Returns:
        datetime: The current datetime object in UTC timezone

    """
    return datetime.now(UTC)


def default_start_date():
    """Returns the default start date as the current datetime object in UTC timezone minus 29 days as the start date.
    The start date is limited to 29 days prior to the current time to avoid any potential issues with the time delta of 30 days.

    Returns:
        datetime: The default start date as the current datetime object in UTC timezone minus 29 days

    """
    return datetime.now(UTC) - timedelta(days=MAX_END_TO_START_DIFF_DAYS - 1)


def create_tag_list(tags: list) -> list:
    """Takes a list of tag dictionaries and returns a flattened list of all the tags.

    :param tags: A list of tag dictionaries.

    :return: A flattened list of all tags.
    """
    if not tags:
        return []

    all_tags = []
    for tag_dict in tags:
        tag = [tag_dict.get("name", "")]
        child_tags = is_key_value_present(tag_dict, "children")
        if child_tags:
            tag += create_tag_list(child_tags)
        all_tags += tag

    return all_tags


def snake_to_title_case(snake_str):
    """Converts a snake_case string to a title case string.
    :param snake_str: A string in snake_case format
    :return: A string in title case format
    """
    words = snake_str.split("_")
    return " ".join(word.capitalize() for word in words)


def create_row_from_dict(row_dict, ignore_fields=()):
    """Converts a dictionary to a new dictionary where the keys are in title case and certain fields are excluded.
    :param row_dict: The dictionary to convert.
    :param ignore_fields: An iterable of field names to exclude from the output.
    :return: A new dictionary with the keys converted to title case and the ignore_fields excluded.
    """
    return {
        snake_to_title_case(key): value
        for key, value in list(row_dict.items())
        if key not in ignore_fields
    }


def create_table_from_list(table_list, ignore_fields=()):
    """Takes a list of dictionaries and returns a list of dictionaries where each dictionary represents a row in a table.
    The output dictionaries will have the keys converted to title case and will exclude any fields specified in the ignore_fields parameter.
    :param table_list: A list of dictionaries representing the table rows
    :param ignore_fields: A tuple of field names to ignore when creating the table
    :return: A list of dictionaries representing the table rows
    """
    if table_list is None:
        return []

    return [create_row_from_dict(row, ignore_fields) for row in table_list]


def get_integration_params(siemplify):
    """Retrieves the integration parameters from Siemplify configuration.

    :param siemplify: SiemplifyAction instance
    :return: auth_type, api_key, username, password, verify_ssl
    """
    auth_type = siemplify.extract_configuration_param(
        INTEGRATION_NAME,
        "Authentication Type",
        input_type=bool,
    )
    api_key = siemplify.extract_configuration_param(
        INTEGRATION_NAME,
        "API Key",
        default_value="",
    ).strip()
    username = siemplify.extract_configuration_param(
        INTEGRATION_NAME,
        "Username",
        default_value="",
    ).strip()
    password = siemplify.extract_configuration_param(
        INTEGRATION_NAME,
        "Password",
        default_value="",
    ).strip()
    verify_ssl = siemplify.extract_configuration_param(
        INTEGRATION_NAME,
        "Verify SSL",
        input_type=bool,
    )

    return auth_type, api_key, username, password, verify_ssl


def is_key_value_present(dictionary, key):
    """Checks if a key exists in a dictionary and has a value that is not None or "".

    :param dictionary: The dictionary to check
    :param key: The key to check
    :return: True if the key exists and has a non-empty value, False otherwise
    """
    return key in dictionary and dictionary[key]


def get_common_query_parameters(siemplify):
    """Retrieves common query parameters from Siemplify action parameters.

    :param siemplify: SiemplifyAction instance
    :return: A tuple containing a string with error message if any, and a dictionary with the common query parameters.
    """
    start_date = siemplify.extract_action_param("Start Date", default_value="").strip()
    end_date = siemplify.extract_action_param("End Date", default_value="").strip()
    days, size = None, None

    error = ""
    try:
        days = siemplify.extract_action_param("Days", input_type=int)
        size = siemplify.extract_action_param("Size", input_type=int)
    except ValueError:
        error = ERRORS["VALIDATIONS"]["NOT_VALID_INTEGERS"]

    return error, {
        "start_date": start_date,
        "end_date": end_date,
        "days": days,
        "size": size,
    }


def remove_empty_elements(d):
    """Recursively remove empty lists, empty dicts, or None elements from a dictionary.

    :param d: Input dictionary.

    :returns: Dictionary with all empty lists, and empty dictionaries removed.
    """

    def empty(x):
        return x is None or x == {} or x == []

    if not isinstance(d, (dict, list)):
        return d
    if isinstance(d, list):
        return [v for v in (remove_empty_elements(v) for v in d) if not empty(v)]
    return {
        k: v
        for k, v in ((k, remove_empty_elements(v)) for k, v in list(d.items()))
        if not empty(v)
    }


def remove_empty_elements_for_hr(d):
    """Recursively remove empty lists, empty dicts, or None elements from a dictionary.

    :param d (dict): Input dictionary.

    :returns: Dictionary with all empty lists, and empty dictionaries removed.
    """

    def empty(x):
        return x is None or x == {} or x == [] or x == ""

    if not isinstance(d, (dict, list)):
        return d
    if isinstance(d, list):
        return [v for v in (remove_empty_elements_for_hr(v) for v in d) if not empty(v)]
    return {
        k: v
        for k, v in ((k, remove_empty_elements_for_hr(v)) for k, v in list(d.items()))
        if not empty(v)
    }


def remove_nulls_from_dictionary(data):
    """Remove Null values from a dictionary. (updating the given dictionary)

    :params data (dict): The data to be added to the context (required)
    """
    list_of_keys = list(data.keys())[:]
    for key in list_of_keys:
        if data[key] in ("", None, [], {}, ()):
            del data[key]


def create_api_usage_table(data):
    """Creates a table from the given API usage data.

    :param data (dict): The API usage data to be transformed into a table.

    :return: A list of dictionaries representing the table.
    """
    if not data:
        return []

    return [
        {"Parameter": "Used Queries", "Value": data.get("used_queries", "-")},
        {"Parameter": "Remaining Queries", "Value": data.get("remaining_queries", "-")},
        {"Parameter": "Query Limit", "Value": data.get("query_limit", "-")},
        {
            "Parameter": "Foundation Used Queries",
            "Value": data.get("foundation_api_usage", {}).get("used_queries", "-"),
        },
        {
            "Parameter": "Foundation Remaining Queries",
            "Value": data.get("foundation_api_usage", {}).get("remaining_queries", "-"),
        },
        {
            "Parameter": "Foundation Query Limit",
            "Value": data.get("foundation_api_usage", {}).get("query_limit", "-"),
        },
    ]


def merge_ip_summary_responses_for_enrichment(responses):
    """Merge the responses from List IP Summary API calls into a single dictionary.

    The single dictionary will have IP addresses as keys and the IP details as values.
    The API usage will also be merged into a single dictionary.

    :param responses (list): A list of dictionaries containing the API responses.

    :return: A tuple of two dictionaries. The first dictionary contains the IP addresses as keys and the IP details as values.
             The second dictionary contains the API usage.
    """
    merged_response = {}
    usage = {}
    for response in responses:
        data = response.get("data", [])
        for single_ip in data:
            merged_response[single_ip.get("ip")] = single_ip
        usage = response.get("usage")

    return merged_response, usage


def merge_ip_summary_responses(responses):
    """Merge the responses from List IP Summary API calls into a single list and a single dictionary.

    The single list will contain all the IP details from the API calls.
    The single dictionary will contain the API usage.

    :param responses (list): A list of dictionaries containing the API responses.

    :return: A tuple of two values. The first is a list of IP details. The second is a dictionary of API usage.
    """
    merged_response = []
    usage = {}
    for response in responses:
        merged_response += response.get("data", [])
        usage = response.get("usage")

    return merged_response, usage


def render_data_table(siemplify_instance, table_name: str, table_data: list):
    table = [{"": "No data found"}]
    if table_data:
        table = table_data

    siemplify_instance.result.add_data_table(table_name, construct_csv(table))
