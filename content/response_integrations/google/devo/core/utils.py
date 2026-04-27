from __future__ import annotations
from typing import List
from .consts import (
    NOW,
    WHITELIST_BLACKLIST_PARAMETER_NAME,
    WHITELIST_FILTER_OPERATOR,
    BLACKLIST_FILTER_OPERATOR,
    OR_OPERATOR,
    AND_OPERATOR,
)
from .exceptions import DevoManagerErrorValidationException
import dateutil.parser


WHITELIST_FILTER = 1
BLACKLIST_FILTER = 2


def remove_empty_kwargs(**kwargs) -> dict:
    """
    Remove keys from dictionary that has empty value (None, empty list, dict, str..)
    :param kwargs: key value arguments
    :return: dictionary without keys that have the value None
    """
    return {k: v for k, v in kwargs.items() if v or isinstance(v, bool)}


def get_timestamp_from_iso8601(iso8601_time: str) -> int:
    """
    Convert ISO 8601 time (2021-08-05T05:18:42Z) to timestamp (1632133049)
    :param iso8601_time: {str} ISO 8601 time (2021-08-05T05:18:42Z)
    :return: {int} timestamp (1632133049)
    """
    return int(dateutil.parser.parse(iso8601_time).timestamp())


def get_start_end_timestamp(start_time: str = None, end_time: str = None) -> (int, int):
    """
    Convert timeframe (start/end time) to timestamps and validate that the times are valid.
    :param start_time: {str} ISO 8601 time (2021-08-05T05:18:42Z)
    :param end_time: {str} ISO 8601 time (2021-08-05T05:18:42Z)
    :return: {Tup(int, int)} timestamp (1632133049, 1632133049)
    """
    if not start_time:
        raise DevoManagerErrorValidationException(
            "'Start Time' should be provided, when 'Custom' is selected in the 'Time Frame' parameter."
        )
    try:
        start_time_as_timestamp = get_timestamp_from_iso8601(start_time)
        end_time_as_timestamp = (
            NOW if not end_time else get_timestamp_from_iso8601(end_time)
        )
    except Exception as error:
        raise DevoManagerErrorValidationException(
            "The provided 'Start' or 'End' times are not in a valid format."
        )

    if end_time is not None and start_time > end_time:
        raise DevoManagerErrorValidationException(
            "'End Time' should be later than 'Start Time'."
        )

    return start_time_as_timestamp, end_time_as_timestamp


def build_devo_query(
    table_name: str,
    fields_to_return: str = None,
    where_filter: str = None,
    whitelist_blacklist_mode: int = None,
    whitelist_blacklist: List = None,
    whitelist_blacklist_param_name: str = WHITELIST_BLACKLIST_PARAMETER_NAME,
) -> str:
    """
    Build a Devo query with the provided fields to return and filters.
    :param table_name: {str} The table to get data from
    :param fields_to_return: {str} Comma-separated field names to return. For example: eventdate, priority
    :param where_filter: {str} Comma-separated filters to filter the data from Devo. For example: priority > 5.0
    :param whitelist_blacklist_mode: {int} If not None, handling the case of whitelist/blacklist parameter
    :param whitelist_blacklist_param_name: {str} The name of the whitelist_blacklist parameter
    :param whitelist_blacklist: {[str]} The Whitelist/Blacklist
    :return: {str} Formatted query. For Example: "from siem.logtrust.alert.info where priority > 6.0 select eventdate"
    """
    query = f"from {table_name}"
    where_filter_list = []
    if where_filter:
        where_filter_list.append(where_filter)

    if (
        whitelist_blacklist_mode
        and whitelist_blacklist_param_name
        and whitelist_blacklist
    ):
        _operator = (
            WHITELIST_FILTER_OPERATOR
            if whitelist_blacklist_mode == WHITELIST_FILTER
            else BLACKLIST_FILTER_OPERATOR
        )
        _logic_operator = (
            OR_OPERATOR
            if whitelist_blacklist_mode == WHITELIST_FILTER
            else AND_OPERATOR
        )
        whitelist_blacklist_str = f" {_logic_operator} ".join(
            [
                f'{whitelist_blacklist_param_name}{_operator}"{curr_param}"'
                for curr_param in whitelist_blacklist
            ]
        )
        where_filter_list.append(whitelist_blacklist_str)

    if where_filter_list:
        query += f' where {", ".join(where_filter_list)}'

    if fields_to_return:
        query += f" select {fields_to_return}"

    return query


def load_csv_to_list(csv: str, param_name: str):
    """
    Load comma separated values represented as string to a list. Remove duplicates if exist
    :param csv: {str} of comma separated values with delimiter ','
    :param param_name: {str} the name of the parameter we are loading csv to list
    :return: {[str]} List of separated string values
            raise DevoManagerErrorValidationException if failed to parse csv string
    """
    try:
        return list(set([t.strip() for t in csv.split(",")]))
    except Exception:
        raise DevoManagerErrorValidationException(
            f'Failed to load comma separated string parameter "{param_name}"'
        )


def load_kv_csv_to_dict(kv_csv: str, param_name: str):
    """
    Load comma separated values of 'key':'value' represented as string to a dictionary
    :param kv_csv: {str} of comma separated values of 'key':'value' represented as a string
    :param param_name: {str} name of the parameter
    :return: {dict} of key:value
            raise DevoManagerErrorValidationException if failed to parse key value csv
    """
    try:
        return {
            kv.split(":")[0].strip(): kv.split(":")[1].strip()
            for kv in kv_csv.split(",")
        }
    except Exception:
        raise DevoManagerErrorValidationException(
            f'Failed to load comma separated key:value string parameter "{param_name}"'
        )


def pass_whitelist_filter(
    siemplify, whitelist_as_a_blacklist, model, model_key, whitelist=None
):
    # whitelist filter
    whitelist = whitelist or siemplify.whitelist
    whitelist_filter_type = (
        BLACKLIST_FILTER if whitelist_as_a_blacklist else WHITELIST_FILTER
    )
    model_value = getattr(model, model_key)
    model_values = model_value if isinstance(model_value, list) else [model_value]

    if whitelist:
        for value in model_values:
            if whitelist_filter_type == BLACKLIST_FILTER and value in whitelist:
                siemplify.LOGGER.info(f"'{value}' did not pass blacklist filter.")
                return False

            if whitelist_filter_type == WHITELIST_FILTER and value not in whitelist:
                siemplify.LOGGER.info(f"'{value}' did not pass whitelist filter.")
                return False

    return True
