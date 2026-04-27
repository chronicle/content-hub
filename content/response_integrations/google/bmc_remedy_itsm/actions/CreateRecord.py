from __future__ import annotations
import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_configuration_param, extract_action_param

from ..core.BMCRemedyITSMManager import BMCRemedyITSMManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    CREATE_RECORD_SCRIPT_NAME,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_RECORD_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    record_type = extract_action_param(
        siemplify, param_name="Record Type", is_mandatory=True, print_value=True
    )
    record_payload = extract_action_param(
        siemplify, param_name="Record Payload", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result = False
    status = EXECUTION_STATE_COMPLETED
    manager = None
    output_message = ""

    try:
        try:
            record_payload = json.loads(record_payload) if record_payload else {}
        except Exception:
            raise Exception(
                'Invalid JSON payload provided in the parameter "Record Payload". Please check the '
                "structure."
            )

        manager = BMCRemedyITSMManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        record = manager.create_record(
            record_type=record_type, record_payload=record_payload
        )
        siemplify.result.add_result_json(record.to_json())

        result = True
        status = EXECUTION_STATE_COMPLETED
        output_message = (
            f"Successfully created {record_type} record in {INTEGRATION_DISPLAY_NAME}."
        )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {CREATE_RECORD_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action {CREATE_RECORD_SCRIPT_NAME}. Reason: {e}"
        )

    finally:
        try:
            if manager:
                siemplify.LOGGER.info(f"Logging out from {INTEGRATION_DISPLAY_NAME}..")
                manager.logout()
                siemplify.LOGGER.info(
                    f"Successfully logged out from {INTEGRATION_DISPLAY_NAME}"
                )
        except Exception as error:
            siemplify.LOGGER.error(f"Logging out failed. Error: {error}")
            siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
