from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.Rapid7InsightIDRManager import Rapid7InsightIDRManager
from ..core.constants import PROVIDER_NAME, CREATE_SAVED_QUERY_SCRIPT_NAME, DEFAULT_DELIMITER
from ..core.Rapid7InsightIDRExceptions import BadRequestException


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_SAVED_QUERY_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="API Key", is_mandatory=True
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
    )

    name = extract_action_param(
        siemplify, param_name="Name", is_mandatory=True, print_value=True
    )
    statement = extract_action_param(
        siemplify, param_name="Statement", is_mandatory=True, print_value=True
    )
    time_frame = extract_action_param(
        siemplify,
        param_name="Time Frame",
        is_mandatory=True,
        input_type=int,
        print_value=True,
    )
    logs = extract_action_param(siemplify, param_name="Logs", print_value=True)
    log_names = (
        [log.strip() for log in logs.split(DEFAULT_DELIMITER) if log.strip()]
        if logs
        else []
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    try:
        manager = Rapid7InsightIDRManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        result = manager.create_saved_query(name, statement, time_frame, log_names)

        if result:
            siemplify.result.add_result_json(result.to_json())
            output_message = f"New {PROVIDER_NAME} saved query created: {result.id}"

    except BadRequestException as e:
        result_value = False
        output_message = f"Failed to create {PROVIDER_NAME} saved query. Error is: {e}"
    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {CREATE_SAVED_QUERY_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to connect to the {PROVIDER_NAME} service! Error is {e}"
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
