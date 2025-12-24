from __future__ import annotations

import ipaddress
import json
from typing import Any, Dict, List, Optional, Tuple, Union

from .constants import (
    CREATE_HOST_RECORD_ACTION_IDENTIFIER,
    DELETE_RESPONSE_POLICY_ZONE_ACTION_IDENTIFIER,
    DELETE_RPZ_RULE_ACTION_IDENTIFIER,
    INTEGRATION_NAME,
    MAX_JSON_CHARS,
    PING_ACTION_IDENTIFIER,
    UPDATE_RPZ_CNAME_ACTION_IDENTIFIER,
)
from .infoblox_exceptions import (
    InfobloxException,
    InternalSeverError,
    InvalidIntegerException,
    ItemNotFoundException,
)


def get_integration_params(siemplify: Any) -> Tuple[str, str, str, bool]:
    """
    Retrieve the integration parameters from Siemplify configuration.

    Args:
        siemplify (SiemplifyAction): SiemplifyAction instance

    Returns:
        tuple: A tuple containing the integration parameters.
    """
    api_root = siemplify.extract_configuration_param(
        INTEGRATION_NAME, "API Root", input_type=str, is_mandatory=True
    )
    username = siemplify.extract_configuration_param(
        INTEGRATION_NAME,
        "Username",
        input_type=str,
        is_mandatory=True,
        print_value=False,
    )
    password = siemplify.extract_configuration_param(
        INTEGRATION_NAME,
        "Password",
        input_type=str,
        is_mandatory=True,
        print_value=False,
    )
    verify_ssl = False

    return api_root, username, password, verify_ssl


def clean_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Remove keys with None values from a dictionary."""
    return {k: v for k, v in params.items() if v is not None}


def validate_required_string(value: Optional[str], param_name: str) -> str:
    if not value or not value.strip():
        raise ValueError(f"{param_name} must be a non-empty string.")
    return value


def validate_additional_params(additional_params: Optional[str]) -> Dict[str, Any]:
    """
    Validate additional_params.
    """
    # Handle additional_params
    if additional_params:
        try:
            additional_params_obj = json.loads(additional_params)
            if not isinstance(additional_params_obj, dict):
                raise ValueError("Additional Parameters must be a JSON object.")

            return additional_params_obj
        except Exception:
            raise ValueError("Additional Parameters must be a JSON object.")

    return {}


def validate_integer_param(
    value: Union[int, str],
    param_name: str,
    zero_allowed: bool = False,
    allow_negative: bool = False,
    max_value: Optional[int] = None,
) -> int:
    """
    Validates if the given value is an integer and meets the specified requirements.

    Args:
        value (int|str): The value to be validated.
        param_name (str): The name of the parameter for error messages.
        zero_allowed (bool, optional): If True, zero is a valid integer. Defaults to False.
        allow_negative (bool, optional): If True, negative integers are allowed. Defaults to False.
        max_value (int, optional): If set, value must be less than max value.
    Raises:
        InvalidIntegerException: If the value is not a valid integer or does not meet the rules.
    Returns:
        int: The validated integer value.
    """
    try:
        int_value = int(value)
    except (ValueError, TypeError):
        raise InvalidIntegerException(f"{param_name} must be an integer.")
    if not allow_negative and int_value < 0:
        raise InvalidIntegerException(f"{param_name} must be a non-negative integer.")
    if not zero_allowed and int_value == 0:
        raise InvalidIntegerException(f"{param_name} must be greater than zero.")
    if max_value and int_value > max_value:
        raise InvalidIntegerException(
            f"{param_name} value must be less than or equal to {max_value}."
        )
    return int_value


def string_to_list(items_str: Optional[str]) -> List[str]:
    if not items_str:
        return []
    return [item.strip() for item in items_str.split(",") if item.strip()]


def truncate_json_for_display(data: Any, max_chars: int = MAX_JSON_CHARS) -> str:
    """
    Convert JSON to a string. If it's too long, truncate and add a suffix.
    """
    try:
        json_str = json.dumps(data)
    except (TypeError, ValueError) as e:
        return f"[Invalid JSON] {str(e)}"

    if len(json_str) > max_chars:
        return json_str[:max_chars] + "... [truncated]"
    return json_str


def validate_enum(
    value: Optional[str], allowed_values: List[str], param_name: str
) -> Optional[str]:
    if value is not None and value not in allowed_values:
        raise ValueError(f"{param_name} must be one of {allowed_values}. Got: {value}")
    return value


def create_rpz_rule_name(name: str, rp_zone: str) -> str:
    if name.endswith(rp_zone):
        return name
    return f"{name}.{rp_zone}"


class HandleExceptions(object):
    """
    A class to handle exceptions based on different actions.
    """

    def __init__(
        self,
        api_identifier: str,
        error: Exception,
        response: Any,
        error_msg: str = "An error occurred",
    ) -> None:
        """
        Initializes the HandleExceptions class.

        Args:
            api_identifier (str): API Identifier.
            error (Exception): The error that occurred.
            error_msg (str, optional): A default error message. Defaults to "An error occurred".
        """
        self.api_identifier = api_identifier
        self.error = error
        self.response = response
        self.error_msg = error_msg

    def do_process(self) -> None:
        """
        Processes the error by calling the appropriate handler.
        """
        if self.response.status_code >= 500:
            raise InternalSeverError(
                "It seems like the Infoblox server is experiencing some issues, "
                + f"Status: {self.response.status_code}"
            )

        try:
            handler = self.get_handler()
            _exception, _error_msg = handler()
        except InfobloxException:
            _exception, _error_msg = self.common_exception()

        raise _exception(_error_msg)

    def get_handler(self) -> callable:
        """
        Retrieves the appropriate handler function based on the api_name.

        Returns:
            function: The handler function corresponding to the api_name.
        """
        return {
            PING_ACTION_IDENTIFIER: self.ping,
            DELETE_RESPONSE_POLICY_ZONE_ACTION_IDENTIFIER: self._handle_rp_zone_error,
            DELETE_RPZ_RULE_ACTION_IDENTIFIER: self._handle_rpz_rule_error,
            CREATE_HOST_RECORD_ACTION_IDENTIFIER: self._handle_host_record_error,
            UPDATE_RPZ_CNAME_ACTION_IDENTIFIER: self._handle_update_rpz_cname_error,
        }.get(self.api_identifier, self.common_exception)

    def common_exception(self) -> Tuple[type, str]:
        """
        Handles common exceptions that don't have a specific handler.

        If the response status code is 400, 404 or 409, extract API error message.
        Otherwise, it calls the general error handler.
        """
        if self.response is not None and self.response.status_code in (400, 404, 409):
            return self._handle_api_error()
        return self._handle_general_error()

    def _handle_api_error(self) -> Tuple[type, str]:
        """
        Extracts and formats error messages from API responses (400/404/409).
        Returns:
            tuple: (Exception class, error message)
        """
        try:
            error_json = self.response.json()
            # Infoblox error: {"Error": "...", "code": "...", "text": "..."}
            if isinstance(error_json, dict) and "text" in error_json:
                error_msg = error_json["text"]
                return InfobloxException, error_msg
            # fallback: sometimes error info might be in "Error"
            if "Error" in error_json and isinstance(error_json["Error"], str):
                return InfobloxException, error_json["Error"]
        except Exception:
            pass
        # fallback to general error
        return self._handle_general_error()

    def _handle_general_error(self) -> Tuple[type, str]:
        """
        Handles general errors by formatting the error message and returning the appropriate
        exception.

        Returns:
            tuple: A tuple containing the exception class and the formatted error message.
        """
        error_msg = "{error_msg}: {error} - {text}".format(
            error_msg=self.error_msg, error=self.error, text=self.error.response.content
        )

        return InfobloxException, error_msg

    # For sample only, we need to remove this
    def ping(self) -> Tuple[type, str]:
        return self._handle_general_error()

    def _handle_rp_zone_error(self) -> Tuple[type, str]:
        """
        Handle 404,400 errors for invalid reference ID.
        Returns a tuple (ExceptionClass, message) as per project convention.
        """
        response = getattr(self, "response", None)
        if response.status_code in (400, 404):
            return (
                ItemNotFoundException,
                "Response Policy Zone with reference ID `{reference_id}` not found.",
            )

        return self._handle_general_error()

    def _handle_rpz_rule_error(self) -> Tuple[type, str]:
        """
        Handle 404,400 errors for invalid reference ID.
        Returns a tuple (ExceptionClass, message) as per project convention.
        """
        response = getattr(self, "response", None)
        if response.status_code in (400, 404):
            return (
                ItemNotFoundException,
                "RPZ Rule with reference ID `{reference_id}` not found.",
            )

        return self._handle_general_error()

    def _handle_update_rpz_cname_error(self) -> Tuple[type, str]:
        """
        Handle 404,400 errors for invalid reference ID.
        Returns a tuple (ExceptionClass, message) as per project convention.
        """
        response = getattr(self, "response", None)
        exception_class, error_msg = self._handle_api_error()
        if response.status_code in (400, 404):
            if "Invalid reference" in error_msg or "not found" in error_msg:
                return (
                    ItemNotFoundException,
                    "RPZ Rule with reference ID `{reference_id}` not found.",
                )
            return exception_class, error_msg

        return self._handle_general_error()

    def _handle_host_record_error(self) -> Tuple[type, str]:
        """
        Handle 400 errors for invalid input parameters.
        Returns a tuple (ExceptionClass, message) as per project convention.
        """
        response = getattr(self, "response", None)
        _, error_msg = self._handle_api_error()
        if response.status_code == 400:
            return (
                ItemNotFoundException,
                f"Please check the provided parameters. Actual error from Infoblox: {error_msg}",
            )

        return self._handle_general_error()


def parse_extended_attributes(ext_attrs: str) -> Dict[str, str]:
    """
    Helper function to transform the extension attributes.
    The user supplies a string of key/value pairs separated by commas.

    This function parses that string and returns a list of dictionaries
    with "name" and "value" keys.

    Args:
    - `ext_attrs` (`str`): The string of key/value pairs separated by commas.

    Returns:
    - `list[dict]` or `None`: A `list[dict]` representing the extension attributes.
    Returns `None` in case there were no delimiters present. If the attributes
    cannot be parsed, an exception is raised.

    For example:

    ```python
    >>>> parse_extended_attributes("Site=Tel-Aviv")
    [{"Site": "Tel-Aviv"}]

    >>>> parse_extended_attributes("IB Discovery Owned=EMEA,Site=Tel-Aviv")
    [{"*IB Discovery Owned": "EMEA", "*Site": "Tel-Aviv"}]
    ```
    """

    # In case there are no delimiters present in the input
    if "," not in ext_attrs and "=" not in ext_attrs:
        return {}

    ext_attrs = ",".join(string_to_list(ext_attrs))

    parsed_ext_attrs: dict = {}

    attributes = ext_attrs.split(",")

    for ext_attr in attributes:
        try:
            key, value = ext_attr.split("=")
            if key and value:
                parsed_ext_attrs.update({f"*{key.strip()}": value.strip()})
        except ValueError:
            raise ValueError(
                f"Unable to parse provided {ext_attrs=}. Expected format is "
                + "'ExtKey1=ExtVal1,ExtKeyN=ExtValN'"
            )

    return parsed_ext_attrs


def validate_ip_address_objects_params(
    ip_address_objects: Optional[str], name: str
) -> List[Dict[str, Any]]:
    """
    Validate the IP address objects parameter.
    """
    if not ip_address_objects:
        return []

    try:
        ip_address_objects_list = json.loads(ip_address_objects)
        if not isinstance(ip_address_objects_list, list):
            raise ValueError(f"{name} must be a JSON array.")

        for item in ip_address_objects_list:
            if not isinstance(item, dict):
                raise ValueError(f"Each item in {name} must be a JSON object.")

        return ip_address_objects_list
    except Exception as e:
        raise ValueError(f"Invalid {name} format: {str(e)}")


def parse_extended_attributes_to_dict(ext_attrs: str) -> Dict[str, Dict[str, str]]:
    """
    Parses extended attributes from a string to a dictionary format.

    Args:
        ext_attrs (str): The string of key/value pairs separated by commas.

    Returns:
        dict: A dictionary with keys as attribute names and values as dictionaries with "value" key.
    """
    parsed_ext_attrs = parse_extended_attributes(ext_attrs)
    return {key.lstrip("*"): {"value": value} for key, value in parsed_ext_attrs.items()}


def validate_ip_address(ip_address: str, name: str = "IP Address", version: int = None) -> bool:
    """
    Validates if the given string is a valid IPv4 or IPv6 address.

    Args:
        ip_address (str): The IP address to validate.
        name (str): Name of the parameter for error messages.
        version (int, optional): IP version to validate against.
                               4 for IPv4, 6 for IPv6, None for either.

    Returns:
        bool: True if the IP address is valid, False otherwise.
    """
    if ip_address:
        try:
            # If version is specified, validate against that specific version
            if version == 4:
                ipaddress.IPv4Address(ip_address)
            elif version == 6:
                ipaddress.IPv6Address(ip_address)
            else:
                # If no version specified, accept either IPv4 or IPv6
                ipaddress.ip_address(ip_address)
            return True
        except ValueError:
            raise ValueError(f"Invalid IP address format for {name} parameter.")


def validate_network_address(network: Optional[str]) -> bool:
    """
    Validates if the given string is a valid network address (IP with subnet information).
    Supports both IPv4 and IPv6 networks.

    Args:
        network (str): The network address to validate (e.g., "192.168.1.0/24" or "2001:db8::/32").

    Returns:
        bool: True if the network address is valid, False otherwise.
    """
    if network:
        try:
            ipaddress.ip_network(network, strict=False)
            return True
        except ValueError:
            raise ValueError("Invalid network address format.")
