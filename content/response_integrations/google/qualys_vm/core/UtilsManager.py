from __future__ import annotations

import csv
import sys

from TIPCommon import convert_comma_separated_to_list, write_ids_with_timestamp

from .constants import SEVERITIES


def read_csv(csv_lines: list[str]) -> list[list[str]]:
    """Get CSV lines as a list of lines, where each line is a list of values.

    Args:
        csv_lines (list[str]): List of CSV lines, where each line is a string.

    Returns:
        list[list[str]]: Parsed CSV data as a list of values.
    """
    try:
        return list(csv.reader(csv_lines))

    except csv.Error:
        increase_csv_field_size_limit()
        return list(csv.reader(csv_lines))


def increase_csv_field_size_limit() -> None:
    """Increase the csv.field_size_limit to the maximum possible value of the system."""
    max_size: int = sys.maxsize
    default_size: int = csv.field_size_limit()

    while max_size > default_size:
        try:
            csv.field_size_limit(max_size)
            break

        except OverflowError:
            max_size //= 10


def filter_old_alerts(logger, alerts, existing_ids, id_key="entry"):
    """
    Filter alerts that were already processed
    :param logger: {SiemplifyLogger} Siemplify logger
    :param alerts: {list} List of Alert objects
    :param existing_ids: {list} List of ids to filter
    :param id_key: {str} The key of identifier
    :return: {list} List of filtered Alert objects
    """
    filtered_alerts = []

    for alert in alerts:
        id = getattr(alert, id_key)

        if id not in existing_ids.get(alert.host_id, []):
            filtered_alerts.append(alert)
        else:
            logger.info(f"The detection {id} skipped since it has been fetched before")

    return filtered_alerts


def pass_severity_filter(siemplify, alert, lowest_severity):
    # severity filter
    if lowest_severity:
        filtered_severities = (
            SEVERITIES[SEVERITIES.index(lowest_severity) :]
            if lowest_severity in SEVERITIES
            else []
        )
        if not filtered_severities:
            siemplify.LOGGER.info(
                'Severity is not checked. Invalid value provided for "Lowest Severity To Fetch" '
                "parameter. Possible values are: 1, 2, 3, 4, 5."
            )
        if filtered_severities and alert.severity not in filtered_severities:
            siemplify.LOGGER.info(
                "Detection with severity: {} did not pass filter. Lowest severity to fetch is "
                "{}.".format(alert.severity, lowest_severity)
            )
            return False
    return True


def pass_status_filter(siemplify, alert, status_filter):
    # status filter
    statuses = [
        status.capitalize() for status in convert_comma_separated_to_list(status_filter)
    ]
    if statuses and alert.status not in statuses:
        siemplify.LOGGER.info(
            f"Detection with status: {alert.status} did not pass filter. Acceptable statuses are: {status_filter}."
        )
        return False
    return True


def write_ids(siemplify, ids, stored_ids_limit):
    """
    Write IDs into a ConnectorDBStream object.
    :param siemplify: {Siemplify} Siemplify object.
    :param ids: {dict} The ids to write to the file
    :param stored_ids_limit: (int) The number of recent IDs from the existing ids which will be written.
    """
    for key, value in ids.items():
        ids[key] = value[-stored_ids_limit:]

    write_ids_with_timestamp(siemplify, ids)
