from __future__ import annotations

import datetime
import json
import os

from soar_sdk.SiemplifyLogger import SiemplifyLogger
from soar_sdk.SiemplifyUtils import utc_now
from TIPCommon.types import ChronicleSOAR, SingleJson

from .constants import (
    CONTEXT_VALUE_CHUNK_LIMIT,
    CONTEXT_VALUE_CHUNK_SIZE,
    GLOBAL_TIMEOUT_THRESHOLD_IN_MIN,
    PRODUCT_NAME,
    TICKET_ID,
)


def is_async_action_global_timeout_approaching(siemplify, start_time):
    return (
        siemplify.execution_deadline_unix_time_ms - start_time
        < GLOBAL_TIMEOUT_THRESHOLD_IN_MIN * 60 * 1000
    )


def get_custom_fields_data(
    custom_fields: SingleJson | str | None,
    logger: SiemplifyLogger,
) -> SingleJson:
    """Parses custom fields data from a JSON string or extracts key-value pairs from a
    plain string.

    Args:
        custom_fields (SingleJson | str | None): The custom fields data,
        which can be either a JSON string or a plain string, or None.
        logger(SiemplifyLogger): SiemplifyLogger object for logging errors.

    Returns:
        SingleJson: A dictionary containing the parsed custom fields data. If parsing
        fails, key-value pairs are extracted from the input string.
    """
    if custom_fields is None:
        return {}
    try:
        custom_fields_data = json.loads(custom_fields)

    except (json.JSONDecodeError, TypeError) as e:
        logger.exception(e)
        return separate_key_value_pairs_from_string(custom_fields)

    return custom_fields_data


def separate_key_value_pairs_from_string(pairs_string):
    """
    Convert key:value paired string to dict
    ;:param pairs_string: {str} key:value paired comma separated string
    :return: {dict} {key: value} dict
    """
    custom_fields_dict = {}

    if pairs_string:
        for key_value in pairs_string.split(","):
            key, value = key_value.strip().split(":", 1)
            custom_fields_dict[key.strip().lower()] = value.strip()

    return custom_fields_dict


def get_case_and_alerts_ids(case, alert_id_key="identifier"):
    """
    Extract incident case alerts ids
    :param case: cases object
    :param alert_id_key: key to retrieve alert identifier
    :return: {dict} Dict of {case id, [alert id]}
    """
    case_alert_ids = {}

    for alert in case.get("cyber_alerts", []):
        case_id, alert_id = case.get("identifier"), alert.get(alert_id_key)
        if not alert_id:
            continue

        if not case_alert_ids.get(case_id):
            case_alert_ids[case_id] = []

        case_alert_ids[case_id].append(alert_id)

    return case_alert_ids


def get_incidents_numbers_from_case(
    case: SingleJson,
    chronicle_soar: ChronicleSOAR | None = None,
) -> list[str]:
    """Extract incidents numbers from case.

    Args:
        case(SingleJson): A dict containing case information.
        chronicle_soar(ChronicleSOAR): ChronicleSOAR object.

    Returns:
        list[str]: List of incident numbers.
    """
    incidents_numbers_and_alert_ids = []

    for alert in case.get("cyber_alerts", []):
        incident_and_alert_ids = get_incident_number_from_alert(
            alert=alert,
            chronicle_soar=chronicle_soar,
        )
        if incident_and_alert_ids:
            incident_number, _ = incident_and_alert_ids
            incidents_numbers_and_alert_ids.append(incident_number)

    return incidents_numbers_and_alert_ids


def get_incident_number_from_alert(
    alert: SingleJson,
    chronicle_soar: ChronicleSOAR | None = None,
) -> tuple[str | None, str | None]:
    """Extract incident number from alert.

    Args:
        alert(SingleJson): A dict containing alert information.
        chronicle_soar(ChronicleSOAR): ChronicleSOAR object.

    Returns:
        tuple[str | None, str | None]: Tuple of incident number, alert id or None
    """
    alert_id = alert.get("identifier")

    if alert.get("reporting_product") == PRODUCT_NAME:
        incident_number = alert.get("additional_properties", {}).get("AlertName")
    else:
        incident_number = alert.get("additional_data")
    if not incident_number:
        incident_number = chronicle_soar.get_context_property(
            2,
            alert.get("alert_group_identifier"),
            TICKET_ID,
        )
    if not incident_number:
        return None

    return incident_number, alert_id


def validate_timestamp(last_run_timestamp, offset_in_hours=None):
    """
    Validate timestamp in range
    :param last_run_timestamp: {datetime} last run timestamp
    :param offset_in_hours: {int} backward hours
    :return: {datetime} if first run, return current time minus offset time, else return timestamp from file
    """
    current_time = utc_now()
    # Check if first run
    if not offset_in_hours:
        timedelta = datetime.timedelta()
    else:
        timedelta = datetime.timedelta(hours=offset_in_hours)
    if current_time - last_run_timestamp > timedelta:
        return current_time - timedelta
    else:
        return last_run_timestamp


def save_attachment(path, name, content):
    """
    Save attachment to local path
    :param path: {str} Path of the folder, where files should be saved
    :param name: {str} File name to be saved
    :param content: {str} File content
    :return: {str} Path to the downloaded files
    """
    # Create path if not exists
    if not os.path.exists(path):
        os.makedirs(path)
    # File local path
    local_path = os.path.join(path, name)
    with open(local_path, "wb") as file:
        file.write(content)
        file.close()

    return local_path


def compare_nested_dicts(dict1, dict2, fields_to_exclude=None):
    """
    Compares two nested dicts and returns a dict containing the differences

    Args:
        dict1: first dict
        dict2: second dict
        fields_to_exclude: list of fields to exclude from comparison

    Returns:
        dict containing the differences between the two dicts. Key is a path to
        different value (e.g., 'key1.key2'). Value is a tuple containing values from
        dict1 and dict2 respectively
    """
    differences = {}
    fields_to_exclude = fields_to_exclude if fields_to_exclude else []

    def _compare_dicts(d1, d2, path=""):
        """
        Compares two dicts recursively

        Args:
            d1: first dict
            d2: second dict
            path: path to the current level in the nested structure
        """
        for key, value in d1.items():
            if key in fields_to_exclude:
                continue

            if key not in d2:
                # key exists in dict1 but not in dict2
                if isinstance(value, dict):
                    _compare_dicts(value, {}, f"{path}{key}.")
                    continue

                differences[f"{path}{key}"] = (value, None)
            elif isinstance(value, dict) or isinstance(d2[key], dict):
                # both values are dicts, compare them recursively
                _compare_dicts(value or {}, d2[key] or {}, f"{path}{key}.")
            elif value != d2[key]:
                # different values for the same key
                differences[f"{path}{key}"] = (value, d2[key])

        for key, value in d2.items():
            if key in fields_to_exclude:
                continue

            if key not in d1:
                # key exists in dict2 but not in dict1
                if isinstance(value, dict):
                    _compare_dicts({}, value, f"{path}{key}.")
                    continue

                differences[f"{path}{key}"] = (None, value)

    _compare_dicts(dict1, dict2)
    return differences


def split_dict_into_chunks(
    original_dict,
    chunk_size=CONTEXT_VALUE_CHUNK_SIZE,
    chunk_limit=CONTEXT_VALUE_CHUNK_LIMIT,
):
    """
    Split a dictionary into chunks of chunk_size
    If after splitting chunk size exceeds chunk_limit, the chunk_size will be decreased

    Args:
        original_dict: original dict
        chunk_size: items count per chunk
        chunk_limit: characters count limit per chunk

    Returns:
        list of dicts
    """
    chunks = []
    current_chunk_size = chunk_size
    chunk_size_reduction = 10

    def _split_dict(size):
        chunks.clear()
        items = list(original_dict.items())

        for i in range(0, len(original_dict), size):
            current_chunk = dict(items[i : i + size])

            if len(json.dumps(current_chunk)) > chunk_limit:
                _split_dict(size - chunk_size_reduction)
                break

            chunks.append(current_chunk)

    _split_dict(current_chunk_size)
    return chunks


def set_chunks_as_job_context_property(soar_job, identifier, key, chunks):
    """
    Set job context properties per each chunk with key prefix and unique counter

    Args:
        soar_job: SiemplifyJob
        identifier: context property identifier
        key: key prefix
        chunks: list of chunks to set

    Returns:

    """
    counter = 0

    for chunk in chunks:
        soar_job.set_job_context_property(
            identifier=identifier,
            property_key=f"{key}_{counter}",
            property_value=json.dumps(chunk),
        )
        counter += 1


def get_chunks_as_job_context_property(soar_job, identifier, key):
    """
    Get job context properties chunks per key prefix and unique counter

    Args:
        soar_job: SiemplifyJob
        identifier: context property identifier
        key: key prefix

    Returns:
        dict of all chunks
    """
    counter = 0
    chunks = {}

    while True:
        chunk = soar_job.get_job_context_property(
            identifier=identifier, property_key=f"{key}_{counter}"
        )

        if chunk is None:
            break

        chunks.update(json.loads(chunk))
        counter += 1

    return chunks


def format_text(text, **kwargs):
    """
    Format text with provided arguments
    Args:
        text: {str} text to format
        **kwargs: {dict} arguments to format

    Returns:
        {str} formatted text
    """
    return text.format(**kwargs)
