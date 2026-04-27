from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.NetskopeManagerFactory import NetskopeManagerFactory
from ..core.exceptions import NetskopeAlreadyProcessedError
from TIPCommon import extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

INTEGRATION_NAME = "Netskope"
ALLOWFILE_SCRIPT_NAME = f"{INTEGRATION_NAME} - AllowFile"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ALLOWFILE_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Parameters
    use_v2_api = extract_action_param(
        siemplify,
        param_name="Use V2 API",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
    )
    file_id = extract_action_param(
        siemplify, param_name="File ID", is_mandatory=True, print_value=True
    )
    quarantine_profile_id = extract_action_param(
        siemplify,
        param_name="Quarantine Profile ID",
        is_mandatory=False,
        print_value=True,
    )

    if not use_v2_api and not quarantine_profile_id:
        raise ValueError("Quarantine Profile ID is mandatory for V1 API.")

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    siemplify.LOGGER.info("Starting to perform the action")
    status = EXECUTION_STATE_FAILED
    result_value = False

    try:
        netskope_manager = NetskopeManagerFactory.get_manager(
            siemplify, api_version="v2" if use_v2_api else "v1"
        )
        if use_v2_api:
            netskope_manager.allow_file(file_id)
        else:
            netskope_manager.allow_file(file_id, quarantine_profile_id)
        result_value = True
        status = EXECUTION_STATE_COMPLETED
        output_message = f"Successfully allowed file {file_id}"
        siemplify.LOGGER.info("Finished performing the action")

    except NetskopeAlreadyProcessedError as e:
        output_message = str(e)
        result_value = True
        status = EXECUTION_STATE_COMPLETED

    except Exception as e:

        output_message = f'Error executing action "AllowFile". Reason: {e}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
