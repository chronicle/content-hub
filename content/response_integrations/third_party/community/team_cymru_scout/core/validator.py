from __future__ import annotations

from datetime import UTC, datetime
from ipaddress import ip_address

from .constants import (
    DATE_FORMAT,
    ERRORS,
    MAX_DAYS,
    MAX_END_TO_START_DIFF_DAYS,
    MAX_START_DATE_DAYS,
    MIN_DAYS,
    MIN_SIZE,
)
from .utils import default_end_date, default_start_date


def is_invalid_ip(ip_str: str) -> str:
    """Validates whether the given IP address string is valid or not.

    Args:
        ip_str (str): The IP address string to be validated.

    Returns:
        str: An empty string if the IP address is valid, otherwise a string with the error message.

    """
    try:
        ip_address(ip_str)
        return ""
    except ValueError:
        return ERRORS["VALIDATIONS"]["INVALID_IP"].format(ip_str)


def is_invalid_date(date_str: str, parameter_name: str) -> str:
    """Validates whether the given date string is in 'YYYY-MM-DD' format or not.

    Parameters
    ----------
        date_str (str): The date string to validate.
        parameter_name (str): The name of the parameter for which the date string is being validated.

    Returns
    -------
        str: An error message if the date string is invalid, otherwise an empty string.

    """
    error = ""
    try:
        # Validate whether the date is in 'YYYY-MM-DD' format or not
        if date_str:
            datetime.strptime(date_str, DATE_FORMAT)
    except ValueError:
        error = ERRORS["VALIDATIONS"]["INVALID_DATE"].format(parameter_name, date_str)

    return error


def remove_duplicate_ips(ip_addresses):
    """Removes duplicate IP addresses from a list of IP addresses.

    Args:
        ip_addresses (list): a list of IP addresses

    Returns:
        tuple: a tuple containing a list of unique IPs and a list of duplicate IPs

    """
    unique_ips = []
    duplicates = []

    for ip in ip_addresses:
        if ip in unique_ips:
            duplicates.append(ip)
        else:
            unique_ips.append(ip)

    return unique_ips, duplicates


def validate_multiple_ips(ip_addresses):
    """Validates multiple IP addresses and returns a tuple of valid IPs, invalid IPs, and duplicate IPs.

    Args:
        ip_addresses (list): a list of IP addresses to validate

    Returns:
        tuple: a tuple containing a list of valid IPs, list of invalid IPs, and list of duplicate IPs

    """
    valid_ips, invalid_ips = [], []

    unique_ips, duplicate_ips = remove_duplicate_ips(ip_addresses)

    for ip in unique_ips:
        if is_invalid_ip(ip):
            invalid_ips.append(ip)
        else:
            valid_ips.append(ip)

    return valid_ips, invalid_ips, duplicate_ips


def validate_start_end_dates(start_date, end_date):
    """Validates the start_date and end_date parameters. If both parameters are valid, returns a tuple with two elements. The first element is a boolean indicating whether the parameters are valid. The second element is a tuple with two elements, the validated start_date and end_date respectively.

    Parameters
    ----------
        start_date (str): The start date of the query in 'YYYY-MM-DD' format.
        end_date (str): The end date of the query in 'YYYY-MM-DD' format.

    Returns
    -------
        tuple: A tuple with two elements. The first element is a boolean indicating whether the parameters are valid. The second element is either a tuple with the validated start_date and end_date, or a string with the error message.

    """
    # Validate the start_date input format
    start_error = is_invalid_date(start_date, "Start Date")
    if start_error:
        return False, start_error

    # Validate the end_date input format
    end_error = is_invalid_date(end_date, "End Date")
    if end_error:
        return False, end_error

    # Initialize the default values for start and end dates, in case they are not passed in the action params
    start_date_obj = default_start_date()
    current_date_obj = default_end_date()
    end_date_obj = current_date_obj

    # If the start_date is provided, use it
    if start_date:
        start_date_obj = datetime.strptime(start_date, DATE_FORMAT).replace(tzinfo=UTC)

    # If the end_date is provided, use it
    if end_date:
        end_date_obj = datetime.strptime(end_date, DATE_FORMAT).replace(tzinfo=UTC)

    # start_date must not be greater than the end_date
    if start_date_obj > end_date_obj:
        return False, ERRORS["VALIDATIONS"]["START_GREATER_THAN_END"]

    # end_date must not be a future date
    if end_date_obj > current_date_obj:
        return False, ERRORS["VALIDATIONS"]["END_MUST_NOT_BE_FUTURE"]

    # start_date cannot be older than 90 days from current_date
    if (current_date_obj - start_date_obj).days > MAX_START_DATE_DAYS:
        return False, ERRORS["VALIDATIONS"]["MAX_START_DATE"]

    # Time difference between start and end dates must be less than 30 days
    if (end_date_obj - start_date_obj).days >= MAX_END_TO_START_DIFF_DAYS:
        return False, ERRORS["VALIDATIONS"]["MAX_END_START_DIFF"]

    # start_date and end_date are valid, hence, return them
    start_date = start_date_obj.strftime(DATE_FORMAT)
    end_date = end_date_obj.strftime(DATE_FORMAT)
    return True, (start_date, end_date)


def validate_and_generate_optional_params(start_date, end_date, days, size, max_size):
    """Validates the start_date, end_date, days and size parameters, and if they are valid, returns a dictionary with the
    validated parameters. If any of the parameters are invalid, returns a list of error messages.

    Parameters
    ----------
        start_date (str): The start date of the query.
        end_date (str): The end date of the query.
        days (int): The number of days to query.
        size (int): The number of results to return.
        max_size (int): The maximum number of results to return.

    Returns
    -------
        tuple: A tuple with two elements. The first element is a boolean indicating whether the parameters are valid.
        The second element is either a dictionary with the validated parameters, or a list of error messages.

    """
    is_valid, response = validate_start_end_dates(start_date, end_date)
    if not is_valid:
        return False, [response]

    start_date, end_date = response

    params = {"start_date": start_date, "end_date": end_date}
    error = []

    if days is not None:
        if MIN_DAYS <= days <= MAX_DAYS:
            params["days"] = days
        else:
            error.append(
                ERRORS["VALIDATIONS"]["INVALID_DAYS"].format(days, MIN_DAYS, MAX_DAYS),
            )

    if size is not None:
        if MIN_SIZE <= size <= max_size:
            params["size"] = size
        else:
            error.append(
                ERRORS["VALIDATIONS"]["INVALID_SIZE"].format(size, MIN_SIZE, max_size),
            )

    if not error:
        return True, params

    return False, error
