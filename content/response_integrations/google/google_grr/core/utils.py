from __future__ import annotations
import math

from .exceptions import GoogleGRRValidationException
from soar_sdk.SiemplifyUtils import convert_unixtime_to_datetime
from .consts import UTC
from datetime import timedelta


def convert_size(size_bytes):
    """
    Converts bytes size to the readable units.
    :param size_bytes: {int} Size in bytes
    :return: {str} Formatted size
    """
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MiB", "GB", "TB", "PB", "EB", "ZB", "YB")
    size_unit = int(math.floor(math.log(size_bytes, 1024)))
    power = math.pow(1024, size_unit)
    size = round(size_bytes / power, 1)
    return f"{size}{size_name[size_unit]}"


def extract_interfaces(interfaces):
    """
    Extract values from interface dictionary
    :param interfaces: {dict} Interfaces dictionary.
    :return: {dict} Extracted needed data in a dictionary
    """
    new_interfaces = []
    for inte in interfaces:
        new_interfaces.append(
            {
                "ifname": inte.get("value", {}).get("ifname", {}).get("value", ""),
                "addresses": [
                    {
                        "packed_bytes": address.get("value", {})
                        .get("packed_bytes", {})
                        .get("value", ""),
                        "address_type": address.get("value", {})
                        .get("address_type", {})
                        .get("value", ""),
                    }
                    for address in inte.get("value", {}).get("addresses")
                ],
                "mac_address": inte.get("value", {})
                .get("mac_address", {})
                .get("value", ""),
            }
        )

    return new_interfaces


def load_csv_to_list(csv, param_name):
    """
    Load comma separated values represented as string to a list
    :param csv: {str} of comma separated values with delimiter ','
    :param param_name: {str} the name of the variable we are validation
    :return: {list} of values
            raise AWSGuardDutyValidationException if failed to parse csv
    """
    try:
        return [t.strip() for t in csv.split(",")]
    except Exception:
        raise GoogleGRRValidationException(f"Failed to parse parameter {param_name}")


def get_date_from_rdf_dateframe(name, objects_data):
    """
    Convert RDFDate to formatted date.
    :param name: {str} Name of date parameter
    :param objects_data: The object data that the name should be
    :return: Formatted date
    """
    if objects_data.get(name):
        date = objects_data.get(name, {}).get("value", "")
        date = convert_unixtime_to_datetime(date / 1000)
        return date.strftime("%Y-%m-%d %H:%M:%S") + " " + UTC

    return ""


def add_duration_to_date(rdf_time, duration):
    """
    Add duration (in seconds) to date
    :param rdf_time: {RDFDatetime} RDFDatetime object
    :param duration: {str} seconds to add to date
    :return: {datetime} New date after the duration was added
    """
    date = convert_unixtime_to_datetime(int(rdf_time) / 1000)
    date += timedelta(seconds=int(duration))
    return date.strftime("%Y-%m-%d %H:%M:%S") + " " + UTC
