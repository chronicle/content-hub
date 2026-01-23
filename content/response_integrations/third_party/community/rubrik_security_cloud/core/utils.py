from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Type, Union
from urllib.parse import urlparse

from TIPCommon.smp_time import unix_now

from .constants import (
    ADVANCE_IOC_SCAN_ACTION_IDENTIFIER,
    DEFAULT_EXPIRY_SECONDS,
    DEFAULT_SCAN_NAME,
    EXPIRES_IN_KEY,
    GET_CDM_CLUSTER_CONNECTION_STATE_ACTION_IDENTIFIER,
    GET_CDM_CLUSTER_LOCATION_ACTION_IDENTIFIER,
    GET_SONAR_SENSITIVE_HITS_ACTION_IDENTIFIER,
    INTEGRATION_NAME,
    IOC_SCAN_RESULTS_ACTION_IDENTIFIER,
    LIST_EVENTS_ACTION_IDENTIFIER,
    LIST_OBJECT_SNAPSHOTS_ACTION_IDENTIFIER,
    LIST_SONAR_FILE_CONTEXTS_ACTION_IDENTIFIER,
    PING_ACTION_IDENTIFIER,
    TURBO_IOC_SCAN_ACTION_IDENTIFIER,
)
from .rubrik_exceptions import (
    InternalSeverError,
    InvalidIntegerException,
    ItemNotFoundException,
    RubrikException,
)


def extract_domain_from_uri(access_token_uri: str) -> str:
    """
    Extract the domain (netloc) from the access_token_uri.

    Args:
        access_token_uri (str): The access token URI from service account JSON

    Returns:
        str: The domain part of the URI (e.g., "rubrik-tme-rdp.my.rubrik.com")

    Raises:
        ValueError: If the URI is invalid or domain cannot be extracted
    """
    if not access_token_uri or not access_token_uri.strip():
        raise ValueError("access_token_uri not present in the Service Account JSON.")

    parsed_uri = urlparse(access_token_uri.strip())
    domain = parsed_uri.netloc

    if not domain:
        raise ValueError(
            f"Could not extract Rubrik Account domain from access_token_uri: {access_token_uri}"
        )

    return domain


def get_integration_params(siemplify: Any) -> Tuple[str, bool]:
    """
    Retrieve the integration parameters from Siemplify configuration.

    Args:
        siemplify (SiemplifyAction): SiemplifyAction instance

    Returns:
        tuple: A tuple containing the integration parameters.
    """
    service_account_json = siemplify.extract_configuration_param(
        INTEGRATION_NAME, "Service Account JSON", input_type=str, is_mandatory=False
    )

    verify_ssl = siemplify.extract_configuration_param(
        INTEGRATION_NAME, "Verify SSL", input_type=bool, is_mandatory=True
    )

    return service_account_json, verify_ssl


def validate_required_string(value: Optional[str], param_name: str) -> str:
    """
    Validates that a string parameter is not empty.

    Args:
        value (str, optional): The value to validate
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
    is_mandatory: bool = False,
) -> Optional[int]:
    """
    Validates if the given value is an integer and meets the specified requirements.

    Args:
        value (int|str|None): The value to be validated.
        param_name (str): The name of the parameter for error messages.
        zero_allowed (bool, optional): If True, zero is a valid integer. Defaults to False.
        allow_negative (bool, optional): If True, negative integers are allowed.
            Defaults to False.
        max_value (int, optional): If set, value must be less than or equal to
            max_value.
        is_mandatory (bool, optional): If True, raises error when value is None
            or empty. Defaults to False.

    Raises:
        ValueError: If is_mandatory is True and value is None or empty.
        InvalidIntegerException: If the value is not a valid integer or does not meet the rules.

    Returns:
        Optional[int]: The validated integer value, or None if value is empty and not mandatory.
    """
    # Handle None or empty string - use default or return None
    is_empty = value is None or (isinstance(value, str) and not value.strip())
    if is_empty:
        return (
            None
            if not default_value
            else validate_integer_param(
                default_value, param_name, None, zero_allowed, allow_negative, max_value
            )
        )

    # Convert to integer - handle both int and string types
    try:
        int_value = value if isinstance(value, int) else int(value.strip())
    except (ValueError, TypeError, AttributeError):
        raise InvalidIntegerException(f"{param_name} must be an integer.")

    # Validate all constraints
    if int_value < 0 and not allow_negative:
        raise InvalidIntegerException(f"{param_name} must be a non-negative integer.")
    if int_value == 0 and not zero_allowed:
        raise InvalidIntegerException(f"{param_name} must be greater than zero.")
    if max_value is not None and int_value > max_value:
        raise InvalidIntegerException(f"{param_name} must be less than or equal to {max_value}.")

    return int_value


def is_valid_date(date_str: str):
    """
    Return True if date_str matches YYYY-MM-DD, YYYY-MM-DDTHH:MM:SSZ,
    or YYYY-MM-DDTHH:MM:SS.fffZ.
    """
    if date_str and date_str.strip():
        date_str = date_str.strip()
    else:
        return None
    formats = [
        "%Y-%m-%d",  # e.g. 2025-10-12
        "%Y-%m-%dT%H:%M:%S.%fZ",  # e.g. 2025-10-12T06:30:00.000Z
        "%Y-%m-%dT%H:%M:%SZ",  # e.g. 2011-11-11T23:59:59Z
    ]
    for fmt in formats:
        try:
            datetime.strptime(date_str, fmt)
            return date_str
        except ValueError:
            continue
    raise ValueError(
        "The Date needs to be in one of the following formats: "
        "YYYY-MM-DD, YYYY-MM-DDTHH:MM:SSZ, or YYYY-MM-DDTHH:MM:SS.fffZ"
    )


def string_to_list(
    items_str: Optional[str], param_name: str = "parameter", is_mandatory: bool = False
) -> List[str]:
    """
    Convert a comma-separated string to a list of strings.

    Args:
        items_str (str, optional): Comma-separated string
        param_name (str): Parameter name for error messages
        is_mandatory (bool): If True, raises error when empty

    Returns:
        List[str]: List of trimmed strings

    Raises:
        ValueError: If is_mandatory is True and items_str is empty
    """
    items_str = items_str.strip() if items_str else None
    if not items_str:
        if is_mandatory:
            raise ValueError(f"{param_name} is required")
        return []
    item_list = [item.strip() for item in items_str.split(",") if item.strip()]
    if not item_list and is_mandatory:
        raise ValueError(f"{param_name} is required")
    return item_list


def validate_json(json_str: str, param_name: str, is_mandatory: bool = False) -> Dict[str, Any]:
    """
    Validate and parse a JSON string.

    Args:
        json_str (str): The JSON string to validate
        param_name (str): Parameter name for error messages

    Returns:
        Dict[str, Any]: Parsed JSON object

    Raises:
        ValueError: If the JSON is invalid
    """
    if json_str is None or not json_str.strip():
        if is_mandatory:
            raise ValueError(f"{param_name} is required")
        return None

    json_str = json_str.strip()
    if not json_str:
        if is_mandatory:
            raise ValueError(f"{param_name} is required")
        return None

    try:
        parsed = json.loads(json_str)
        if not isinstance(parsed, dict):
            raise ValueError(f"{param_name} must be a valid JSON object.")
        return parsed
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {param_name}: {str(e)}")


def generate_scan_name(scan_name: str) -> str:
    """Generate or validate a scan name for threat hunts.

    Args:
        scan_name: User-provided scan name or empty string.

    Returns:
        str: Either the provided scan name or a generated name with current date/time.
    """
    if scan_name and scan_name.strip():
        return scan_name.strip()
    now = datetime.now()
    return DEFAULT_SCAN_NAME.format(
        DATE=now.strftime("%Y-%m-%d"),
        TIME=now.strftime("%H:%M:%S"),
    )


def generate_encryption_key(client_id: str, account_domain: str) -> str:
    """Generate an encryption key from existing settings.

    Args:
        client_id: OAuth client ID.
        account_domain: Rubrik account domain.

    Returns:
        str: SHA-256 hash hex string used for token encryption.
    """
    unique_string = f"{client_id}:{account_domain}"
    # Create a SHA-256 hash to ensure consistent length and format
    return hashlib.sha256(unique_string.encode()).hexdigest()


def compute_expiry(response: Dict[str, Any]) -> int:
    """Calculate token expiration time from OAuth response.

    Args:
        response: OAuth token response dictionary containing 'expires_in' field.

    Returns:
        int: Expiration time in milliseconds since epoch.
    """
    now_ms = unix_now()
    expires_in = response.get(EXPIRES_IN_KEY)
    if expires_in is not None:
        try:
            expires_in_sec = int(expires_in)
            return now_ms + (expires_in_sec * 1000)

        except (TypeError, ValueError):
            pass
    return now_ms + (DEFAULT_EXPIRY_SECONDS * 1000)


class HandleExceptions(object):
    """
    Handle and process exceptions from Rubrik API calls with action-specific logic.
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
            error_msg (str, optional): A default error message. Defaults to "An error occurred".
        """
        self.action_identifier = action_identifier
        self.error = error
        self.response = response
        self.error_msg = error_msg

    def do_process(self) -> None:
        """
        Processes the error by calling the appropriate handler based on the action identifier.
        Handles both HTTP-level errors and GraphQL errors in responses.

        Raises:
            Exceptions based on the error type (RubrikException, GraphQLQueryException, etc.)
        """
        if self.response.status_code >= 500:
            error_msg = f"Rubrik server error: Status code {self.response.status_code}"
            if hasattr(self.response, "text") and self.response.text:
                error_msg += f" - {self.response.text[:200]}"
            raise InternalSeverError(error_msg)

        try:
            handler = self.get_handler()
            exception_class, error_msg = handler()

            if hasattr(self, "error") and self.error:
                error_msg = f"{error_msg} (Original error: {str(self.error)})"

        except RubrikException:
            exception_class, error_msg = self.common_exception()

        raise exception_class(error_msg)

    def get_handler(self) -> callable[[], Tuple[Type[Exception], str]]:
        """
        Retrieves the appropriate handler function based on the api_name.

        Returns:
            function: The handler function corresponding to the api_name.
        """
        return {
            PING_ACTION_IDENTIFIER: self.ping,
            TURBO_IOC_SCAN_ACTION_IDENTIFIER: self._handle_turbo_ioc_scan,
            ADVANCE_IOC_SCAN_ACTION_IDENTIFIER: self._handle_advance_ioc_scan,
            IOC_SCAN_RESULTS_ACTION_IDENTIFIER: self._handle_ioc_scan_results,
            LIST_OBJECT_SNAPSHOTS_ACTION_IDENTIFIER: self._handle_list_object_snapshots,
            LIST_SONAR_FILE_CONTEXTS_ACTION_IDENTIFIER: self._handle_list_sonar_file_contexts,
            LIST_EVENTS_ACTION_IDENTIFIER: self._handle_list_events,
            GET_SONAR_SENSITIVE_HITS_ACTION_IDENTIFIER: self._handle_get_sonar_sensitive_hits,
            GET_CDM_CLUSTER_CONNECTION_STATE_ACTION_IDENTIFIER: (
                self._handle_cdm_cluster_connection_state
            ),
            GET_CDM_CLUSTER_LOCATION_ACTION_IDENTIFIER: self._handle_cdm_cluster_location,
        }.get(self.action_identifier, self.common_exception)

    def common_exception(self) -> Tuple[Type[Exception], str]:
        """
        Handles common exceptions that don't have a specific handler.

        If the response status code is 400, 404 or 409, extract API error message.
        Otherwise, it calls the general error handler.
        """
        if self.response is not None and self.response.status_code in (
            400,
            404,
            409,
            403,
        ):
            return self._handle_api_error()
        return self._handle_general_error()

    def _extract_error_codes(self, errors: List[Dict[str, Any]]) -> List[str]:
        """
        Extract error codes from GraphQL errors.

        Args:
            errors: List of GraphQL error objects

        Returns:
            List of error code strings
        """
        error_codes = []
        for error in errors:
            if (
                "extensions" in error
                and isinstance(error.get("extensions"), dict)
                and "code" in error["extensions"]
            ):
                error_codes.append(str(error["extensions"]["code"]))
        return error_codes

    def _format_error_message(self, error_messages: List[str], error_codes: List[str]) -> str:
        """
        Format error messages with optional error codes.

        Args:
            error_messages: List of error message strings
            error_codes: List of error code strings

        Returns:
            Formatted error message string
        """
        error_message = "; ".join(filter(None, error_messages))
        if error_codes:
            error_message = f"[Error codes: {', '.join(error_codes)}] {error_message}"
        return error_message

    def _process_graphql_errors(self, errors: List[Dict[str, Any]]) -> Optional[Tuple[type, str]]:
        """
        Process GraphQL errors array and return formatted error tuple.

        Args:
            errors: List of GraphQL error objects

        Returns:
            Tuple of (exception_class, error_message) or None
        """
        if not errors:
            return None

        # Extract error messages
        error_messages = [err.get("message", "") for err in errors if "message" in err]

        if not error_messages:
            return None

        # Extract error codes
        error_codes = self._extract_error_codes(errors)

        # Format and return error
        error_message = self._format_error_message(error_messages, error_codes)
        return (RubrikException, error_message)

    def _extract_graphql_errors(
        self, response_json: Dict[str, Any]
    ) -> Tuple[bool, Optional[Tuple[type, str]]]:
        """
        Extract error messages and error codes from GraphQL response JSON.

        Args:
            response_json (dict): The GraphQL response JSON that may contain errors

        Returns:
            tuple: (has_errors, error_tuple) where has_errors is a boolean and error_tuple
                  is (exception_class, error_message) if has_errors is True, otherwise None
        """
        if not isinstance(response_json, dict):
            return False, None

        # Check for GraphQL errors array
        if "errors" in response_json and isinstance(response_json["errors"], list):
            error_tuple = self._process_graphql_errors(response_json["errors"])
            if error_tuple:
                return True, error_tuple

        # Check for direct message field
        if "message" in response_json:
            return True, (RubrikException, response_json["message"])

        return False, None

    def _handle_api_error(self) -> Tuple[Type[Exception], str]:
        """
        Extracts and formats error messages from API responses (400/404/409).
        Handles both standard REST API errors and GraphQL-specific errors.

        Returns:
            tuple: (Exception class, error message)
        """
        try:
            error_json = self.response.json()

            # First check for GraphQL errors using our helper method
            has_errors, error_tuple = self._extract_graphql_errors(error_json)
            if has_errors:
                # We found GraphQL errors, return the error tuple
                return error_tuple

            # If no GraphQL-specific errors, check for standard REST error patterns
            if "error" in error_json:
                # Standard REST API error
                if isinstance(error_json["error"], str):
                    return RubrikException, error_json["error"]
                elif isinstance(error_json["error"], dict) and "message" in error_json["error"]:
                    return RubrikException, error_json["error"]["message"]

        except Exception:
            # If we can't parse the JSON or any other error occurs, fall back to general error
            pass

        # fallback to general error handling
        return self._handle_general_error()

    def _handle_general_error(self) -> Tuple[Type[Exception], str]:
        """
        Handles general errors by formatting the error message and returning the appropriate
        exception.

        Returns:
            tuple: A tuple containing the exception class and the formatted error message.
        """
        error_msg = "{error_msg}: {error} - {text}".format(
            error_msg=self.error_msg,
            error=self.error,
            text=self.error.response.content,
        )

        return RubrikException, error_msg

    def ping(self) -> Tuple[Type[Exception], str]:
        """
        Handler for ping action errors.
        """
        return self._handle_general_error()

    def _handle_turbo_ioc_scan(self) -> Tuple[Type[Exception], str]:
        """
        Handle errors for Turbo IOC Scan action.
        Returns a tuple (ExceptionClass, message) as per project convention.
        """
        status_code = self.response.status_code

        if status_code == 400:
            try:
                res = self.response.json()
                has_errors, error_tuple = self._extract_graphql_errors(res)
                if has_errors:
                    return error_tuple
            except Exception:
                pass

        return self.common_exception()

    def _handle_advance_ioc_scan(self) -> Tuple[Type[Exception], str]:
        """
        Handle errors for Advance IOC Scan action.
        Returns a tuple (ExceptionClass, message) as per project convention.
        """
        status_code = self.response.status_code

        if status_code == 400:
            try:
                res = self.response.json()
                has_errors, error_tuple = self._extract_graphql_errors(res)
                if has_errors:
                    return error_tuple
            except Exception:
                pass

        return self.common_exception()

    def _handle_ioc_scan_results(self) -> Tuple[Type[Exception], str]:
        """
        Handle errors for IOC Scan Results action.
        Returns a tuple (ExceptionClass, message) as per project convention.
        """
        status_code = self.response.status_code

        if status_code == 404:
            try:
                res = self.response.json()
                has_errors, error_tuple = self._extract_graphql_errors(res)
                if has_errors:
                    # Use ItemNotFoundException instead of the default RubrikException
                    return ItemNotFoundException, error_tuple[1]
                return ItemNotFoundException, "Hunt ID does not exist."
            except Exception:
                pass

        # For other status codes, use the common exception handler
        if status_code == 400:
            try:
                res = self.response.json()
                has_errors, error_tuple = self._extract_graphql_errors(res)
                if has_errors:
                    return error_tuple
            except Exception:
                pass

        return self.common_exception()

    def _handle_list_object_snapshots(self) -> Tuple[Type[Exception], str]:
        """
        Handle errors for List Object Snapshots action.
        Returns a tuple (ExceptionClass, message) as per project convention.
        """
        status_code = self.response.status_code

        if status_code == 404:
            return RubrikException, "Object ID does not exist or no snapshots found."

        if status_code == 400:
            try:
                res = self.response.json()
                has_errors, error_tuple = self._extract_graphql_errors(res)
                if has_errors:
                    return error_tuple
            except Exception:
                pass

        return self.common_exception()

    def _handle_list_sonar_file_contexts(self) -> Tuple[Type[Exception], str]:
        """
        Handle errors for List Sonar File Contexts action.
        Returns a tuple (ExceptionClass, message) as per project convention.
        """
        status_code = self.response.status_code

        if status_code == 404:
            return RubrikException, "Object ID or Snapshot ID does not exist."

        if status_code == 400:
            try:
                res = self.response.json()
                has_errors, error_tuple = self._extract_graphql_errors(res)
                if has_errors:
                    return error_tuple
            except Exception:
                pass

        return self.common_exception()

    def _handle_list_events(self) -> Tuple[Type[Exception], str]:
        """
        Handle errors for List Events action.
        Returns a tuple (ExceptionClass, message) as per project convention.
        """
        status_code = self.response.status_code

        if status_code == 404:
            return RubrikException, "No events found for the Object ID."

        if status_code == 400:
            try:
                res = self.response.json()
                has_errors, error_tuple = self._extract_graphql_errors(res)
                if has_errors:
                    return error_tuple
            except Exception:
                pass

        return self.common_exception()

    def _handle_get_sonar_sensitive_hits(self) -> Tuple[Type[Exception], str]:
        """
        Handle errors for Get Sonar Sensitive HITS action.
        Returns a tuple (ExceptionClass, message) as per project convention.
        """
        status_code = self.response.status_code

        if status_code == 404:
            return RubrikException, "No sensitive HITS found for the Object ID."

        if status_code == 400:
            try:
                res = self.response.json()
                has_errors, error_tuple = self._extract_graphql_errors(res)
                if has_errors:
                    return error_tuple
            except Exception:
                pass

        return self.common_exception()

    def _handle_cdm_cluster_connection_state(self) -> Tuple[Type[Exception], str]:
        """
        Handle errors for Get CDM Cluster Connection State action.
        Returns a tuple (ExceptionClass, message) as per project convention.
        """
        status_code = self.response.status_code

        if status_code == 404:
            return RubrikException, "Cluster not found."

        if status_code == 400:
            try:
                res = self.response.json()
                has_errors, error_tuple = self._extract_graphql_errors(res)
                if has_errors:
                    return error_tuple
            except Exception:
                pass

        return self.common_exception()

    def _handle_cdm_cluster_location(self) -> Tuple[Type[Exception], str]:
        """
        Handle errors for Get CDM Cluster Location action.
        Returns a tuple (ExceptionClass, message) as per project convention.
        """
        status_code = self.response.status_code

        if status_code == 404:
            return RubrikException, "Cluster not found."

        if status_code == 400:
            try:
                res = self.response.json()
                has_errors, error_tuple = self._extract_graphql_errors(res)
                if has_errors:
                    return error_tuple
            except Exception:
                pass

        return self.common_exception()
