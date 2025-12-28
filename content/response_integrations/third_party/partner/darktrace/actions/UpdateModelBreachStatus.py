from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_action_param, extract_configuration_param

from ..core.constants import (
    INTEGRATION_DISPLAY_NAME,
    INTEGRATION_NAME,
    MODEL_BREACH_STATUSES,
    UPDATE_MODEL_BREACH_STATUS_SCRIPT_NAME,
)
from ..core.DarktraceExceptions import (
    AlreadyAppliedException,
    ErrorInResponseException,
    NotFoundException,
)
from ..core.DarktraceManager import DarktraceManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_MODEL_BREACH_STATUS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
        print_value=True,
    )
    api_private_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Private Token",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    # Action parameters
    model_breach_status = extract_action_param(
        siemplify, param_name="Status", is_mandatory=True, print_value=True
    )
    model_breach_id = extract_action_param(
        siemplify, param_name="Model Breach ID", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result = False
    status = EXECUTION_STATE_FAILED

    try:
        manager = DarktraceManager(
            api_root=api_root,
            api_token=api_token,
            api_private_token=api_private_token,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        model_breach = manager.get_model_breach(model_breach_id)

        if (
            model_breach_status == MODEL_BREACH_STATUSES.get("acknowledged")
            and model_breach.acknowledged
        ) or (
            model_breach_status == MODEL_BREACH_STATUSES.get("unacknowledged")
            and not model_breach.acknowledged
        ):
            raise AlreadyAppliedException

        if model_breach_status == MODEL_BREACH_STATUSES.get("acknowledged"):
            manager.acknowledge_model_breach(model_breach_id)

        if model_breach_status == MODEL_BREACH_STATUSES.get("unacknowledged"):
            manager.unacknowledge_model_breach(model_breach_id)

        result = True
        status = EXECUTION_STATE_COMPLETED
        output_message = (
            f'Successfully updated status of the model breach "{model_breach_id}" to '
            f'"{model_breach_status}" in {INTEGRATION_DISPLAY_NAME}.'
        )

    except AlreadyAppliedException:
        result = True
        status = EXECUTION_STATE_COMPLETED
        output_message = (
            f'Model breach "{model_breach_id}" already has status "{model_breach_status}" '
            f"in {INTEGRATION_DISPLAY_NAME}. "
        )
    except ErrorInResponseException:
        output_message = (
            f'Error executing action "{UPDATE_MODEL_BREACH_STATUS_SCRIPT_NAME}". Reason: model '
            f"breach"
            f" \"{model_breach_id}\" wasn't found in {INTEGRATION_DISPLAY_NAME}.'"
        )
    except NotFoundException:
        output_message = (
            f'Error executing action "{UPDATE_MODEL_BREACH_STATUS_SCRIPT_NAME}". Reason: model '
            f"breach"
            f" \"{model_breach_id}\" wasn't found in {INTEGRATION_DISPLAY_NAME}.'"
        )
    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {UPDATE_MODEL_BREACH_STATUS_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        output_message = (
            f"Error executing action {UPDATE_MODEL_BREACH_STATUS_SCRIPT_NAME}. Reason: {e}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
