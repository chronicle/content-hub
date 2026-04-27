from __future__ import annotations
from ..core.Rapid7InsightIDRExceptions import NotFoundException
from ..core.Rapid7InsightIDRManager import Rapid7InsightIDRManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import (
    UPDATE_INVESTIGATION_SCRIPT_NAME,
    PROVIDER_NAME,
    STATUS_MAPPING,
    DISPOSITION_MAPPING,
)


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_INVESTIGATION_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Key",
        is_mandatory=True,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
    )

    investigation_id = extract_action_param(
        siemplify, param_name="Investigation ID", is_mandatory=True, print_value=True
    )
    investigation_status = extract_action_param(
        siemplify, param_name="Status", is_mandatory=False, print_value=True
    )
    disposition = extract_action_param(
        siemplify, param_name="Disposition", is_mandatory=False, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result_value = True
    output_message = f"Successfully updated investigation with ID {investigation_id} in Rapid7 InsightIDR"
    status = EXECUTION_STATE_COMPLETED

    if not (investigation_status or disposition):
        raise Exception(
            'Error executing action "Update Investigation".\n'
            'Reason: at least one of the  "Status" or "Disposition" parameters should have a value.'
        )

    investigation_status = STATUS_MAPPING.get(investigation_status)
    disposition = DISPOSITION_MAPPING.get(disposition)

    try:
        manager = Rapid7InsightIDRManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )
        result = manager.update_investigation(
            investigation_id, status=investigation_status, disposition=disposition
        )

        if result:
            siemplify.result.add_result_json(result.to_json())

    except NotFoundException as not_found_exception:
        siemplify.LOGGER.error(not_found_exception)
        result_value = False
        output_message = (
            f'Error executing action "Update Investigation".\n'
            f"Reason: investigation with ID {investigation_id} wasn’t found in Rapid7 InsightIDR.\n"
            f"Please check the spelling."
        )
        status = EXECUTION_STATE_FAILED
    except Exception as critical_error:
        siemplify.LOGGER.exception(critical_error)
        result_value = False
        output_message = (
            f'Error executing action "Update Investigation". Reason: {critical_error}'
        )
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
