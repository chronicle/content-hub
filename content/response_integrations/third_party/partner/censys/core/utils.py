from __future__ import annotations

import ipaddress
import re
from datetime import datetime
from typing import Any, List, Optional, Tuple, Union

from soar_sdk.SiemplifyDataModel import EntityTypes

from .censys_exceptions import CensysException, InternalServerError, InvalidIntegerException
from .constants import ENRICHMENT_PREFIX, INTEGRATION_NAME, PING_ACTION_IDENTIFIER


def get_integration_params(siemplify: Any) -> Tuple[str, str, bool]:
    """
    Retrieve the integration parameters from Siemplify configuration.

    Args:
        siemplify (SiemplifyAction): SiemplifyAction instance

    Returns:
        tuple: A tuple containing the integration parameters (api_key,
        organization_id, verify_ssl).
    """
    api_key = siemplify.extract_configuration_param(
        INTEGRATION_NAME, "API Key", input_type=str, is_mandatory=True
    ).strip()

    organization_id = siemplify.extract_configuration_param(
        INTEGRATION_NAME, "Organization Id", input_type=str, is_mandatory=True
    ).strip()

    verify_ssl = siemplify.extract_configuration_param(
        INTEGRATION_NAME, "Verify SSL", input_type=bool, is_mandatory=True
    )

    return api_key, organization_id, verify_ssl


def validate_required_string(value: str, param_name: str) -> str:
    """
    Validates that a string parameter is not empty.

    Args:
        value (str): The value to validate
        param_name (str): The name of the parameter for error messages

    Returns:
        str: The validated string value

    Raises:
        ValueError: If the value is None or empty
    """
    if not value or not value.strip():
        raise ValueError(f"{param_name} must be a non-empty string.")
    return value.strip()


def validate_integer_param(
    value: Union[int, str, None],
    param_name: str,
    default_value: Optional[str] = None,
    zero_allowed: bool = False,
    allow_negative: bool = False,
    max_value: Optional[int] = None,
    min_value: Optional[int] = None,
) -> Optional[int]:
    """
    Validates if the given value is an integer and meets the specified requirements.

    Args:
        value: The value to be validated
        param_name: The name of the parameter for error messages
        default_value: Default value to use if value is empty
        zero_allowed: If True, zero is a valid integer
        allow_negative: If True, negative integers are allowed
        max_value: If set, value must be less than or equal to max_value
        min_value: If set, value must be greater than or equal to min_value

    Returns:
        Optional[int]: The validated integer value, or None if value is empty and not mandatory

    Raises:
        InvalidIntegerException: If the value is not a valid integer or does not meet the rules
    """
    is_empty = value is None or (isinstance(value, str) and not value.strip())
    if is_empty:
        return (
            None
            if not default_value
            else validate_integer_param(
                default_value, param_name, None, zero_allowed, allow_negative, max_value, min_value
            )
        )

    try:
        int_value = value if isinstance(value, int) else int(value.strip())
    except (ValueError, TypeError, AttributeError):
        raise InvalidIntegerException(f"{param_name} must be an integer.")

    if int_value < 0 and not allow_negative:
        raise InvalidIntegerException(f"{param_name} must be a non-negative integer.")
    if int_value == 0 and not zero_allowed:
        raise InvalidIntegerException(f"{param_name} must be greater than zero.")
    if max_value is not None and int_value > max_value:
        raise InvalidIntegerException(f"{param_name} must be less than or equal to {max_value}.")
    if min_value is not None and int_value < min_value:
        raise InvalidIntegerException(f"{param_name} must be greater than or equal to {min_value}.")

    return int_value


def validate_ip_address(ip_string: str, param_name: str = "IP Address") -> str:
    """
    Validate if a string is a valid IPv4 or IPv6 address.

    Args:
        ip_string (str): The IP address string to validate
        param_name (str): Name of the parameter for error messages

    Returns:
        str: The validated and stripped IP address string

    Raises:
        ValueError: If the IP address is invalid or empty

    Examples:
        >>> validate_ip_address("192.168.1.1")
        '192.168.1.1'
        >>> validate_ip_address("2001:db8::1")
        '2001:db8::1'
        >>> validate_ip_address("invalid")
        ValueError: Invalid IP Address: invalid
    """
    if not ip_string or not ip_string.strip():
        raise ValueError(f"{param_name} must be a non-empty string.")

    ip_string = ip_string.strip()

    try:
        ipaddress.ip_address(ip_string)
        return ip_string
    except (ValueError, TypeError):
        raise ValueError(f"Invalid {param_name}: {ip_string}")


def filter_valid_ips(ip_list: List[str]) -> Tuple[List[str], List[str]]:
    """
    Filter IP addresses into valid and invalid lists.

    Args:
        ip_list (List[str]): List of IP address strings to validate

    Returns:
        Tuple[List[str], List[str]]: Tuple of (valid_ips, invalid_ips)
    """
    valid_ips = []
    invalid_ips = []

    for ip in ip_list:
        try:
            validated_ip = validate_ip_address(ip)
            valid_ips.append(validated_ip)
        except ValueError:
            invalid_ips.append(ip)

    return valid_ips, invalid_ips


def validate_rfc3339_timestamp(timestamp_str: str, param_name: str = "At Time") -> str:
    """
    Validates if a string is a valid RFC3339 datetime format.

    Args:
        timestamp_str: The timestamp string to validate
        param_name: Name of the parameter for error messages

    Raises:
        ValueError: If the timestamp_str is not in valid RFC3339 format

    Examples:
        Valid formats:
        - 2024-01-15T00:00:00Z
        - 2024-01-15T14:30:00Z
        - 2024-01-15T14:30:00.123Z
        - 2024-01-15T14:30:00+05:30
        - 2024-01-15T14:30:00-07:00
    """
    timestamp_str = timestamp_str.strip()

    if not timestamp_str:
        raise ValueError(
            f"{param_name} must be a non-empty string in RFC3339 format. "
            "Example: 2024-01-15T00:00:00Z"
        )

    rfc3339_pattern = re.compile(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
    )

    if not rfc3339_pattern.match(timestamp_str):
        raise ValueError(
            f"{param_name} must be a valid RFC3339 datetime string: '{timestamp_str}'. "
            "Expected format: YYYY-MM-DDTHH:MM:SSZ or "
            "YYYY-MM-DDTHH:MM:SS±HH:MM. "
            "Example: 2024-01-15T00:00:00Z"
        )

    try:
        if timestamp_str.endswith("Z"):
            datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")
        elif "." in timestamp_str and timestamp_str[-1] == "Z":
            base_timestamp = timestamp_str.split(".")[0] + "Z"
            datetime.strptime(base_timestamp, "%Y-%m-%dT%H:%M:%SZ")
        elif "+" in timestamp_str or timestamp_str.count("-") > 2:
            base_timestamp = timestamp_str[:19]
            datetime.strptime(base_timestamp, "%Y-%m-%dT%H:%M:%S")
        else:
            raise ValueError("Invalid timestamp_str format")
    except ValueError as e:
        raise ValueError(f"Invalid date/time values in timestamp_str '{timestamp_str}': {str(e)}")

    return timestamp_str


def validate_and_parse_ports(ports_string: str) -> List[int]:
    """
    Validate and parse comma-separated port numbers.

    Args:
        ports_string (str): Comma-separated port numbers

    Returns:
        List[int]: List of valid port numbers

    Raises:
        ValueError: If any port is invalid or out of range (1-65535)

    Examples:
        Valid inputs:
        - "80,443" -> [80, 443]
        - "80, 443, 8080" -> [80, 443, 8080]
        - "8080" -> [8080]
    """
    if not ports_string or not isinstance(ports_string, str):
        raise ValueError("Port parameter must be a non-empty string. Example: 80,443")

    ports_string = ports_string.strip()

    if not ports_string:
        raise ValueError("Port parameter must be a non-empty string. Example: 80,443")

    port_list = []
    port_strings = [p.strip() for p in ports_string.split(",")]

    for port_str in port_strings:
        if not port_str:
            continue

        try:
            port = int(port_str)
            if port < 1 or port > 65535:
                raise ValueError(f"Port {port} is out of valid range (1-65535)")
            port_list.append(port)
        except ValueError as e:
            if "invalid literal" in str(e):
                raise ValueError(
                    f"Invalid port value '{port_str}'. Port must be a number between 1 and 65535"
                )
            raise

    if not port_list:
        raise ValueError(
            "No valid ports found in input. "
            "Please provide comma-separated port numbers (e.g., 80,443)"
        )

    return port_list


def validate_domain(domain: str) -> bool:
    """
    Validate domain name format.

    Args:
        domain: Domain name to validate

    Returns:
        bool: True if domain is valid, False otherwise

    Note:
        Leading/trailing dots are rejected as they represent different
        resources in Censys (.example.com vs example.com are same).
        Validation catches obvious errors that API will reject.
    """
    if not domain or not isinstance(domain, str):
        return False

    domain = domain.strip()

    if not domain or len(domain) > 253:
        return False

    if domain.endswith("."):
        return False

    if " " in domain:
        return False

    if ".." in domain:
        return False

    if not re.match(r"^[a-zA-Z0-9.-]+$", domain):
        return False

    if "." not in domain:
        return False

    return True


def validate_certificate_id(cert_id: str) -> bool:
    """
    Validate certificate ID (SHA-256 fingerprint) format.

    Args:
        cert_id: Certificate SHA-256 fingerprint to validate

    Returns:
        bool: True if certificate ID is valid, False otherwise

    Note:
        Certificate IDs must be exactly 64 hexadecimal characters
        (SHA-256 hash format). Case-insensitive validation.
    """
    if not cert_id or not isinstance(cert_id, str):
        return False

    cert_id = cert_id.strip()

    if len(cert_id) != 64:
        return False

    if not re.match(r"^[a-fA-F0-9]{64}$", cert_id):
        return False

    return True


def filter_valid_certificate_ids(cert_ids: List[str]) -> Tuple[List[str], List[str]]:
    """
    Filter and validate certificate IDs.

    Args:
        cert_ids: List of certificate SHA-256 fingerprints

    Returns:
        Tuple of (valid_cert_ids, invalid_cert_ids)
    """
    valid_certs = []
    invalid_certs = []

    for cert_id in cert_ids:
        if validate_certificate_id(cert_id):
            valid_certs.append(cert_id)
        else:
            invalid_certs.append(cert_id)

    return valid_certs, invalid_certs


def validate_web_property_entities(entities: List, siemplify: Any) -> Tuple[List, List[str]]:
    """
    Validate entities for web properties (IPs and domains).

    Args:
        entities: List of entities to validate
        siemplify: SiemplifyAction instance for logging

    Returns:
        Tuple of (valid_entities, invalid_entity_identifiers)
    """
    valid_entities = []
    invalid_identifiers = []

    for entity in entities:
        identifier = entity.identifier
        entity_type = entity.entity_type

        is_valid = False

        if entity_type == EntityTypes.ADDRESS:
            try:
                ipaddress.ip_address(identifier)
                is_valid = True
            except ValueError:
                siemplify.LOGGER.info(f"Invalid IP address format: {identifier}")
                invalid_identifiers.append(identifier)

        elif entity_type == EntityTypes.DOMAIN:
            if validate_domain(identifier):
                is_valid = True
            else:
                siemplify.LOGGER.info(f"Invalid domain format: {identifier}")
                invalid_identifiers.append(identifier)
        else:
            siemplify.LOGGER.info(f"Unsupported entity type {entity_type}: {identifier}")
            invalid_identifiers.append(identifier)

        if is_valid:
            valid_entities.append(entity)

    return valid_entities, invalid_identifiers


def get_ip_entities(siemplify: Any) -> List:
    """
    Get IP ADDRESS type entities from scope.

    Args:
        siemplify: SiemplifyAction instance

    Returns:
        list: List of IP address entities
    """
    return [
        entity for entity in siemplify.target_entities if entity.entity_type == EntityTypes.ADDRESS
    ]


def get_web_property_entities(siemplify: Any) -> List:
    """
    Get ADDRESS and DOMAIN type entities from scope.

    Args:
        siemplify: SiemplifyAction instance

    Returns:
        list: List of ADDRESS and DOMAIN entities
    """
    return [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in [EntityTypes.ADDRESS, EntityTypes.DOMAIN]
    ]


def get_filehash_entities(siemplify: Any) -> List:
    """
    Get FILEHASH type entities from scope.

    Args:
        siemplify: SiemplifyAction instance

    Returns:
        list: List of FILEHASH entities
    """
    return [
        entity for entity in siemplify.target_entities if entity.entity_type == EntityTypes.FILEHASH
    ]


def remove_ip_enrichment(entity) -> None:
    """
    Clear old Censys IP enrichment data from entity by setting values to "-".
    Preserves web property enrichment (Censys_{port}_*) keys.

    Args:
        entity: Entity object to clean
    """
    if not hasattr(entity, "additional_properties"):
        return

    # Clear only IP enrichment keys (not port-prefixed web keys)
    # IP keys: Censys_service_count, Censys_ports, etc.
    # Web keys: Censys_80_*, Censys_443_*, etc. (preserved)
    for key in entity.additional_properties.keys():
        if key.startswith(ENRICHMENT_PREFIX):
            # Check if it's NOT a web property key (port-prefixed)
            parts = key.split("_", 2)
            if len(parts) >= 2 and parts[1].isdigit():
                # This is a web property key like Censys_80_web_hostname
                continue
            # This is an IP enrichment key - set to "-"
            entity.additional_properties[key] = "-"


def remove_web_property_enrichment(entity, port: int) -> None:
    """
    Clear old Censys web property enrichment for specific port by setting values to "-".
    Preserves IP enrichment and other port enrichments.

    Args:
        entity: Entity object to clean
        port: Port number to clear enrichment for
    """
    if not hasattr(entity, "additional_properties"):
        return

    # Clear only web property keys for this specific port
    # Example: Censys_80_web_hostname, Censys_443_endpoint_type
    port_prefix = f"{ENRICHMENT_PREFIX}{port}_"
    for key in entity.additional_properties.keys():
        if key.startswith(port_prefix):
            entity.additional_properties[key] = "-"


def remove_certificate_enrichment(entity) -> None:
    """
    Clear old Censys certificate enrichment data from entity by setting values to "-".
    Certificates enrich FileHash entities only.

    Args:
        entity: Entity object to clean
    """
    if not hasattr(entity, "additional_properties"):
        return

    # Clear all Censys enrichment keys for certificates
    for key in entity.additional_properties.keys():
        if key.startswith(ENRICHMENT_PREFIX):
            entity.additional_properties[key] = "-"


class HandleExceptions(object):
    """
    Handle and process exceptions from Censys API calls with action-specific logic.
    """

    def __init__(
        self,
        action_identifier: str,
        error: Exception,
        response: Any,
        error_msg: str = "An error occurred",
    ) -> None:
        """
        Initializes the HandleExceptions class.

        Args:
            action_identifier (str): Action Identifier.
            error (Exception): The error that occurred.
            response (Any): The response object.
            error_msg (str, optional): A default error message. Defaults to "An error occurred".
        """
        self.action_identifier = action_identifier
        self.error = error
        self.response = response
        self.error_msg = error_msg

    def do_process(self) -> None:
        """
        Processes the error by calling the appropriate handler based on the action identifier.

        Raises:
            Exceptions based on the error type (CensysException, etc.)
        """
        if self.response.status_code >= 500:
            raise InternalServerError(
                "It seems like the Censys server is experiencing some issues, "
                + f"Status: {self.response.status_code}"
            )

        try:
            handler = self.get_handler()
            _exception, _error_msg = handler()
        except CensysException:
            _exception, _error_msg = self.common_exception()

        raise _exception(_error_msg)

    def get_handler(self) -> callable:
        """
        Retrieves the appropriate handler function based on the action_identifier.

        Returns:
            function: The handler function corresponding to the action_identifier.
        """
        return {
            PING_ACTION_IDENTIFIER: self.ping,
        }.get(self.action_identifier, self.common_exception)

    def common_exception(self) -> Tuple[type, str]:
        """
        Handles common exceptions that don't have a specific handler.

        If the response status code is 400, 401, 403, 404, 409, or 422, extract API error message.
        Otherwise, it calls the general error handler.
        """
        if self.response is not None and self.response.status_code in (
            400,
            401,
            403,
            404,
            409,
            422,
        ):
            return self._handle_api_error()
        return self._handle_general_error()

    def _handle_api_error(self) -> Tuple[type, str]:
        """
        Extracts and formats error messages from API responses.
        Handles three error formats:
        1. 401 format: {"error": {"code": 401, "message": "...",
        "reason": "...", "status": "..."}}
        2. 403/400/422 format: {"detail": "...", "errors": [...],
        "status": 400, "title": "...", "type": "..."}
        3. 422 format: {"title": "...", "status": 422, "detail": "...", "errors":
        [{"message": "..."}]}

        Returns:
            tuple: (Exception class, error message)
        """
        try:
            error_json = self.response.json()
            if isinstance(error_json, dict):
                # Format 1: 401 error with nested error object
                if "error" in error_json:
                    error_obj = error_json["error"]
                    if isinstance(error_obj, dict):
                        # Try to get message and reason
                        message = error_obj.get("message", "")
                        reason = error_obj.get("reason", "")
                        if message and reason:
                            return CensysException, f"{message}: {reason}"
                        elif message:
                            return CensysException, message
                    elif isinstance(error_obj, str):
                        return CensysException, error_obj

                # Format 2 & 3: 403/400/422 error with detail and errors array
                if "detail" in error_json:
                    detail = error_json["detail"]
                    errors = error_json.get("errors", [])

                    # Build error message from errors array
                    if errors and isinstance(errors, list):
                        error_messages = []
                        for err in errors[:3]:  # Limit to first 3 errors
                            if isinstance(err, dict):
                                err_msg = err.get("message", "")
                                err_loc = err.get("location", "")
                                if err_msg:
                                    if err_loc:
                                        error_messages.append(f"{err_loc}: {err_msg}")
                                    else:
                                        error_messages.append(err_msg)

                        # If we have error messages, use them; otherwise use detail
                        if error_messages:
                            return CensysException, " | ".join(error_messages)

                    # If no errors array or empty, return detail
                    return CensysException, detail

                # Fallback: check for direct message field
                if "message" in error_json:
                    return CensysException, error_json["message"]

        except Exception:
            pass
        return self._handle_general_error()

    def _handle_general_error(self) -> Tuple[type, str]:
        """
        Handles general errors by formatting the error message and returning the appropriate
        exception.

        Returns:
            tuple: A tuple containing the exception class and the formatted error message.
        """
        error_msg = "{error_msg}: {error} - {text}".format(
            error_msg=self.error_msg, error=self.error, text=self.response.content
        )

        return CensysException, error_msg

    def ping(self) -> Tuple[type, str]:
        """Handle ping action errors."""
        return self._handle_general_error()
