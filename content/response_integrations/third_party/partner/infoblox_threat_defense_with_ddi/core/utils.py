from __future__ import annotations
import json
import re

from .InfobloxExceptions import (
    InfobloxException,
    InvalidIntegerException,
    ItemNotFoundException,
    InternalSeverError,
)
from .constants import (
    INTEGRATION_NAME,
    MAX_JSON_CHARS,
    PING_ACTION_IDENTIFIER,
    GET_SOC_INSIGHTS_COMMENTS_ACTION_IDENTIFIER,
    GET_SOC_INSIGHTS_INDICATORS_ACTION_IDENTIFIER,
    GET_SOC_INSIGHTS_EVENTS_ACTION_IDENTIFIER,
    GET_INDICATOR_INTEL_LOOKUP_RESULT_ACTION_IDENTIFIER,
    INDICATOR_THREAT_LOOKUP_WITH_TIDE_ACTION_IDENTIFIER,
    GET_SOC_INSIGHTS_ASSETS_ACTION_IDENTIFIER,
    INITIATE_INDICATOR_INTEL_LOOKUP_WITH_DOSSIER_ACTION_IDENTIFIER,
)


def get_integration_params(siemplify):
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
    api_key = siemplify.extract_configuration_param(
        INTEGRATION_NAME,
        "API Key",
        input_type=str,
        is_mandatory=True,
        print_value=False,
    )
    verify_ssl = siemplify.extract_configuration_param(
        INTEGRATION_NAME,
        "Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
    )

    return api_root, api_key, verify_ssl


def clean_params(params):
    """Remove keys with None values from a dictionary."""
    return {k: v for k, v in params.items() if v is not None}


def is_empty_string(value):
    return isinstance(value, str) and value.strip().lower() == "empty"


def get_nullable_field(value, existing_value=None, parser=None):
    if not value:
        return existing_value
    if is_empty_string(value):
        return None
    return parser(value) if parser else value


def parse_and_validate_int_list(param_str, param_name):
    if param_str is not None:
        if is_empty_string(param_str):
            return []
        return [
            validate_integer_param(
                x, param_name, zero_allowed=False, allow_negative=False
            )
            for x in string_to_list(param_str)
        ]
    return None


def parse_rules_param(rules):
    """
    Parse and validate the rules parameter as a JSON array.
    Returns the rules list if valid, otherwise raises ValueError.
    """
    if rules:
        try:
            rules_obj = json.loads(rules)
            if not isinstance(rules_obj, list):
                raise ValueError("Rules must be a JSON array.")
            return rules_obj
        except Exception:
            raise ValueError("Rules must be a valid JSON array string.")


def add_additional_params_to_payload(payload, additional_params):
    """
    Update the payload dict with validated additional_params only.
    """
    # Handle additional_params
    if additional_params:
        try:
            additional_params_obj = json.loads(additional_params)
            if not isinstance(additional_params_obj, dict):
                raise ValueError("Additional Parameters must be a JSON object.")
        except Exception:
            raise ValueError("Additional Parameters must be a JSON object.")

        allowed_keys = {
            "precedence",
            "access_codes",
            "doh_enabled",
            "doh_fqdn",
            "ecs",
            "onprem_resolve",
            "dfp_services",
            "net_address_dfps",
            "user_groups",
            "default_redirect_name",
        }
        unsupported_keys = set(additional_params_obj.keys()) - allowed_keys
        if unsupported_keys:
            raise InfobloxException(
                f"Unsupported key(s) in Additional Parameters: `{', '.join(unsupported_keys)}`. "
                f"Supported keys are: {', '.join(sorted(allowed_keys))}."
            )
        payload.update(additional_params_obj)
    return payload


def validate_indicators(items_list):
    ip4_pattern = re.compile(
        r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?:/([0-9]|[1-2][0-9]|3[0-2]))?$"
    )
    ip6_pattern = re.compile(
        r"^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}(?:/[0-9]{1,3})?$"
    )
    domain_pattern = re.compile(
        r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(?:\.[A-Za-z]{2,})+$"
    )
    for item in items_list:
        if not (
            ip4_pattern.match(item)
            or ip6_pattern.match(item)
            or domain_pattern.match(item)
        ):
            raise ValueError(
                f"Item '{item}' is not a valid IPv4, IPv6, or domain name."
            )
    return items_list


def validate_required_string(value, param_name):
    if not value or not value.strip():
        raise ValueError(f"{param_name} must be a non-empty string.")
    return value


def validate_integer_param(
    value, param_name, zero_allowed=False, allow_negative=False
):
    """
    Validates if the given value is an integer and meets the specified requirements.

    Args:
        value (int|str): The value to be validated.
        param_name (str): The name of the parameter for error messages.
        zero_allowed (bool, optional): If True, zero is a valid integer. Defaults to False.
        allow_negative (bool, optional): If True, negative integers are allowed. Defaults to False.
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
        raise InvalidIntegerException(
            f"{param_name} must be a non-negative integer."
        )
    if not zero_allowed and int_value == 0:
        raise InvalidIntegerException(
            f"{param_name} must be greater than zero."
        )
    return int_value


def string_to_list(items_str):
    if not items_str:
        return []
    return [item.strip() for item in items_str.split(",") if item.strip()]


def parse_tags(tags_str):
    if not tags_str:
        return None
    try:
        tags = json.loads(tags_str)
        if isinstance(tags, dict):
            return tags
        else:
            raise ValueError()
    except Exception:
        raise ValueError("Tags must be a valid JSON object string.")


def truncate_json_for_display(data, max_chars=MAX_JSON_CHARS):
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


def validate_enum(value, allowed_values, param_name):
    if value is not None and value not in allowed_values:
        raise ValueError(
            f"{param_name} must be one of {allowed_values}. Got: {value}"
        )
    return value


class HandleExceptions(object):
    """
    A class to handle exceptions based on different actions.
    """

    def __init__(
        self, api_identifier, error, response, error_msg="An error occurred"
    ):
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

    def do_process(self):
        """
        Processes the error by calling the appropriate handler.
        """
        if self.response.status_code >= 500:
            raise InternalSeverError(
                "It seems like the Infoblox server is experiencing some issues, Status: "
                + str(self.response.status_code)
            )

        try:
            handler = self.get_handler()
            _exception, _error_msg = handler()
        except InfobloxException:
            _exception, _error_msg = self.common_exception()

        raise _exception(_error_msg)

    def get_handler(self):
        """
        Retrieves the appropriate handler function based on the api_name.

        Returns:
            function: The handler function corresponding to the api_name.
        """
        return {
            PING_ACTION_IDENTIFIER: self.ping,
            GET_SOC_INSIGHTS_COMMENTS_ACTION_IDENTIFIER: self._handle_soc_insights_error,
            GET_SOC_INSIGHTS_INDICATORS_ACTION_IDENTIFIER: self._handle_soc_insights_error,
            GET_SOC_INSIGHTS_EVENTS_ACTION_IDENTIFIER: self._handle_soc_insights_error,
            GET_INDICATOR_INTEL_LOOKUP_RESULT_ACTION_IDENTIFIER:
                self.get_indicator_intel_lookup_result,
            INDICATOR_THREAT_LOOKUP_WITH_TIDE_ACTION_IDENTIFIER: self.get_indicator_tide_lookup,
            GET_SOC_INSIGHTS_ASSETS_ACTION_IDENTIFIER: self._handle_soc_insights_error,
            INITIATE_INDICATOR_INTEL_LOOKUP_WITH_DOSSIER_ACTION_IDENTIFIER:
                self._handle_dossier_lookup_result,
        }.get(self.api_identifier, self.common_exception)

    def common_exception(self):
        """
        Handles common exceptions that don't have a specific handler.

        If the response status code is 400, 404 or 409, extract API error message.
        Otherwise, it calls the general error handler.
        """
        if self.response is not None and self.response.status_code in (
            400,
            404,
            409,
        ):
            return self._handle_api_error()
        return self._handle_general_error()

    def _handle_api_error(self):
        """
        Extracts and formats error messages from API responses (400/404/409).
        Returns:
            tuple: (Exception class, error message)
        """
        try:
            error_json = self.response.json()
            if isinstance(error_json, dict) and "error" in error_json:
                # error is usually a list of dicts with 'message'
                error_list = error_json["error"]
                if (
                    isinstance(error_list, list)
                    and error_list
                    and "message" in error_list[0]
                ):
                    error_msg = error_list[0]["message"]

                    return InfobloxException, error_msg
        except Exception:
            pass
        # fallback to general error
        return self._handle_general_error()

    def _handle_general_error(self):
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

        return InfobloxException, error_msg

    # For sample only, we need to remove this
    def ping(self):
        return self._handle_general_error()

    def _handle_soc_insights_error(self):
        """
        Handle 404 errors for invalid insight IDs.
        Returns a tuple (ExceptionClass, message) as per project convention.
        """
        response = getattr(self, "response", None)
        if response.status_code == 404:
            return InfobloxException, "Insight doesn't exist."

        if response.status_code == 400:
            res = self.response.json()
            msg = res.get("message")
            if msg:
                return InfobloxException, msg

        return self._handle_general_error()

    def get_indicator_intel_lookup_result(self):
        """
        The default handler for indicator intel lookup result.

        Raises:
            ItemNotFoundException: An exception with a specific error message.
        """
        status_code = self.response.status_code
        if status_code == 404:
            res = self.response.json()
            error_msg = "Job ID does not exist. Error: " + (
                res.get("error") or ""
            )
            return ItemNotFoundException, error_msg

        return self.common_exception()

    def get_indicator_tide_lookup(self):
        """
        The default handler for indicator threat lookup result.

        Raises:
            InfobloxException: An exception with a specific error message.
        """
        status_code = self.response.status_code
        if status_code == 400:
            res = self.response.json()
            error_msg = res.get("message")
            return InfobloxException, error_msg

        return self.common_exception()

    def _handle_dossier_lookup_result(self):
        """
        Handle the response of the Indicator Intel Lookup with Dossier action.

        If the response status code is 400, extract the error message from the response body.
        Otherwise, call the common error handler.

        Returns:
            tuple: A tuple containing the exception class and the formatted error message.
        """
        status_code = self.response.status_code
        if status_code == 400:
            res = self.response.json()
            return InfobloxException, res.get("error")

        return self.common_exception()
