from __future__ import annotations

import time

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.api_manager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    CREATE_TASK_FOR_IOCS_SCRIPT_NAME,
    NO_ENTITIES_ERROR,
    NO_VALID_IOC_ERROR,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.cyware_exceptions import CywareException
from ..core.utils import get_entities, get_integration_params, validate_integer_param


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_TASK_FOR_IOCS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_FALSE
    json_results: list = []

    try:
        base_url, access_id, secret_key, verify_ssl = get_integration_params(siemplify)
        ioc_values = get_entities(siemplify)
        text = siemplify.extract_action_param("Text", print_value=False, is_mandatory=True)
        priority = siemplify.extract_action_param("Priority", print_value=True, is_mandatory=True)
        task_status = siemplify.extract_action_param("Status", print_value=True, is_mandatory=True)

        deadline_days_str = siemplify.extract_action_param(
            "Deadline", print_value=True, is_mandatory=True
        )
        assignee_email = siemplify.extract_action_param(
            "Assignee Email ID", print_value=True, is_mandatory=False
        )

        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        if text:
            text = text.strip()
            if len(text) > 2000:
                output_message = "Text must not exceed 2000 characters."
                result_value = RESULT_VALUE_FALSE
                status = EXECUTION_STATE_FAILED
                return

        if not ioc_values:
            output_message = NO_ENTITIES_ERROR
            result_value = RESULT_VALUE_TRUE
            status = EXECUTION_STATE_COMPLETED
            return

        # Validate and calculate deadline
        deadline_days = validate_integer_param(
            deadline_days_str, "Deadline", zero_allowed=False, max_value=365
        )
        current_time = int(time.time())
        deadline_seconds = deadline_days * 24 * 60 * 60
        deadline_epoch = current_time + deadline_seconds

        siemplify.LOGGER.info(
            f"Calculated deadline: {deadline_days} days from now = {deadline_epoch} (epoch)"
        )

        cyware_manager = APIManager(
            base_url.strip(), access_id, secret_key, verify_ssl=verify_ssl, siemplify=siemplify
        )

        # Retrieve user by email if provided
        assignee_user_id = None
        if assignee_email and assignee_email.strip():
            siemplify.LOGGER.info(f"Retrieving user information for email: {assignee_email}")
            user_info = cyware_manager.get_user_by_email(assignee_email)

            if not user_info:
                output_message = (
                    f"User with email '{assignee_email}' not found in Cyware Intel Exchange. "
                    f"Please verify the email address."
                )
                result_value = RESULT_VALUE_FALSE
                status = EXECUTION_STATE_FAILED
                return

            assignee_user_id = user_info.get("id")
            if not assignee_user_id:
                output_message = (
                    f"Unable to retrieve user ID for email '{assignee_email}'. "
                    f"User data may be incomplete."
                )
                result_value = RESULT_VALUE_FALSE
                status = EXECUTION_STATE_FAILED
                return

            siemplify.LOGGER.info(f"Found user: {user_info.get('email')} (ID: {assignee_user_id})")
        else:
            siemplify.LOGGER.info(
                "No assignee email provided. Task will be created without an assignee."
            )

        # Fetch indicator IDs from provided names via bulk IOC lookup
        siemplify.LOGGER.info("Fetching indicator IDs from provided names via bulk IOC lookup.")
        ioc_lookup = cyware_manager.lookup_iocs(ioc_values)
        missing_iocs = [value for value in ioc_values if value not in ioc_lookup]
        if missing_iocs:
            siemplify.LOGGER.info(
                f"Indicator(s) not found on Cyware Intel Exchange and will be skipped: "
                f"{', '.join(missing_iocs)}"
            )
        valid_iocs = [value for value in ioc_values if value in ioc_lookup]

        if not valid_iocs:
            output_message = NO_VALID_IOC_ERROR
            result_value = RESULT_VALUE_TRUE
            status = EXECUTION_STATE_COMPLETED
            return

        # Create tasks for each valid IOC
        task_responses = []
        successful_tasks = []
        failed_tasks = []

        for indicator_value in valid_iocs:
            indicator_id = ioc_lookup[indicator_value]

            try:
                siemplify.LOGGER.info(
                    f"Creating task for indicator '{indicator_value}' (ID: {indicator_id})"
                )
                task_params = {
                    "text": text,
                    "priority": priority,
                    "status": task_status,
                    "object_id": indicator_id,
                    "deadline": deadline_epoch,
                }
                if assignee_user_id:
                    task_params["assignee"] = assignee_user_id

                task_response = cyware_manager.create_task(**task_params)

                task_responses.append({
                    "indicator": indicator_value,
                    "indicator_id": indicator_id,
                    "task": task_response,
                })

                if task_response:
                    task_id = task_response.get("id", "N/A")
                    successful_tasks.append({
                        "indicator": indicator_value,
                        "indicator_id": indicator_id,
                        "task_id": task_id,
                    })
                    siemplify.LOGGER.info(
                        f"Successfully created task for IOC '{indicator_value}' "
                        f"(ID: {indicator_id}). Task ID: {task_id}"
                    )
                else:
                    failed_tasks.append(indicator_value)
                    siemplify.LOGGER.warning(
                        f"Create task API returned empty response for IOC '{indicator_value}' "
                        f"(ID: {indicator_id})."
                    )

            except Exception as inner_error:
                failed_tasks.append(indicator_value)
                siemplify.LOGGER.error(
                    f"Failed to create task for IOC '{indicator_value}' (ID: {indicator_id}). "
                    f"Error: {inner_error}"
                )
                siemplify.LOGGER.exception(inner_error)

        if task_responses:
            json_results = task_responses

        if successful_tasks:
            output_message = f"Successfully created tasks for {len(successful_tasks)} IOC(s). "
            if assignee_email and assignee_email.strip():
                output_message += f"Assignee: {assignee_email}. "
            output_message += f"Deadline: {deadline_days} day(s) from now."
            if missing_iocs:
                output_message += (
                    f"\nSkipped {len(missing_iocs)} IOC(s) not found on "
                    f"Cyware Intel Exchange: {', '.join(missing_iocs)}."
                )
            if failed_tasks:
                output_message += (
                    f" Failed to create tasks for {len(failed_tasks)} IOC(s): "
                    f"{', '.join(failed_tasks)}."
                )
            result_value = RESULT_VALUE_TRUE
        else:
            output_message = "Failed to create tasks for any IOC."
            if failed_tasks:
                output_message += f" Affected IOC(s): {', '.join(failed_tasks)}."
            result_value = RESULT_VALUE_FALSE
            status = EXECUTION_STATE_FAILED

    except CywareException as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(CREATE_TASK_FOR_IOCS_SCRIPT_NAME, e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    finally:
        siemplify.result.add_result_json(json_results)
        siemplify.LOGGER.info("----------------- Main - Finished -----------------")
        siemplify.LOGGER.info(f"Status: {status}")
        siemplify.LOGGER.info(f"result_value: {result_value}")
        siemplify.LOGGER.info(f"Output Message: {output_message}")
        siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
