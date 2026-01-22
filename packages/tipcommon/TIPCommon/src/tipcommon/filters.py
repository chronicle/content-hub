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

import arrow

from .consts import (
    BLACKLIST_FILTER,
    NUM_OF_HOURS_IN_DAY,
    NUM_OF_MILLI_IN_SEC,
    NUM_OF_SEC_IN_SEC,
    WHITELIST_FILTER,
)


def filter_list_by_type(array, inner_type):
    """Filter out any items in the list that are not of the requested type.

    Args:
        array (list[Any]): The list to check
        inner_type (type): The requested type of the items in the list

    Examples:
        >>> arr = [1, 2, "3", 4]
        >>> arr1 = purify_typed_list(arr, int)
        >>> arr2 = purify_typed_list(arr, str)
        >>> arr1
        [1, 2, 4]
        >>> arr2
        ['3']

    Returns:
        list[type[inner_type]: A new array containing only
        the items of type inner_type

    """
    return [item for item in array if isinstance(item, inner_type)]


def filter_old_ids(alert_ids, existing_ids):
    """Filters ids that were already processed.

    Args:
        alert_ids: (list) List of new ids from the alert to filter
        existing_ids: (list) List of ids to compare to

    Returns:
        (list) List of filtered ids

    """
    new_alert_ids = []

    for alert_id in alert_ids:
        if alert_id not in existing_ids:
            new_alert_ids.append(alert_id)

    return new_alert_ids


def filter_old_ids_by_timestamp(ids, offset_in_hours, convert_to_milliseconds, offset_is_in_days):
    """Filters ids that are older than IDS_HOURS_LIMIT hours.

    Args:
        ids: (dict) The ids to filter.
        offset_in_hours: (int) The IDs time limit (offset value) in hours.
        offset_is_in_days: (bool) If the offset supplied to this method is in days, please mark this as True for
                            converting the offset days into hours.
        convert_to_milliseconds: (bool) Transform each ID's timestamp (unix) from seconds to milliseconds.

    Returns:
        (dict) The filtered ids.

    """
    filtered_ids = {}
    milliseconds = NUM_OF_MILLI_IN_SEC if convert_to_milliseconds else NUM_OF_SEC_IN_SEC

    if offset_is_in_days:
        offset_in_hours = offset_in_hours * NUM_OF_HOURS_IN_DAY

    for alert_id, timestamp in ids.items():
        if timestamp > arrow.utcnow().shift(hours=-offset_in_hours).int_timestamp * milliseconds:
            filtered_ids[alert_id] = timestamp

    return filtered_ids


def filter_old_alerts(siemplify, alerts, existing_ids, id_key="alert_id"):
    """Filters alerts that were already processed.

    Args:
        siemplify: (obj) An instance of the SDK `SiemplifyConnectorExecution` class.
        alerts: (list) List of Alert objects.
        existing_ids: (list) List of ids to filter.
        id_key: (str) The key of identifier. The key under which the ids can be found in the alert. Default is "alert_id".

    Returns:
        (list) List of filtered Alert objects.

    """
    filtered_alerts = []

    for alert in alerts:
        ids = getattr(alert, id_key)

        if ids not in existing_ids:
            filtered_alerts.append(alert)
        else:
            siemplify.LOGGER.info(f"The alert {ids} skipped since it has been fetched before")

    return filtered_alerts


def pass_whitelist_filter(siemplify, whitelist_as_a_blacklist, model, model_key, whitelist=None):
    """Determines whether a values from a key in a model pass the whitelist filter.

    Args:
        siemplify: (obj) An instance of the SDK `SiemplifyConnectorExecution` class.
        whitelist_as_a_blacklist: (bool) The value of the Connector's input checkbox `Use whitelist as blacklist`.
        model: (obj) An alert object of some type from which to extract the specific type/id that will be matched
                    against the whitelist.
        model_key: (str) The key (attribute) whose value is the specific type/id that will be matched against
                    the whitelist.
        whitelist: (Iterable) The list from which to search if a value is in order to determine whether it passes
                    the filter. If no value is provided the default will be the full connector's whitelist
                    (as can be seen in Siemplify's UI).

    Returns:
        (bool) True if the model passed the filter successfully else False.

    """
    # whitelist filter
    whitelist = whitelist or siemplify.whitelist
    whitelist_filter_type = BLACKLIST_FILTER if whitelist_as_a_blacklist else WHITELIST_FILTER
    model_value = getattr(model, model_key)
    model_values = model_value if isinstance(model_value, list) else [model_value]

    if whitelist:
        for value in model_values:
            if whitelist_filter_type == BLACKLIST_FILTER and value in whitelist:
                siemplify.LOGGER.info(f"'{value}' did not pass blocklist filter.")
                return False

            if whitelist_filter_type == WHITELIST_FILTER and value not in whitelist:
                siemplify.LOGGER.info(f"'{value}' did not pass allowlist filter.")
                return False

    return True


def filter_none_kwargs(**kwargs):
    """Filters out arguments with `None` values

    Args:
        **kwargs: key-word arguments

    Returns:
        dict: key-word arguments where the arg value is not None

    """
    return {k: v for k, v in kwargs.items() if v is not None}
