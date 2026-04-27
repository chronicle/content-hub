# coding=utf-8
from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
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
SCRIPT_NAME = "SymantecATP_Get Incident Comments"
INTEGRATION_NAME = "SymantecATP"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    output_message = ""
    is_success = "true"
    json_results = []
    csv_table = []

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
    max_comments_to_return = extract_action_param(
        siemplify,
        param_name="Max Comments To Return",
        is_mandatory=False,
        default_value=20,
        input_type=int,
        print_value=True,
    )

    if max_comments_to_return > 1000:
        max_comments_to_return = 1000

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        atp_manager = SymantecATPManager(api_root, client_id, client_secret, verify_ssl)
        comments = atp_manager.get_comments_for_incident(
            incident_uuid, max_comments_to_return
        )

        for comment in comments:
            csv_table.append(comment.to_table())
            json_results.append(comment.to_json())

        if not comments:
            is_success = "false"
            siemplify.LOGGER.info(
                f"No comments were found for the Symantec ATP incident with UUID {incident_uuid}"
            )
            output_message += f"No comments were found for the Symantec ATP incident with UUID {incident_uuid}"
        else:
            siemplify.result.add_data_table(
                title=f"Symantec ATP Incident {incident_uuid} Comments",
                data_table=construct_csv(csv_table),
            )
            siemplify.result.add_result_json(json_results)
            siemplify.LOGGER.info(
                f"Successfully returned comments for Symantec ATP incident with UUID {incident_uuid}"
            )
            output_message += f"Successfully returned comments for Symantec ATP incident with UUID {incident_uuid}"

    except SymantecATPIncidentNotFoundError as e:
        is_success = "false"
        output_message = (
            f"Symantec ATP Incident with UUID {incident_uuid} was not found"
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
        output_message += f"Error executing action Get Incident Comments. Reason: {e}"
        is_success = "false"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {is_success}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, is_success, status)


if __name__ == "__main__":
    main()
