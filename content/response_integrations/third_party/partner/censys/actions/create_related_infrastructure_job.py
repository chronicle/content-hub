from __future__ import annotations

import re

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.api_manager import APIManager
from ..core.censys_exceptions import CensysException
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    CREATE_RELATED_INFRA_JOB_SCRIPT_NAME,
    INVALID_CERTIFICATE_FORMAT_ERROR,
    INVALID_TARGET_TYPE_ERROR,
    INVALID_WEB_PROPERTY_FORMAT_ERROR,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
    TARGET_TYPE_CERTIFICATE,
    TARGET_TYPE_HOST,
    TARGET_TYPE_WEB_PROPERTY,
    TARGET_VALUE_REQUIRED_ERROR,
)
from ..core.utils import get_integration_params, validate_ip_address


def validate_create_job_params(target_type: str, target_value: str) -> None:
    """Validate parameters for creating a CensEye job.

    Args:
        target_type: Type of target (Host, Web Property, Certificate)
        target_value: The target value to validate

    Raises:
        ValueError: If validation fails
    """
    if not target_value or not target_value.strip():
        raise ValueError(TARGET_VALUE_REQUIRED_ERROR)

    target_value = target_value.strip()

    if target_type == TARGET_TYPE_HOST:
        validate_ip_address(target_value, "Target Value")

    elif target_type == TARGET_TYPE_WEB_PROPERTY:
        if ":" not in target_value:
            raise ValueError(INVALID_WEB_PROPERTY_FORMAT_ERROR)
        parts = target_value.split(":")
        if len(parts) != 2 or not parts[0]:
            raise ValueError(INVALID_WEB_PROPERTY_FORMAT_ERROR)
        try:
            port = int(parts[1])
            if port < 1 or port > 65535:
                raise ValueError(INVALID_WEB_PROPERTY_FORMAT_ERROR)
        except ValueError:
            raise ValueError(INVALID_WEB_PROPERTY_FORMAT_ERROR)

    elif target_type == TARGET_TYPE_CERTIFICATE:
        if not re.match(r"^[a-fA-F0-9]{64}$", target_value):
            raise ValueError(INVALID_CERTIFICATE_FORMAT_ERROR)

    else:
        raise ValueError(INVALID_TARGET_TYPE_ERROR.format(target_type))


@output_handler
def main():
    """Create a CensEye Related Infrastructure job.

    This action initiates a CensEye job to discover related infrastructure for a given
    target (host, web property, or certificate). The job runs asynchronously and returns
    a job ID that can be used to monitor status and retrieve results.

    Returns:
        None. Results are returned via siemplify.end() with:
            - output_message (str): Status message with job ID
            - result_value (bool): True if successful, False otherwise
            - status (str): Execution state (COMPLETED or FAILED)

    Raises:
        ValueError: If parameter validation fails
        CensysException: If API call fails
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_RELATED_INFRA_JOB_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_key, organization_id, verify_ssl = get_integration_params(siemplify)

    target_type = siemplify.extract_action_param(
        param_name="Target Type", input_type=str, is_mandatory=True
    )
    target_value = siemplify.extract_action_param(
        param_name="Target Value", input_type=str, is_mandatory=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""

    try:
        validate_create_job_params(target_type, target_value)

        censys_manager = APIManager(
            api_key,
            organization_id,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        siemplify.LOGGER.info(f"Creating CensEye job for {target_type}: {target_value}")

        response = censys_manager.create_censeye_job(
            target_type=target_type,
            target_value=target_value,
        )

        siemplify.result.add_result_json(response)

        result = response.get("result", {})
        job_id = result.get("job_id")
        state = result.get("state")
        create_time = result.get("create_time")

        if job_id:
            output_message = (
                f"Successfully created CensEye job for {target_type} '{target_value}'. "
                f"Job ID: {job_id}"
            )
            if state:
                output_message += f", State: {state}"
            if create_time:
                output_message += f", Created: {create_time}"

            siemplify.LOGGER.info(output_message)
        else:
            output_message = "CensEye job created but no job ID returned."
            siemplify.LOGGER.info(output_message)
            result_value = RESULT_VALUE_FALSE
            status = EXECUTION_STATE_FAILED

    except ValueError as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except (CensysException, Exception) as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            CREATE_RELATED_INFRA_JOB_SCRIPT_NAME, str(e)
        )
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
