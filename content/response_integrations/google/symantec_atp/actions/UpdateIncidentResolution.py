# coding=utf-8
from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.SymantecATPManager import (
    SymantecATPManager,
    SymantecATPTokenPermissionError,
    SymantecATPIncidentNotFoundError,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

# =====================================
#             CONSTANTS               #
# =====================================
SCRIPT_NAME = "SymantecATP_Update Incident Resolution"
INTEGRATION_NAME = "SymantecATP"

# Resolution Types
RESOLUTION_TYPES = {
    "INSUFFICIENT DATA": 0,
    "SECURITY RISK": 1,
    "FALSE POSITIVE": 2,
    "MANAGED EXTERNALLY": 3,
    "NOT SET": 4,
    "BENIGN": 5,
    "TEST": 6,
}


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    output_message = ""
    is_success = "true"
    status = EXECUTION_STATE_COMPLETED
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Integration Parameters
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    # Action Parameters
    incident_uuid = extract_action_param(
        siemplify, param_name="Incident UUID", is_mandatory=True
    )
    identifier_type = extract_action_param(
        siemplify,
        param_name="Resolution Status",
        is_mandatory=True,
        default_value="INSUFFICIENT DATA",
        input_type=str,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        atp_manager = SymantecATPManager(api_root, client_id, client_secret, verify_ssl)
        resolution_status = RESOLUTION_TYPES.get(identifier_type)

        atp_manager.update_incident_resolution(incident_uuid, resolution_status)
        output_message = f"Successfully updated resolution on the Symantec ATP incident with UUID {incident_uuid}"

    except SymantecATPIncidentNotFoundError as e:
        is_success = "false"
        output_message = (
            f"Symantec ATP Incident with UUID {incident_uuid} was not found."
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except SymantecATPTokenPermissionError as e:
        is_success = "false"
        output_message = "API token doesn’t have permissions to perform this action"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action Update Incident Resolution. Reason: {e}"
        )
        is_success = "false"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {is_success}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, is_success, status)


if __name__ == "__main__":
    main()
