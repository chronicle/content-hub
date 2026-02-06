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
from typing import Iterable, Any
import functools
import inspect
import os
from pathlib import Path
import re
import argparse
import sys
import tempfile
import uuid
import requests
from SiemplifyAddressProvider import BASE_1P_SDK_CONTROLLER_VERSION
from TIPCommon.types import ChronicleSOAR, SingleJson
from .consts import (
    ENTITY_OG_ID_KEY,
    FALSE_VAL_LOWER_STRINGS,
    NO_CONTENT_STATUS_CODE,
    ONE_PLATFORM_ARG,
    SIEM_ID_ATTR_KEY,
    TRUE_VAL_LOWER_STRINGS,
    _CAMEL_TO_SNAKE_PATTERN1,
    _CAMEL_TO_SNAKE_PATTERN2,
)


def get_unique_items_by_difference(item_pool, items_to_remove):
    # type: (Iterable, Iterable) -> list
    """Get set difference items from two iterables (item_pool - items_to_remove)
    Args:
        item_pool (Iterable): The item pool to filter from
        items_to_remove (Iterable): The items that should be removed if exist
    Returns:
        list:
            A list containing unique items from item_pool that were not part of
            items_to_remove
    """
    return list(set(item_pool).difference(items_to_remove))


def get_entity_original_identifier(entity):
    """Helper function for getting entity original identifier
    Args:
        entity (Entity): The entity from which function will get original identifier
    Returns:
        str: The original identifier
    """
    return entity.additional_properties.get(ENTITY_OG_ID_KEY, entity.identifier)


def is_test_run(sys_argv):
    """
    Return a boolean value that indicates whether the connector's execution state.
    Args:
        sys_argv (_type_): _description_
    Returns:
        _type_: _description_
    """
    return not (len(sys_argv) < 2 or sys_argv[1] == "True")


def is_first_run(sys_argv):
    """
    Return a boolean value that indicates whether the action is being
    executed asynchronously.
    Args:
        sys_argv: The command line arguments from the sys module: sys.argv
    Returns:
        True if the action is being executed asynchronously else False.
    """
    return len(sys_argv) < 3 or sys_argv[2] == "True"


def clean_result(value):
    """
    Strip the value from unnecessary spaces before or after the value.
    Args:
        value (str): The value to clean.
    Returns:
        str: A cleaned version of the original value.
    """
    try:
        return value.strip()
    except Exception:
        return value


def is_python_37():
    """
    Check if the python version of the system is 3.7 or above.
    Args:
        None.
    Returns:
        bool: True if the current python version is at least 3.7.
    """
    return sys.version_info >= (3, 7)


def platform_supports_db(siemplify):
    """
    Check if the platform supports database usage.
    Args:
        siemplify (object): The siemplify SDK object.
    Returns:
        True if the siemplify SDK object has an attribute called
        "set_connector_context_property" or "set_job_context_property".
    """
    return hasattr(siemplify, "set_job_context_property") or hasattr(
        siemplify, "set_connector_context_property"
    )


def is_empty_string_or_none(data):
    """
    Check if the data is an 'empty string' or 'None'.
    Args:
        data (str): The data to check.
    Returns:
        bool: True if the supplied data is 'None', or if it only contains an
        empty string "".
    """
    if data is None or data == "":
        return True
    return False


def cast_keys_to_int(data):
    """
    Cast the keys of a dictionary to integers.
    Args:
        data (dict): The data whose keys will be cast to ints.
    Returns:
        dict: A new dict with its keys as ints.
    """
    return {int(k): v for k, v in data.items()}


def none_to_default_value(value_to_check, value_to_return_if_none):
    """
    Check if the current value is None. If it is, replace it with another value. If not,
    return the original value.
    Args:
        value_to_check (dict/list/str): The value to check.
        value_to_return_if_none (dict/list/str): The value to return if `value_to_check`
        is None.
    Returns:
        dict/list/str: The original value of `value_to_check` if it is not None, or
        `value_to_return_if_none` if it is None.
    """
    if value_to_check is None:
        value_to_check = value_to_return_if_none
    return value_to_check


def camel_to_snake_case(string):
    """
    Convert a camel case string to snake case
    :param string: (str) the string to convert
    :return: (str) the converted string
    """
    string = string.replace(" ", "")
    string = _CAMEL_TO_SNAKE_PATTERN1.sub(r"\1_\2", string)
    return _CAMEL_TO_SNAKE_PATTERN2.sub(r"\1_\2", string).lower()


def is_overflowed(siemplify, alert_info, is_test_run):
    """
    Checks if overflowed.
    Args:
        siemplify: (obj) An instance of the SDK `SiemplifyConnectorExecution` class
        alert_info: (AlertInfo)
        is_test_run: (bool) Whether test run or not.
    Returns:
        `True` if the alert is overflowed, `False` otherwise.
    """
    params = {
        "environment": alert_info.environment,
        "alert_identifier": alert_info.ticket_id,
        "alert_name": alert_info.rule_generator,
        "product": alert_info.device_product,
    }
    #   Check if 'siem_alert_id' is a valid argument in the SDK overflow method
    #   un-coupled from SDK version
    try:
        method_args = get_function_arg_names(siemplify.is_overflowed_alert)
        if SIEM_ID_ATTR_KEY in method_args:
            params[SIEM_ID_ATTR_KEY] = getattr(alert_info, SIEM_ID_ATTR_KEY, None)
    except Exception as e:
        siemplify.LOGGER.error(
            f"Error {e}. {SIEM_ID_ATTR_KEY} argument will not be used in Overflow check"
            f" for alert {alert_info.ticket_id}."
        )
    try:
        return siemplify.is_overflowed_alert(**params)
    except Exception as err:
        siemplify.LOGGER.error(f"Error validation connector overflow, ERROR: {err}")
        siemplify.LOGGER.exception(err)
        if is_test_run:
            raise
    return False


def get_function_arg_names(func):
    """Retrieves all of the argument names of a specific function.
    Args:
        func: (Callable) The function or method to analyze
    Returns:
        list: All of the argument keys defined in the given fucntion
    """
    if is_python_37():
        method_args = inspect.getfullargspec(func)[0]
    else:
        # Python 2.7 as it is the only other python version supported in
        # SOAR integrations virtual envs.
        method_args = inspect.getargspec(func)[0]
    return method_args


def safe_cast_bool_value_from_str(default_value):
    """Check if a default value is a string containing boolean value
    If it is, convert it to boolean, else return it
    Args:
        default_value: The default value to return if the casting fails
    Returns:
        The casted value or the default value
    """
    if not isinstance(default_value, str):
        return default_value
    lowered = default_value.lower()
    if lowered in TRUE_VAL_LOWER_STRINGS:
        default_value = True
    elif lowered in FALSE_VAL_LOWER_STRINGS:
        default_value = False
    return default_value


def safe_cast_int_value_from_str(default_value):
    """Check if a default value is a string containing integer value
    If it is, convert it to boolean, else return it
    Args:
        default_value: The default value to return if the casting fails
    Returns:
        The casted value or the default value
    """
    if not isinstance(default_value, str):
        return default_value
    try:
        default_value = int(default_value)
    except ValueError:
        # If it's not an int then an error will be raised in the extract
        # method
        pass
    return default_value


def is_valid_email(email_addr):
    """Check if a provided value is a valid email address.
    Args:
        email_addr (str): Email address to check
    Returns:
        bool: True if email is valid else False
    """
    return re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+[.][A-Za-z]{2,}$", email_addr) is not None


@functools.singledispatch
def create_and_write_to_tempfile(content: str | bytes) -> Path:
    """Generic function for writing content to a temporary file."""
    raise TypeError(f"Unsupported type: {type(content)}")


@create_and_write_to_tempfile.register
def _(content: str) -> Path:
    """Creates a temporary file, writes string content, and returns the file path."""
    return _create_and_write_to_tempfile(content, mode="w", encoding="utf-8")


@create_and_write_to_tempfile.register
def _(content: bytes) -> Path:
    """Creates a temporary file, writes bytes content, and returns the file path."""
    return _create_and_write_to_tempfile(content, mode="wb", encoding=None)


def _create_and_write_to_tempfile(
    content: str | bytes,
    mode: str,
    encoding: str | None,
) -> Path:
    """Creates a temporary file, writes content into it, and returns the file path.
    Allows reading the content later, but does not delete the file automatically.
    Args:
        content (str | bytes): Content to write to the temporary file.
        mode (str): File mode to write the content.
        encoding (str | None): Encoding type.
    Returns:
        Path: Path object of temporary file.
    """
    temp_path: Path | None = None
    try:
        fd, temp_path = tempfile.mkstemp()
        temp_path = Path(temp_path)
        with os.fdopen(fd, mode, encoding=encoding) as temp_file:
            temp_file.write(content)
        return temp_path
    except (OSError, IOError, PermissionError) as error:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except (FileNotFoundError, OSError) as cleanup_error:
                raise cleanup_error from error
        raise error


def platform_supports_1p_api() -> bool:
    """
    Check whether the platform is 1p or not.
    Returns:
        bool: True if platform is 1p, False otherwise.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(ONE_PLATFORM_ARG, action="store_true")
    args, _ = parser.parse_known_args(sys.argv[1:])
    return args.onePlatformSupport


def get_value_from_json(data: SingleJson, *keys: str, default: Any = None) -> Any:
    """
    Get a value from a JSON/dictionary using fallback keys.
    Tries keys in order and returns the value for the first key found.
    If none of the keys exist, returns the default value.
    Args:
        data: The dictionary/JSON data to search in
        *keys: Variable number of keys to try in order
        default: Value to return if none of the keys are found
    Returns:
        The value for the first key found, or default if no keys exist
    Examples:
        >>> d = {"new_key": "value1", "old_key": "value2"}
        >>> get_value_from_json(d, "new_key", "old_key", default="not_found")
        'value1'
        >>> get_value_from_json(d, "missing", "old_key", default="not_found")
        'value2'
        >>> get_value_from_json(d, "missing1", "missing2", default="not_found")
        'not_found'
    """
    if not keys:
        raise TypeError("get_value_from_json() expected at least 1 key argument")
    for key in keys:
        if key in data:
            return data[key]
    return default


def is_valid_uuid(string: str) -> bool:
    """Check if a string is a valid UUID (version 4).
    Args:
        string: The string to check.
    Returns:
        True if the string is a valid UUID v4, False otherwise.
    """
    try:
        val = uuid.UUID(string, version=4)
    except (TypeError, ValueError):
        return False
    return str(val) == string and val.version == 4


def get_sdk_api_uri(chronicle_soar: ChronicleSOAR) -> str:
    """Get Google SecOps URI.
    Args:
        chronicle_soar: The ChronicleSOAR object.
    Returns:
        str: Google SecOps URI.
    """
    if platform_supports_1p_api():
        return chronicle_soar.sdk_config.one_platform_api_root_uri_format.format(
            BASE_1P_SDK_CONTROLLER_VERSION
        )
    return f"{chronicle_soar.API_ROOT}/external/v1"


def escape_odata_literal(value: Any) -> Any:
    """
    Escapes single quotes in a string for OData literal usage by doubling them.
    This is necessary to ensure that single quotes within string literals
    are properly escaped when constructing OData queries with $filter expressions.
    Args:
        value (Any): The raw string value. if other data type provided, It will not be
        processed.
    Returns:
        Any: The escaped string with single quotes doubled if str else return without
        processing.
    """
    if not isinstance(value, str):
        return value
    return value.replace("'", "''")


def safe_json_for_204(
    response: requests.Response,
    default_for_204: list[SingleJson] | SingleJson | None = None,
) -> list[SingleJson] | SingleJson:
    """Safely handles 204 and invalid JSON.
    204 responses do not contain a body, so attempting to parse them as JSON
    would raise an error. This function checks for a 204 status code and returns
    a default value if provided, or an empty list otherwise. For other status codes,
    it attempts to parse the response as JSON.
    Args:
        response (requests.Response): The HTTP response object.
        default_for_204 (None | list[SingleJson] | SingleJson): The default value to
            return for 204 responses. If None, returns an empty list.
    Returns: list[SingleJson] | SingleJson: The JSON content of the response or the
            default value for 204 responses.
    """
    if response.status_code == NO_CONTENT_STATUS_CODE:
        return {} if default_for_204 is None else default_for_204
    return response.json()


def temporarily_remove_header(header_name: str):
    """A decorator that temporarily removes a specified header from the session headers
    before calling the decorated method, and then restores it afterwards.
    This is useful for API calls that might behave unexpectedly or return errors
    if certain headers (like 'Prefer') are present, even if they are not
    relevant to that specific call.
    Args:
        header_name (str): The name of the header to temporarily remove.
    Returns:
        callable: A decorator function.
    """

    def decorator(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            session = self.chronicle_soar.session
            old = session.headers.pop(header_name, None)
            try:
                return method(self, *args, **kwargs)
            finally:
                if old is not None:
                    session.headers[header_name] = old

        return wrapper

    return decorator


def merge_and_sort(
    list_1: Iterable[tuple[int, int]],
    list_2: Iterable[tuple[int, int]],
) -> list[tuple[int, int]]:
    """
    Merges two iterables of (id, timestamp) tuples, with datab taking precedence
    in case of duplicate ids, and sorts the result by timestamp.
    Args:
        dataa (Iterable[tuple[int, int]]): First iterable of (id, timestamp) tuples.
        datab (Iterable[tuple[int, int]]): Second iterable of (id, timestamp
            tuples), which takes precedence over dataa for duplicate ids.
    Returns:
        list[tuple[int, int]]: Merged and sorted list of (id, timestamp) tuples.
    """
    merged = {}
    for _id, ts in list_1:
        merged[_id] = ts
    for _id, ts in list_2:
        merged[_id] = ts
    return sorted(merged.items(), key=lambda x: x[1])
