from __future__ import annotations

import datetime
import hashlib
import json
import os
import re

from soar_sdk.SiemplifyUtils import (
    convert_datetime_to_unix_time,
    convert_string_to_unix_time,
    convert_unixtime_to_datetime,
    unix_now,
    utc_now,
)

from .constants import *
from .VectraRUXExceptions import *


def get_integration_params(siemplify):
    """Extracts the common integration configuration parameters.

    Args:
        siemplify (SiemplifyAction): The SiemplifyAction object.

    Returns:
        tuple: A tuple of (api_root, client_id, client_secret).

    """
    api_root = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        input_type=str,
        is_mandatory=True,
    )
    client_id = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        input_type=str,
        is_mandatory=True,
    )
    client_secret = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        print_value=False,
        is_mandatory=True,
    )
    return api_root, client_id, client_secret


def compute_expiry(response):
    """Calculate token expiration time from OAuth response.

    Args:
        response (dict): OAuth token response dictionary containing 'expires_in' field.

    Returns:
        int: Expiration time in milliseconds since epoch.

    """
    now_ms = unix_now()
    expires_in = response.get(EXPIRES_IN_KEY)
    if expires_in is not None:
        try:
            return now_ms + (int(expires_in) * 1000) - (TOKEN_EXPIRY_BUFFER_SECONDS * 1000)
        except (TypeError, ValueError):
            pass
    return now_ms + (DEFAULT_EXPIRY_SECONDS * 1000)


def generate_encryption_key(client_id, api_root):
    """Generate an encryption key for token storage from existing settings.

    Args:
        client_id (str): OAuth client ID.
        api_root (str): VectraRUX API root.

    Returns:
        str: SHA-256 hash hex string used for token encryption.

    """
    unique_string = f"{client_id}:{api_root}"
    return hashlib.sha256(unique_string.encode()).hexdigest()


class HandleExceptions:
    """A class to handle exceptions based on different actions."""

    def __init__(self, api_name, error, response, error_msg="An error occurred"):
        """Initializes the HandleExceptions class.

        Args:
            api_name (str): API name.
            error (Exception): The error that occurred.
            error_msg (str, optional): A default error message. Defaults to "An error occurred".

        """
        self.api_name = api_name
        self.error = error
        self.response = response
        self.error_msg = error_msg

    def do_process(self):
        """Processes the error by calling the appropriate handler."""
        if self.response.status_code >= 500:
            raise InternalSeverError(
                f"It seems like the Vectra server is experiencing some issues, Status: {self.response.status_code}",
            )

        try:
            handler = self.get_handler()
            _exception, _error_msg = handler()
        except:
            _exception, _error_msg = self.common_exception()

        raise _exception(_error_msg)

    def get_handler(self):
        """Retrieves the appropriate handler function based on the api_name.

        Returns:
            function: The handler function corresponding to the api_name.

        """
        return {
            TAGGING_API_NAME: self.get_tags,
            DESCRIBE_DETECTION_API_NAME: self.get_entity,
            DESCRIBE_ENTITY_API_NAME: self.get_entity,
            LIST_ENTITY_API_NAME: self.get_entity,
            LIST_DETECTIONS_API_NAME: self.get_entity,
            LIST_ENTITY_DETECTIONS_API_NAME: self.get_entity,
            ASSIGNMENT_API_NAME: self.get_assignment,
            UPDATE_ASSIGNMENT_API_NAME: self.get_assignment,
            LIST_GROUPS_API_NAME: self._handle_uri_error_request,
            ADD_NOTE_API_NAME: self.handler_note_action,
            REMOVE_NOTE_API_NAME: self.handler_note_action,
            ASSIGN_ENTITY_API_NAME: self.get_assignment,
            DOWNLOAD_PCAP_API_NAME: self.get_file,
            UPDATE_GROUP_MEMBERS_API_NAME: self.update_group_members,
            LIST_USERS_API_NAME: self.get_user_list,
            LIST_ENTITY_NOTES_API_NAME: self.handler_note_action,
            UPDATE_ENTITY_NOTE_API_NAME: self.handler_note_action,
            LIST_TAGS_API_NAME: self.get_tags,
            SET_ENTITY_UNRESOLVED_PRIORITY_API_NAME: self.get_entity,
            SET_DETECTION_STATUS_API_NAME: self.get_entity,
            CLOSE_DETECTIONS_API_NAME: self.get_entity,
            OPEN_DETECTIONS_API_NAME: self.get_entity,
            SET_DETECTION_TICKET_API_NAME: self.get_entity,
            SET_ENTITY_TICKET_API_NAME: self.get_entity,
            QUERY_INVESTIGATION_API_NAME: self.get_query_investigation_error,
            GET_INVESTIGATION_RESULTS_API_NAME: self.get_entity,
        }.get(self.api_name, self.common_exception)

    def common_exception(self):
        """Handles common exceptions that don't have a specific handler.

        If the response status code is 400, it calls the appropriate handler for bad request errors.
        Otherwise, it calls the general error handler.
        """
        if self.response.status_code == 400:
            return self._handle_bad_request_error()
        if self.response.status_code == 401:
            return UnauthorizeException, "UnauthorizeException"

        return self._handle_general_error()

    def _handle_general_error(self):
        """Handles general errors by formatting the error message and returning the appropriate
        exception.

        Returns:
            tuple: A tuple containing the exception class and the formatted error message.

        """
        error_msg = f"{self.error_msg}: {self.error} - {self.error.response.content}"

        return VectraRUXException, error_msg

    def _handle_bad_request_error(self):
        error_response = self.response.json()

        if isinstance(error_response, list) and len(error_response) > 0:
            # If the response is a list, return the first error message
            return BadRequestException, error_response[0]
        if isinstance(error_response, dict):
            if "_meta" in error_response:
                # Remove the _meta key from the error response
                del error_response["_meta"]

            # Extract the error message from the response
            error_msg = error_response.get(list(error_response.keys())[0])
            return BadRequestException, error_msg

        # If no error message is found, return the general error message
        return self._handle_general_error()

    def _handle_not_found_error(self):
        """The default handler for 404 error.

        Raises:
            ItemNotFoundException: An exception with a formatted error message.

        """
        status_code = self.response.status_code
        res = self.response.json()
        if status_code == 404:
            error_msg = res.get("detail")
            return ItemNotFoundException, f"{error_msg}"
        return self.common_exception()

    def get_tags(self):
        """Handler for adding tags.

        Raises:
            AddTagException: An exception with a specific error message.

        """
        # Logic to extract error
        status_code = self.response.status_code
        res = self.response.json()
        if status_code == 404:
            error_msg = res.get("message") or res.get("reason")
            status = res.get("status")
            return ItemNotFoundException, f"{status}: {error_msg}"
        return self.common_exception()

    def get_assignment(self):
        """The default handler for assignment.

        Raises:
            UserNotPermittedException: An exception with a formatted error message.
            ItemNotFoundException: An exception with a specific error message.

        """
        status_code = self.response.status_code
        res = self.response.json()
        if status_code == 400:
            error_msg = ""
            for error in res["errors"]:
                error_msg += error.get("title")
            return UserNotPermittedException, error_msg
        if status_code == 404 or status_code == 409:
            error_msg = res.get("detail")
            return ItemNotFoundException, f"{error_msg}"
        return self.common_exception()

    def _handle_uri_error_request(self):
        """Handles the request URI too long error.

        If the response status code is 414, it returns a LongURIException with a specific error
        message.
        Otherwise, it calls the common exception handler.

        Returns:
            tuple: A tuple containing the exception class and the formatted error message.

        """
        status_code = self.response.status_code

        if status_code == 414:
            error_msg = (
                "The combined length of all parameter values exceeds the allowed limit."
            )
            return LongURIException, error_msg

        return self.common_exception()

    def handler_note_action(self):
        """Handler for note related action.

        Raises:
            ItemNotFoundException: An exception with a specific error message.

        """
        if not self.response.content:
            error_msg = "Entity ID is invalid"
            return ItemNotFoundException, error_msg

        status_code = self.response.status_code

        res = (
            self.response.json()
            if "application/json" in self.response.headers.get("Content-Type")
            else {}
        )

        error_messages = {
            403: (
                UserNotPermittedException,
                res.get("detail", "User not permitted to perform this action"),
            ),
            404: (ItemNotFoundException, "Entity ID or Note ID does not exist"),
            413: (
                RequestEntityTooLargeException,
                "Note is too large for the requested URL",
            ),
        }

        if status_code in error_messages:
            exception, error_msg = error_messages[status_code]
            return exception, error_msg

        return self.common_exception()

    def update_group_members(self):
        """Handles the assign group request error.
        If the response status code is 422, it extracts the error message from the response and
        returns a BadRequestException with the error message.
        Otherwise, it calls the common exception handler.

        Returns:
            tuple: A tuple containing the exception class and the formatted error message.

        """
        status_code = self.response.status_code
        error_response = self.response.json()
        if status_code == 422:
            error_msg = error_response["_meta"]["message"]
            error = error_msg.get("members") if isinstance(error_msg, dict) else []
            members = []
            # Extract the error message
            if isinstance(error, list):
                pattern1 = r"members value '([^']*)' is invalid\."
                pattern2 = r"IP address is not valid: (.*)"
                group_type = (
                    "domain" if error and error[0].startswith("members") else "IP"
                )
                for err in error:
                    match1 = re.search(pattern1, err)
                    match2 = re.search(pattern2, err)
                    members.append(match1.group(1) if match1 else match2.group(1))

                if not members:
                    error_msg = "Error: This group cannot be edited. "
                else:
                    error_msg = f"Following {group_type}s are invalid: {', '.join(members)}, Please provide a valid {group_type}s."
            else:
                error_msg = error + ", Provide a valid member that exists."
            return BadRequestException, error_msg

        if status_code == 404:
            error_msg = "Group id does not exist, please provide a valid group id."
            return ItemNotFoundException, error_msg

        return self.common_exception()

    def get_file(self):
        """Handler for downloading file.

        Raises:
            ItemNotFoundException: An exception with a specific error message.

        """
        # Logic to extract error
        status_code = self.response.status_code
        if status_code == 404:
            error_msg = "File Not Found"
            return ItemNotFoundException, f"{status_code}: {error_msg}"
        return self.common_exception()

    def get_entity(self):
        """The default handler for getting entity.

        Raises:
            ItemNotFoundException: An exception with a formatted error message.

        """
        status_code = self.response.status_code
        res = self.response.json()
        if status_code == 404:
            error_msg = res.get("detail")
            return ItemNotFoundException, f"{error_msg}"
        return self.common_exception()

    def get_user_list(self):
        """Handles exceptions for getting user list.

        Raises:
            BadRequestException: An exception with a specific error message.

        """
        status_code = self.response.status_code
        response = self.response.json()
        if status_code == 400 and isinstance(response, list):
            error_msg = "Invalid role provided. Please provide an existing role."
            return BadRequestException, error_msg

        return self.common_exception()

    def get_query_investigation_error(self):
        """Handler for the query investigation action.

        Handles the 400 response returned when the query syntax is invalid or an
        unsupported query version is provided, e.g.:
            {
                "error": {
                    "extra": [{"message": "query parsing failed: ...", ...}],
                    "errorCode": "SYNTAX_ERROR",
                    "errorId": "Q3H0A4"
                }
            }

        Raises:
            BadRequestException: An exception with a formatted error message.

        """
        status_code = self.response.status_code
        if status_code == 400:
            error_msg = "Invalid query provided. Please provide a valid query that follows the required syntax."
            return BadRequestException, error_msg

        return self.common_exception()


def validate_integer(value, zero_allowed=False, allow_negative=False, field_name=None):
    """Validates if the given value is an integer.

    Args:
        value (int|str): The value to be validated.
        zero_allowed (bool, optional): If True, zero is a valid integer. Defaults to False.
        allow_negative (bool, optional): If True, negative integers are allowed. Defaults to False.
        field_name (str, optional): The name of the field being validated. Defaults to None.

    Raises:
        InvalidIntegerException: If the given value is not a valid integer.

    Returns:
        int: The validated integer value.

    """
    try:
        value = int(value)
        if not zero_allowed and value == 0:
            raise InvalidIntegerException(
                f"Please enter a valid integer value for '{field_name}'.",
            )
        if not allow_negative and value < 0:
            raise InvalidIntegerException(
                f"Please enter a valid non-negative integer value for '{field_name}'.",
            )
        return value
    except:
        raise InvalidIntegerException(
            f"Please enter a valid integer value for '{field_name}'.",
        )


def extract_fields(response, mandatory_fields):
    """Extracts the mandatory fields and any additional fields that are present in the response
    up to the total number of required fields. If the total number of fields in the response
    is less than or equal to the total number of required fields, the entire response is returned.

    Args:
        response (dict): The response to extract the fields from.
        mandatory_fields (list): A list of the mandatory fields to extract.

    Returns:
        dict: A dictionary with the extracted fields.

    """
    updated_response = {
        key: response[key]
        for key, value in response.items()
        if not isinstance(value, (list, dict))
    }
    present_fields = {key: response[key] for key in mandatory_fields if key in response}

    total_fields_in_response = len(response)

    result = {}
    result.update(present_fields)

    total_required = len(mandatory_fields)

    remaining_fields_count = len(mandatory_fields) - len(present_fields)

    if total_fields_in_response <= total_required:
        return updated_response
    if remaining_fields_count > 0:
        remaining_fields = [key for key in response if key not in result]
        result.update(
            {key: response[key] for key in remaining_fields[:remaining_fields_count]},
        )

    return result


def process_action_parameter(action_parameter):
    """Processes the given action parameter by splitting it by comma, stripping each
    of the resulting strings and returning them as a list of strings.

    Args:
        action_parameter (str): The parameter to be processed

    Returns:
        list: A list of strings

    """
    return (
        list(
            set(
                parameter.strip()
                for parameter in action_parameter.split(",")
                if parameter.strip()
            ),
        )
        if action_parameter
        else None
    )


def validator(value, zero_allowed=False, name=None):
    if value:
        return validate_integer(value, zero_allowed=zero_allowed, field_name=name)
    return None


def save_attachment(path, name, content):
    """Save attachment

    Args:
        path (str): File Path
        name (str): File Name
        content (str): File content

    Returns:
        file path: File path where file will add

    """
    # Create path if not exists
    if not os.path.exists(path):
        os.makedirs(path)
    # File local path
    local_path = os.path.join(path, name)

    with open(local_path, "wb") as file:
        file.write(content)
    return local_path


def validate_limit_param(limit, param_name="Limit"):
    limit = limit.strip() if limit is not None else limit
    if limit == "0":
        raise InvalidIntegerException(f"{param_name} must be greater than 0.")

    return limit or 0


def get_alert_id(entity_id, last_modified_timestamp, entity_type):
    return f"{entity_type}#{entity_id}-{last_modified_timestamp}"

def get_detection_alert_id(detection_id, event_id):
    return f"{DETECTION_ALERT_ID_PREFIX}{detection_id}-{event_id}"


# Job functions
def get_last_success_time_for_job(
    siemplify,
    offset_with_metric,
    time_format=DATETIME_FORMAT,
    print_value=True,
    microtime=False,
    timestamp_key=CASES_TIMESTAMP_DB_KEY,
):
    # Fetch the last run timestamp
    last_run_timestamp = fetch_timestamp_for_job(
        siemplify,
        timestamp_key,
        datetime_format=True,
    )
    offset = datetime.timedelta(**offset_with_metric)
    current_time = utc_now()

    # Calculate the result based on the offset
    datetime_result = (
        current_time - offset
        if current_time - last_run_timestamp > offset
        else last_run_timestamp
    )

    # Convert result to Unix time
    unix_result = convert_datetime_to_unix_time(datetime_result)
    unix_result = (
        unix_result if not microtime else int(unix_result / NUM_OF_MILLI_IN_SEC)
    )

    if print_value:
        siemplify.LOGGER.info(
            f"Last success time. Date time:{datetime_result}.",
        )

    return unix_result if time_format == UNIX_FORMAT else datetime_result


def save_timestamp_for_job(
    siemplify,
    new_timestamp=unix_now(),
    timestamp_key=CASES_TIMESTAMP_DB_KEY,
):
    if isinstance(new_timestamp, datetime.datetime):
        new_timestamp = convert_datetime_to_unix_time(new_timestamp)

    try:
        siemplify.set_scoped_job_context_property(
            property_key=timestamp_key,
            property_value=json.dumps(new_timestamp),
        )
    except Exception as e:
        raise VectraRUXException(f"Failed saving timestamps to db, ERROR: {e}")


def fetch_timestamp_for_job(
    siemplify,
    timestamp_key=CASES_TIMESTAMP_DB_KEY,
    datetime_format=False,
):
    try:
        last_run_time = siemplify.get_scoped_job_context_property(
            property_key=timestamp_key,
        )
    except Exception as e:
        raise VectraRUXException(
            f"Failed reading timestamps from db, ERROR: {e}",
        )

    if last_run_time is None:
        last_run_time = 0
    try:
        last_run_time = int(last_run_time)
    except:
        last_run_time = convert_string_to_unix_time(last_run_time)

    if datetime_format:
        last_run_time = convert_unixtime_to_datetime(last_run_time)
    else:
        last_run_time = int(last_run_time)

    return last_run_time


def expire_inactive_detections(
    siemplify,
    inactive_detection_ids,
    cases_last_success_timestamp,
    all_cases,
    environments=CASE_DEFAULT_ENVIRONMENT,
    product_names=CASE_DEFAULT_PRODUCTNAME,
    max_cases=MAX_OPEN_CASES,
):
    """Job to close the alert(s) whose associated Vectra detection has gone inactive.

    Fetches at the fixed MAX_OPEN_CASES ceiling, then trims to `max_cases`
    before the expensive per-case loop, so the log shows the true backlog
    size even when it's larger than this run's processing budget.

    Returns:
        int | None: The highest modification_time_unix_time_in_ms seen among
        the cases that were actually processed (i.e. within the `max_cases`
        budget), for the caller to use as the next run's checkpoint. None if
        no case was successfully processed this run.
    """
    siemplify.LOGGER.info(
        f"Using checkpoint - {cases_last_success_timestamp}. Date time - "
        f"{convert_unixtime_to_datetime(cases_last_success_timestamp)} - to fetch open "
        f"cases (all_cases={all_cases}).",
    )
    open_cases = get_all_open_cases(siemplify, cases_last_success_timestamp, all_cases)
    siemplify.LOGGER.info(f"Fetched {len(open_cases)} open case(s).")

    cases_to_process = open_cases
    if len(open_cases) > max_cases:
        siemplify.LOGGER.info(f"Capping to {max_cases} case(s) (Max Cases To Process).")
        cases_to_process = open_cases[:max_cases]

    closed_alerts_count = 0
    skipped_cases_count = 0
    last_case_timestamp = None
    for o_case in cases_to_process:
        siemplify.LOGGER.info(f"processing case - {o_case}")
        try:
            entities = get_case_entities(siemplify, o_case)
            case_alerts_by_detection = get_case_alerts_by_detection_id(
                siemplify,
                entities,
                o_case,
                environments,
                product_names,
            )
        except Exception as e:
            skipped_cases_count += 1
            siemplify.LOGGER.error(f"Failed to process case {o_case}: {e}. Skipping.")
            continue

        last_case_timestamp = max(
            last_case_timestamp or 0,
            entities.get("modification_time") or entities.get("creation_time", 0),
        )

        for detection_id, alerts in case_alerts_by_detection.items():
            if detection_id not in inactive_detection_ids:
                continue

            for alert in alerts:
                alert_identifier = alert["identifier"]
                siemplify.LOGGER.info(
                    f"Detection {detection_id} is inactive on Vectra. "
                    f"Closing alert '{alert_identifier}' in case {o_case}.",
                )
                comment = (
                    f"Closing alert '{alert_identifier}' in case - {o_case} "
                    f"as the associated detection - {detection_id} is inactive on Vectra."
                )
                try:
                    siemplify.close_alert(
                        INACTIVE_DETECTION_ALERT_ROOT_CAUSE,
                        comment,
                        CASE_ALERT_REASON,
                        o_case,
                        alert_id=alert_identifier,
                    )
                    closed_alerts_count += 1
                except Exception as e:
                    siemplify.LOGGER.error(
                        f"Exception occured as alert - {alert_identifier} is already closed. Hence, Skipping to closing this alert",
                    )
                    siemplify.LOGGER.error(f"Exception - {e}")

    siemplify.LOGGER.info(
        f"Total {closed_alerts_count} alerts closed. {skipped_cases_count} case(s) skipped due to errors.",
    )

    return last_case_timestamp


def get_case_alerts_by_detection_id(siemplify, entities, o_case, environments, product_names):
    """Maps each Vectra detection ID referenced by a case to the alert(s) the Detection
    Events Connector created for it.

    Args:
        entities (dict): The case object returned by `_get_case_by_id`.
        o_case (str): The case ID, used for logging.
        environments (list): Allowed environments.
        product_names (list): Allowed product/device names.

    Returns:
        dict: Mapping of detection_id (str) to a list of dicts, each with the alert's
        "identifier" (str) and "creation_time" (int).

    """
    detection_alerts = {}

    if entities.get("environment") not in environments:
        siemplify.LOGGER.info(
            f"Case - {o_case} does not fall under the environments - {environments}.",
        )
        return detection_alerts

    for alert in entities.get("cyber_alerts", []):
        if alert.get("additional_properties", {}).get("DeviceProduct") not in product_names:
            siemplify.LOGGER.info(
                f"Case - {o_case}, Alert - {alert.get('identifier')} does not fall under the Product names - {product_names}.",
            )
            continue

        alert_identifier = alert.get("identifier")
        detection_ids = {
            str(event.get("additional_properties", {}).get("detection_id"))
            for event in alert.get("security_events", [])
            if event.get("additional_properties", {}).get("detection_id") is not None
        }

        if not detection_ids:
            siemplify.LOGGER.info(
                f"Case - {o_case}, Alert - {alert_identifier} has no detection_id.",
            )
            continue

        alert_entry = {
            "identifier": alert_identifier,
            "creation_time": alert.get("creation_time") or 0,
        }
        for detection_id in detection_ids:
            detection_alerts.setdefault(detection_id, []).append(alert_entry)

    return detection_alerts


def get_case_detection_alerts(siemplify, entities, o_case, environments, product_names):
    """Maps each Vectra detection_id referenced by a case to the alert(s) tied
    to it, carrying enough info to compare alerts for the same detection_id
    across different cases.

    Args:
        entities (dict): The case object returned by `_get_case_by_id`.
        o_case (str): The case ID the alerts belong to; stashed on each entry
            since callers compare alerts across multiple cases.
        environments (list): Allowed environments.
        product_names (list): Allowed product/device names.

    Returns:
        dict: Mapping of detection_id (str) to a list of dicts, each with
        "identifier" (str), "creation_time" (int), "investigation_status"
        (str, lowercased), "case_id" (str) and "name" (str, the CASE's own
        "title" field - confirmed via a live case to read
        "{RULE_GENERATOR}: {entity_uid}", e.g. "Vectra RUX: sgflutter-37".
        NOT the alert's own "name" field, which the platform stores as
        "{entity_uid}_{ticket_id}" for display uniqueness and is therefore
        unique per alert, not per entity - and NOT a "name" key on the case
        object, which doesn't exist).

    """
    detection_alerts = {}

    if entities.get("environment") not in environments:
        siemplify.LOGGER.info(
            f"Case {o_case} is in environment '{entities.get('environment')}', which "
            f"is outside the configured environments {environments}. Skipping this case.",
        )
        return detection_alerts

    for alert in entities.get("cyber_alerts", []):
        additional_properties = alert.get("additional_properties", {})
        if additional_properties.get("DeviceProduct") not in product_names:
            siemplify.LOGGER.info(
                f"Case {o_case}: alert {alert.get('identifier')} comes from a product "
                f"outside the configured products {product_names}. Skipping this alert.",
            )
            continue

        alert_identifier = alert.get("identifier")
        detection_ids = {
            str(event.get("additional_properties", {}).get("detection_id"))
            for event in alert.get("security_events", [])
            if event.get("additional_properties", {}).get("detection_id") is not None
        }

        if not detection_ids:
            siemplify.LOGGER.info(
                f"Case {o_case}: alert {alert_identifier} has no Vectra detection_id "
                f"on it. Skipping this alert.",
            )
            continue

        alert_entry = {
            "identifier": alert_identifier,
            "creation_time": alert.get("creation_time") or 0,
            "investigation_status": (
                additional_properties.get("investigation_status") or ""
            ).strip().lower(),
            "case_id": str(o_case),
            "name": entities.get("title") or "",
        }
        siemplify.LOGGER.info(
            f"Case {o_case}: alert {alert_identifier} belongs to detection(s) "
            f"{sorted(detection_ids, key=int)}, currently in investigation_status "
            f"'{alert_entry['investigation_status'] or 'unknown'}'.",
        )
        for detection_id in detection_ids:
            detection_alerts.setdefault(detection_id, []).append(alert_entry)

    return detection_alerts


def _is_already_closed_alert_error(exception):
    """Whether `exception` is the platform's "You can not perform this action
    on a closed alert" rejection (errorCode 2000) from `close_alert`, as
    opposed to a genuine failure (permissions, network, etc.).

    Matched on the response body text rather than a typed exception class,
    since `close_alert` raises a generic HTTP error with no dedicated
    exception type for this case.
    """
    message = str(exception).lower()
    return "errorcode\":2000" in message or "on a closed alert" in message


def get_open_cases_by_case_name(siemplify, case_name, environments, exclude_case_ids):
    """Fetch every OPEN case sharing `case_name` - regardless of when it was
    created - so a detection_id's alert history sitting outside this job's
    configured time window is not missed when deciding whether its previous
    alerts are safe to close.

    Args:
        case_name (str): The case name to search for - the CASE's own name
            (shared by every alert filed under it), not an individual
            alert's name (which bakes in its detection_id/event_id and is
            therefore unique per alert, not per case).
        environments (list): Allowed environments.
        exclude_case_ids (set): Case IDs (str) already processed this run;
            skipped here to avoid reprocessing/double-counting.

    Returns:
        list of dict: Case objects (as returned by `_get_case_by_id`), not
        already in `exclude_case_ids`.

    """
    if not case_name:
        return []

    siemplify.LOGGER.info(
        f"Looking for other open cases named '{case_name}', so an earlier alert for "
        f"this detection sitting outside the fetch window isn't missed.",
    )
    try:
        cases = siemplify.get_cases_by_filter(
            case_names=[case_name],
            statuses=[CASE_STATUS_FILTER_OPEN],
            environments=environments,
        )
    except Exception as e:
        siemplify.LOGGER.error(
            f"Failed to search for open cases named '{case_name}': {e}",
        )
        return []

    candidate_ids = []
    historical_cases = []
    for case in cases or []:
        # `get_cases_by_filter` may return full case objects or bare case IDs
        # depending on SDK version - normalize to full case objects.
        case_id, case_details = (case.get("identifier"), case) if isinstance(case, dict) else (case, None)
        if case_id is None:
            continue
        candidate_ids.append(str(case_id))

        if str(case_id) in exclude_case_ids:
            continue

        if case_details is None:
            try:
                case_details = get_case_entities(siemplify, case_id)
            except Exception as e:
                siemplify.LOGGER.error(f"Failed to fetch case {case_id}: {e}")
                continue

        # The filter is queried moments before this check, so the case can have
        # closed in between (filter lag or a concurrent close elsewhere).
        # Guard against acting on stale data rather than trusting the filter.
        if case_details.get("status") != CASE_STATUS_FILTER_OPEN:
            siemplify.LOGGER.info(
                f"Case {case_id} matched the name search but has since closed. "
                f"Skipping it.",
            )
            continue

        historical_cases.append(case_details)

    if candidate_ids:
        siemplify.LOGGER.info(
            f"Found {len(candidate_ids)} case(s) named '{case_name}': {candidate_ids}. "
            f"{len(historical_cases)} of them are new to this run and will be "
            f"inspected; the rest are either already handled or no longer open.",
        )
    else:
        siemplify.LOGGER.info(f"No open cases found named '{case_name}'.")

    return historical_cases


def _pull_in_historical_alerts(
    siemplify,
    case_name,
    environments,
    product_names,
    processed_case_ids,
    historical_cases_cache,
    detection_alerts_map,
    related_cases_budget,
):
    """Fetches every OPEN case sharing `case_name` and folds ALL of its
    detection_id(s) -> alerts into `detection_alerts_map` - not just the
    detection_id that triggered this lookup - so an earlier alert sitting
    outside this run's time window is not missed.

    A case can hold alerts for several detection_ids that share the same
    entity (and therefore the same case_name). Pulling only the one
    detection_id being searched for would still let the case be marked fully
    `processed_case_ids` - so any OTHER detection_id in that same case would
    never get a chance to see it again, silently losing its alerts. Doing a
    full extraction every time a case is touched means marking it processed
    is always safe.

    `historical_cases_cache` memoizes the case-name lookup itself: several
    detection_ids can share the same case_name within a single case, which
    would otherwise repeat the same `get_open_cases_by_case_name` API call
    once per detection_id. Reusing the cached list is safe even as
    `processed_case_ids` keeps growing across the run, since each historical
    case is still checked against the latest `processed_case_ids` before
    being used.

    `related_cases_budget` caps how many historical cases get fully inspected
    (i.e. `get_case_detection_alerts` called on them) across the WHOLE run,
    not just this call. `get_cases_by_filter` has no server-side max_results
    support, so a single case_name match could otherwise return an unbounded
    number of cases. Once the cap is hit, the rest are left for a later run
    to pick up.

    Args:
        case_name (str): The case name to search for.
        processed_case_ids (set): Case IDs (str) already processed this run;
            mutated in place as historical cases are consumed.
        historical_cases_cache (dict): case_name -> list of case dicts,
            shared and mutated across calls for the whole run.
        detection_alerts_map (dict): detection_id -> list of alert entries
            (see `get_case_detection_alerts`); mutated in place with
            whatever is found in historical cases not already processed.
        related_cases_budget (dict): {"inspected": int, "exhausted_logged":
            bool}, shared and mutated across the whole run.

    """
    def _mark_budget_exhausted():
        if not related_cases_budget["exhausted_logged"]:
            siemplify.LOGGER.info(
                f"Reached the limit of {MAX_RELATED_CASES_TO_INSPECT} older case(s) "
                f"inspected in one run. Any remaining older cases will be picked up "
                f"on a later run.",
            )
            related_cases_budget["exhausted_logged"] = True

    if related_cases_budget["inspected"] >= MAX_RELATED_CASES_TO_INSPECT:
        _mark_budget_exhausted()
        return

    if case_name not in historical_cases_cache:
        historical_cases_cache[case_name] = get_open_cases_by_case_name(
            siemplify, case_name, environments, processed_case_ids,
        )

    for historical_case in historical_cases_cache[case_name]:
        historical_case_id = historical_case.get("identifier")
        if historical_case_id is None or str(historical_case_id) in processed_case_ids:
            continue

        if related_cases_budget["inspected"] >= MAX_RELATED_CASES_TO_INSPECT:
            _mark_budget_exhausted()
            break

        processed_case_ids.add(str(historical_case_id))
        related_cases_budget["inspected"] += 1

        historical_case_alerts = get_case_detection_alerts(
            siemplify,
            historical_case,
            historical_case_id,
            environments,
            product_names,
        )
        if historical_case_alerts:
            total_alerts = sum(len(alerts) for alerts in historical_case_alerts.values())
            siemplify.LOGGER.info(
                f"Found {total_alerts} earlier alert(s) for {len(historical_case_alerts)} "
                f"detection(s) in older case {historical_case_id} (also named "
                f"'{case_name}').",
            )
        for historical_detection_id, historical_alerts in historical_case_alerts.items():
            detection_alerts_map.setdefault(historical_detection_id, []).extend(historical_alerts)


def _process_case(
    siemplify,
    case_id,
    environments,
    product_names,
    processed_case_ids,
    detection_alerts_map,
):
    """Fetch one case and fold its own detection_id -> alerts into
    detection_alerts_map.

    Marks `case_id` as processed itself, so a later case-name lookup (see
    `_expand_terminal_detections_to_related_cases`) can never re-discover this
    same case as one of its own results.

    Returns:
        int | None: The case's modification/creation time, for the caller's
        checkpoint. None if the case couldn't be fetched.

    """
    try:
        case_details = get_case_entities(siemplify, case_id)
        case_detection_alerts = get_case_detection_alerts(
            siemplify,
            case_details,
            case_id,
            environments,
            product_names,
        )
    except Exception as e:
        siemplify.LOGGER.error(f"Failed to process case {case_id}: {e}. Skipping.")
        return None

    processed_case_ids.add(str(case_id))

    for detection_id, alerts in case_detection_alerts.items():
        detection_alerts_map.setdefault(detection_id, []).extend(alerts)

    return case_details.get("modification_time") or case_details.get("creation_time", 0)


def _expand_terminal_detections_to_related_cases(
    siemplify,
    detection_alerts_map,
    environments,
    product_names,
    processed_case_ids,
    historical_cases_cache,
    related_cases_budget,
):
    """For every detection_id whose most-recently-created known alert already
    looks closed/expired, look past the fetch window for that detection's
    other OPEN cases by name, so an earlier alert sitting outside the window
    isn't missed when the closing decision is made.

    Only detections that already look terminal (based on the alerts found in
    this run's in-window cases) are expanded. A detection still in progress
    has nothing to close yet, so searching for its other cases would be a
    wasted API call - and would burn `related_cases_budget` that a genuinely
    terminal detection elsewhere might need.

    Names are collected into a snapshot set before any expansion runs, since
    `_pull_in_historical_alerts` mutates `detection_alerts_map` in place -
    iterating the dict directly while it grows would raise
    "dictionary changed size during iteration".

    Mutates `detection_alerts_map`, `processed_case_ids` and
    `historical_cases_cache` in place; nothing is returned.

    """
    case_names_to_search = set()
    for alerts in detection_alerts_map.values():
        sorted_alerts = sorted(alerts, key=lambda alert: alert["creation_time"])
        latest_alert = sorted_alerts[-1]
        if latest_alert["investigation_status"] not in CLOSED_OR_EXPIRED_INVESTIGATION_STATUSES:
            continue
        case_name = next(
            (alert["name"] for alert in alerts if alert.get("name")),
            None,
        )
        if case_name:
            case_names_to_search.add(case_name)

    if not case_names_to_search:
        siemplify.LOGGER.info(
            "None of this run's detections have a closed/expired alert yet, so there "
            "is nothing to look up in older cases.",
        )
        return

    siemplify.LOGGER.info(
        f"Some detections already look closed/expired, spanning {len(case_names_to_search)} "
        f"distinct case name(s). Checking each of those names for earlier alerts sitting "
        f"in older cases.",
    )
    for case_name in sorted(case_names_to_search):
        _pull_in_historical_alerts(
            siemplify,
            case_name,
            environments,
            product_names,
            processed_case_ids,
            historical_cases_cache,
            detection_alerts_map,
            related_cases_budget,
        )


def close_previous_alerts_for_expired_detections(
    siemplify,
    cases_last_success_timestamp,
    all_cases,
    environments=CASE_DEFAULT_ENVIRONMENT,
    product_names=CASE_DEFAULT_PRODUCTNAME,
    max_cases=MAX_OPEN_CASES,
):
    """Job to close every previous alert for a Vectra detection_id - across
    whichever cases they landed in - once the most recently created alert for
    that detection_id has an investigation_status of "closed" or "expired".

    Alerts are grouped by detection_id across all open cases processed this
    run - not just within a single case - since the same detection_id can end
    up spread across separate cases (e.g. an earlier case for that
    detection_id was closed and a later event opened a new one).

    Also looks past the configured time window: once every in-window case is
    processed, each detection_id whose latest known alert already looks
    closed/expired has every OTHER OPEN case sharing that detection_id's case
    name (the connector names a case after its alert) fetched regardless of
    age, so an earlier alert for the same detection_id is not missed just
    because its case falls outside the window. See
    `_expand_terminal_detections_to_related_cases`.

    Fetches at the fixed MAX_OPEN_CASES ceiling, then trims to `max_cases`
    before the expensive per-case loop, so the log shows the true backlog
    size even when it's larger than this run's processing budget.

    Returns:
        tuple[int | None, int]: The highest modification_time seen among the
        cases that were actually processed (i.e. within the `max_cases`
        budget) - None if no case was successfully processed this run - and
        the count of alerts that failed to close, for the caller to decide
        whether to surface this run as failed.

    """
    siemplify.LOGGER.info(
        f"Looking for open cases updated since "
        f"{convert_unixtime_to_datetime(cases_last_success_timestamp)}.",
    )
    open_cases = get_all_open_cases(siemplify, cases_last_success_timestamp, all_cases)
    siemplify.LOGGER.info(f"Found {len(open_cases)} open case(s) to review.")

    cases_to_process = open_cases
    if len(open_cases) > max_cases:
        siemplify.LOGGER.info(
            f"That's more than the 'Max Cases To Process' limit of {max_cases}, so "
            f"only the first {max_cases} will be reviewed this run; the rest will be "
            f"picked up on a later run.",
        )
        cases_to_process = open_cases[:max_cases]

    # Step 1: build a map of detection_id -> alerts across ALL processed
    # cases, so the "latest alert" for a detection_id is found wherever it
    # landed, not just within a single case.
    detection_alerts_map = {}
    skipped_cases_count = 0
    last_case_timestamp = None
    processed_case_ids = set()
    historical_cases_cache = {}
    related_cases_budget = {"inspected": 0, "exhausted_logged": False}
    for o_case in cases_to_process:
        if str(o_case) in processed_case_ids:
            # Already fully extracted via an earlier case-name lookup this run.
            siemplify.LOGGER.info(
                f"Case {o_case} was already reviewed earlier in this run. Skipping.",
            )
            continue

        siemplify.LOGGER.info(f"Reviewing case {o_case}.")
        case_timestamp = _process_case(
            siemplify,
            o_case,
            environments,
            product_names,
            processed_case_ids,
            detection_alerts_map,
        )
        if case_timestamp is None:
            skipped_cases_count += 1
            continue

        last_case_timestamp = max(last_case_timestamp or 0, case_timestamp)

    _expand_terminal_detections_to_related_cases(
        siemplify,
        detection_alerts_map,
        environments,
        product_names,
        processed_case_ids,
        historical_cases_cache,
        related_cases_budget,
    )

    cross_case_detection_ids = sorted(
        (
            detection_id
            for detection_id, alerts in detection_alerts_map.items()
            if len({alert["case_id"] for alert in alerts}) > 1
        ),
        key=int,
    )
    siemplify.LOGGER.info(
        f"Found {len(detection_alerts_map)} detection(s) with alerts in this run's "
        f"cases; {len(cross_case_detection_ids)} of them have alerts spread across "
        f"more than one case: {cross_case_detection_ids}.",
    )

    # Step 2: for each detection_id with 2+ alerts, check whether the most
    # recently created one is closed/expired, and if so close the rest,
    # wherever they landed.
    closed_alerts_count = 0
    already_closed_alerts_count = 0
    failed_alerts_count = 0
    for detection_id, alerts in detection_alerts_map.items():
        if len(alerts) < 2:
            continue

        involved_case_ids = sorted({alert["case_id"] for alert in alerts}, key=int)
        siemplify.LOGGER.info(
            f"Detection {detection_id} has {len(alerts)} alert(s) across "
            f"{len(involved_case_ids)} case(s): {involved_case_ids}. Checking whether "
            f"the most recent one is closed/expired on Vectra.",
        )

        sorted_alerts = sorted(alerts, key=lambda alert: alert["creation_time"])
        latest_alert, previous_alerts = sorted_alerts[-1], sorted_alerts[:-1]

        if latest_alert["investigation_status"] not in CLOSED_OR_EXPIRED_INVESTIGATION_STATUSES:
            siemplify.LOGGER.info(
                f"Detection {detection_id}'s most recent alert (case "
                f"{latest_alert['case_id']}) is still '{latest_alert['investigation_status'] or 'unknown'}' "
                f"on Vectra, so its older alerts are left open.",
            )
            continue

        siemplify.LOGGER.info(
            f"Detection {detection_id}'s most recent alert (case "
            f"{latest_alert['case_id']}) is '{latest_alert['investigation_status']}' on "
            f"Vectra. Closing its {len(previous_alerts)} older alert(s), spread across "
            f"{len({alert['case_id'] for alert in previous_alerts})} case(s).",
        )

        for alert in previous_alerts:
            case_id, alert_identifier = alert["case_id"], alert["identifier"]
            comment = (
                f"Closing alert '{alert_identifier}' in case - {case_id} as the latest "
                f"alert '{latest_alert['identifier']}' in case - {latest_alert['case_id']} "
                f"for detection - {detection_id} has investigation_status "
                f"'{latest_alert['investigation_status']}'."
            )
            try:
                siemplify.close_alert(
                    OUTDATED_ALERT_ROOT_CAUSE,
                    comment,
                    CASE_ALERT_REASON,
                    case_id,
                    alert_id=alert_identifier,
                )
                closed_alerts_count += 1
            except Exception as e:
                if _is_already_closed_alert_error(e):
                    already_closed_alerts_count += 1
                    siemplify.LOGGER.info(
                        f"Alert '{alert_identifier}' in case {case_id} was already "
                        f"closed - nothing more to do here.",
                    )
                    continue

                failed_alerts_count += 1
                siemplify.LOGGER.error(
                    f"Could not close alert '{alert_identifier}' in case {case_id}: {e}",
                )
                try:
                    siemplify.add_comment(
                        f"Failed to auto-close this alert as outdated - see job logs "
                        f"for details.",
                        case_id,
                        alert_identifier=alert_identifier,
                    )
                except Exception as comment_error:
                    siemplify.LOGGER.error(
                        f"Also could not leave a comment on alert '{alert_identifier}' "
                        f"in case {case_id} explaining the failure: {comment_error}",
                    )

    siemplify.LOGGER.info(
        f"Done. {closed_alerts_count} alert(s) closed, {already_closed_alerts_count} "
        f"were already closed, {failed_alerts_count} failed to close, and "
        f"{skipped_cases_count} case(s) were skipped due to errors.",
    )

    return last_case_timestamp, failed_alerts_count

def clear_empty_cases(
    siemplify,
    cases_last_success_timestamp,
    all_cases,
    environments=CASE_DEFAULT_ENVIRONMENT,
    product_names=CASE_DEFAULT_PRODUCTNAME,
):
    """Job to clear empty cases from Siemplify SOAR."""
    # Step 1: Fetch all open cases
    open_cases = get_all_open_cases(siemplify, cases_last_success_timestamp, all_cases)
    siemplify.LOGGER.info(f"Total {len(open_cases)} cases are open")
    case_dict = {}
    # Step 2: Iterate through each case
    for o_case in open_cases:
        # Get the entity and associated detections for the case
        siemplify.LOGGER.info(f"processing case - {o_case}")
        entities = get_case_entities(siemplify, o_case)
        alert_detection_list = get_case_detections(
            siemplify,
            entities,
            o_case,
            environments,
            product_names,
        )
        if alert_detection_list:
            case_dict[str(o_case)] = alert_detection_list

    if open_cases:
        # Run the function for findings duplicate and close those cases
        siemplify.LOGGER.info(
            f"A total of {len(case_dict)} open cases will be processed.",
        )
        find_identical_alerts(siemplify, case_dict)


# Supporting functions
def get_all_open_cases(siemplify, cases_last_success_timestamp, all_cases, max_cases=MAX_OPEN_CASES):
    """Fetch all open cases from Siemplify.

    Filters on start_time OR update_time, not start_time alone: a case can
    have been created long before `cases_last_success_timestamp` and still
    be exactly what a caller needs to catch, if it just received a fresh
    alert (which bumps its update_time, not its start_time). Filtering on
    start_time alone would leave such a case unfetched no matter how
    recently it changed.

    Returns:
        list of dict: List of cases with basic information (case_id, etc.).

    """
    if all_cases:
        siemplify.LOGGER.info("Fetching every open case, regardless of when it last changed.")
        open_cases = siemplify.get_cases_ids_by_filter(
            status=CASE_STATUS,
            max_results=max_cases,
            start_time_from_unix_time_in_ms=1,
            operator="OR",
            sort_by="UPDATE_TIME",
            sort_order="ASC",
        )
    else:
        siemplify.LOGGER.info(
            f"Fetching open cases created or updated since "
            f"{convert_unixtime_to_datetime(cases_last_success_timestamp)}.",
        )
        open_cases = siemplify.get_cases_ids_by_filter(
            status=CASE_STATUS,
            max_results=max_cases,
            start_time_from_unix_time_in_ms=cases_last_success_timestamp,
            update_time_from_unix_time_in_ms=cases_last_success_timestamp,
            operator="OR",
            sort_by="UPDATE_TIME",
            sort_order="ASC",
        )

    if open_cases and len(open_cases) >= max_cases:
        siemplify.LOGGER.error(
            f"There are at least {max_cases} open case(s) matching this fetch, which "
            f"is the fetch limit - some open cases were not fetched this run and will "
            f"be picked up on a later run.",
        )
    return open_cases


def get_case_entities(siemplify, case_id):
    """Fetch all entities associated with a given case.

    Args:
        case_id (str): The unique ID of the case.

    Returns:
        list of dict: List of entities in the case (entity_id, entity_name, etc.).

    """
    return siemplify._get_case_by_id(case_id)


def get_case_detections(siemplify, entities, o_case, environments, product_names):
    """Fetch all detections associated with a given case.

    Args:
        case_id (str): The unique ID of the case.

    Returns:
        list of dict: List of detections associated with the case.

    """
    detections = {}

    if entities.get("environment") not in environments:
        siemplify.LOGGER.info(
            f"Case - {o_case} does not fall under the environments - {environments}.",
        )
        return detections

    sorted_alerts = alerts = entities.get("cyber_alerts", [])
    try:
        if alerts and len(alerts) > 1:
            # Sorting alerts by their creation_time. Here, We observe this time is ingestion time
            siemplify.LOGGER.info("Sorting alerts list by their creation_time")
            sorted_alerts = sorted(alerts, key=lambda alert: alert["creation_time"])
    except KeyError as e:
        siemplify.LOGGER.info(
            f"Case - {o_case} alerts does not contains 'creation_time' in list. Hence, skipping to sort.",
        )
        siemplify.LOGGER.error(f"Exception - {e}")

    for alert in sorted_alerts:
        security_events = alert.get("security_events", [])
        events_id_list = []
        if alert.get("additional_properties", {}).get("DeviceProduct") in product_names:
            for event in security_events:
                if event.get("additional_properties", {}).get("id"):
                    events_id_list.append(
                        event.get("additional_properties", {}).get("id"),
                    )
                else:
                    siemplify.LOGGER.info(
                        f"Case - {o_case}, Alert - {alert.get('identifier')} has no detections.",
                    )
            if events_id_list:
                detections[alert.get("identifier")] = list(set(events_id_list))
        else:
            siemplify.LOGGER.info(
                f"Case - {o_case}, Alert - {alert.get('identifier')} does not fall under the Product names - {product_names}.",
            )
            break
    return detections


def find_identical_alerts(siemplify, cases):
    """Finds identical alerts and determines which cases/alerts to remove based on the provided logic,
    while ignoring previously closed cases and alerts.

    Args:
        cases (dict): Dictionary of cases with their alerts and event IDs.

    Example structure:
    {
        'case_1': {'Alert1': ['2', '1']},
        'case_2': {'Alert2': ['2', '1', '4']},
        'case_3': {'Alert3': ['1'], 'Alert4': ['5', '8']},
        'case_4': {'Alert5': ['1']}
    }

    Returns:
        None: Prints the operations performed and calls the necessary functions.

    """
    closed_cases_count = 0
    closed_alerts_count = 0

    def close_case_as_not_malicious(case_id, comment, alert_name):
        """Closes the specified case as not malicious.

        Args:
            case_id (str): The ID of the case to close.
            alert_name (str): The name/identifier of the alert to remove.
            comment (str): commennt of the alert to remove.

        Returns:
            closed_alert_count (int): Alert close success or failure count

        """
        try:
            closed_case_count = 0
            siemplify.LOGGER.info(f"Closing case {case_id}")
            closed_cases.add(case_id)  # Mark the case as closed
            siemplify.close_case(
                CASE_ROOT_CAUSE,
                comment,
                CASE_ALERT_REASON,
                case_id,
                alert_identifier=alert_name,
            )
            closed_case_count += 1
        except Exception as e:
            siemplify.LOGGER.error(f"Exception - {e}")
            siemplify.LOGGER.error(
                f"Exception occured as case - {case_id} is already closed. Hence, Skipping to closing this case",
            )
        return closed_case_count

    def remove_alert_from_case(case_id, alert_name, comment):
        """Removes a specific alert from a case without closing the case.

        Args:
            case_id (str): The ID of the case.
            alert_name (str): The name/identifier of the alert to remove.
            comment (str): commennt of the alert to remove.

        Returns:
            closed_alert_count (int): Alert close success or failure count

        """
        try:
            closed_alert_count = 0
            siemplify.LOGGER.info(f"Closing alert '{alert_name}' from case {case_id}")
            closed_alerts.add((case_id, alert_name))  # Mark the alert as removed
            siemplify.close_alert(
                ALERT_ROOT_CAUSE,
                comment,
                CASE_ALERT_REASON,
                case_id,
                alert_id=alert_name,
            )
            closed_alert_count += 1
        except Exception as e:
            siemplify.LOGGER.error(f"Exception - {e}")
            siemplify.LOGGER.error(
                f"Exception occured as alert - {alert_name} is already closed. Hence, Skipping to closing this alert",
            )
        return closed_alert_count

    # Step 1: Sort cases by their IDs
    sorted_cases = sorted(
        cases.items(),
        key=lambda x: int(x[0]),
    )  # Sort by case IDs numerically

    # Step 2: Create a map of event IDs to cases and alerts for easier lookup
    event_map = {}
    for case_id, alerts in sorted_cases:
        for alert_name, event_ids in alerts.items():
            for event_id in event_ids:
                if event_id not in event_map:
                    event_map[event_id] = []
                event_map[event_id].append(
                    {"case_id": case_id, "alert_name": alert_name},
                )

    # Keep track of closed cases and removed alerts
    closed_cases = set()
    closed_alerts = set()

    # Step 3: Process each case to determine if it should be closed or alerts removed
    for case_id, alerts in sorted_cases:
        if case_id in closed_cases:
            continue  # Skip already closed cases

        for alert_name, event_ids in alerts.items():
            if (case_id, alert_name) in closed_alerts:
                continue  # Skip already removed alerts

            # Check if all event IDs in this alert are present in non-closed cases/alerts
            identical_alerts = [
                mapping
                for event_id in event_ids
                for mapping in event_map[event_id]
                if mapping["case_id"] != case_id or mapping["alert_name"] != alert_name
                if mapping["case_id"] not in closed_cases
                and (mapping["case_id"], mapping["alert_name"]) not in closed_alerts
            ]

            alert_name_counts = {}
            for alert in identical_alerts:
                name = alert["alert_name"]
                if name in alert_name_counts:
                    alert_name_counts[name] += 1
                else:
                    alert_name_counts[name] = 1

            # Get the count of the target alert
            target_count = len(event_ids)

            # Check if the target alert's count is greater than or equal to others
            proceed = False
            for name, count in alert_name_counts.items():
                if target_count == count:
                    proceed = True
                    break
            if proceed:
                # Case should be closed if all alerts and their event IDs are duplicated in different case
                case_alert_dict = {alert["case_id"] for alert in identical_alerts}
                if len(case_alert_dict) >= 1 and case_id not in case_alert_dict:
                    siemplify.LOGGER.info(
                        f"Case {case_id} can be closed; identical alerts found: {identical_alerts}",
                    )
                    comment = f"Closing case - {case_id} as identical alerts found: {identical_alerts}"
                    closed_cases_count += close_case_as_not_malicious(
                        case_id,
                        comment,
                        alert_name,
                    )
                    break  # Move to the next case
                # Remove only specific alerts that are fully duplicated
                if identical_alerts:
                    siemplify.LOGGER.info(
                        f"Alert '{alert_name}' in case {case_id} can be removed; duplicate events: {identical_alerts}",
                    )
                    comment = f"Closing Alert - '{alert_name}' from case - {case_id} as it is duplicate events found: {identical_alerts}"
                    closed_alerts_count += remove_alert_from_case(
                        case_id,
                        alert_name,
                        comment,
                    )
            else:
                siemplify.LOGGER.info(
                    f"Alert '{alert_name}' in case {case_id} can not be removed as it contains more events then other alerts in same or other identical case",
                )

    siemplify.LOGGER.info(f"Total {closed_cases_count} cases closed")
    siemplify.LOGGER.info(f"Total {closed_alerts_count} alerts closed")


def process_action_parameter_integer(action_parameter, field_name):
    """Processes the given action parameter by splitting it by comma, stripping each
    of the resulting strings and returning them as a list of string.

    Args:
        action_parameter (str): The parameter to be processed
        field_name (str): The name of the parameter

    Returns:
        list: A list of strings

    """
    if action_parameter:
        return [
            str(validate_integer(parameter.strip(), field_name=field_name))
            for parameter in action_parameter.split(",")
            if parameter.strip()
        ]
    return []
