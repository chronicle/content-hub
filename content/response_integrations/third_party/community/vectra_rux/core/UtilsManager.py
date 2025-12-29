from __future__ import annotations

import datetime
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
            LIST_DETECTIONS_API_NAME: self.get_entity,
            ASSIGNMENT_API_NAME: self.get_assignment,
            MARK_DETECTION_API_NAME: self.get_mark_detection,
            LIST_GROUPS_API_NAME: self._handle_uri_error_request,
            ADD_NOTE_API_NAME: self.handler_note_action,
            REMOVE_NOTE_API_NAME: self.handler_note_action,
            ASSIGN_ENTITY_API_NAME: self.get_assignment,
            DOWNLOAD_PCAP_API_NAME: self.get_file,
            RESOLVE_ASSIGNMENT_API_NAME: self.get_assignment,
            UPDATE_GROUP_MEMBERS_API_NAME: self.update_group_members,
            PING: self.ping_handle,
            LIST_USERS_API_NAME: self.get_user_list,
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

    def get_mark_detection(self):
        """The default handler for mark detection.

        Raises:
            InvalidDetectionIDException: An exception with a formatted error message.

        """
        status_code = self.response.status_code
        res = self.response.json()
        if status_code == 404:
            error_msg = res["_meta"]["message"]
            return InvalidDetectionIDException, error_msg
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
                error_msg = error + ", Provide a valid hosts that exists."
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

    def ping_handle(self):
        """Handles connectivity exceptions that don't have a specific handler.

        If the response status code is 400, it calls the appropriate handler for bad request errors.
        Otherwise, it calls the common error handler.
        """
        res = self.response.json()
        error_msg = res.get("error")
        if self.response.status_code == 400:
            return RefreshTokenException, error_msg
        if self.response.status_code == 401:
            if VECTRA_REFRESH_TOKEN_EXPIRE_MESSAGE in error_msg:
                return RefreshTokenException, error_msg
            return UnauthorizeException, error_msg

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


def validate_triage(triage_as):
    """Validate triage_as parameter

    Args:
        triage_as (str): triage_as parameter

    Raises:
        VectraRUXException: If it contains invalid characters or length less than 4.

    """
    invalid_characters = "!@#$%^&*()"

    # Check if the string contains any invalid characters
    if any(char in triage_as for char in invalid_characters):
        raise VectraRUXException("Error: triage as contains invalid characters.")

    if len(triage_as) < 4:
        raise VectraRUXException("Error: triage as should be more than 3 characters.")


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
    unix_result = convert_datetime_to_unix_time(current_time - offset)
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
def get_all_open_cases(siemplify, cases_last_success_timestamp, all_cases):
    """Fetch all open cases from Siemplify.

    Returns:
        list of dict: List of cases with basic information (case_id, etc.).

    """
    if all_cases:
        siemplify.LOGGER.info("Fetching all the open cases")
        open_cases = siemplify.get_cases_ids_by_filter(
            status=CASE_STATUS,
            max_results=MAX_OPEN_CASES,
            start_time_from_unix_time_in_ms=1,
            operator="OR",
        )
    else:
        siemplify.LOGGER.info(
            f"Fetching all the open cases after unix time - {cases_last_success_timestamp}. Date time - {convert_unixtime_to_datetime(cases_last_success_timestamp)}",
        )
        open_cases = siemplify.get_cases_ids_by_filter(
            status=CASE_STATUS,
            max_results=MAX_OPEN_CASES,
            start_time_from_unix_time_in_ms=cases_last_success_timestamp,
            operator="OR",
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
