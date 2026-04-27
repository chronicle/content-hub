from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import construct_csv

from ..core.BMCRemedyITSMManager import BMCRemedyITSMManager
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    GET_INCIDENT_DETAILS_SCRIPT_NAME,
    DEFAULT_WORK_NOTES_LIMIT,
)
from ..core.UtilsManager import convert_comma_separated_to_list

TABLE_NAME = "Incident Details"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_INCIDENT_DETAILS_SCRIPT_NAME
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

    # action parameters
    incident_ids = extract_action_param(
        siemplify, param_name="Incident IDs", is_mandatory=True, print_value=True
    )
    fields_to_return = extract_action_param(
        siemplify, param_name="Fields To Return", print_value=True
    )
    fetch_work_notes = extract_action_param(
        siemplify,
        param_name="Fetch Work Notes",
        default_value=True,
        print_value=True,
        input_type=bool,
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Work Notes To Return",
        input_type=int,
        default_value=DEFAULT_WORK_NOTES_LIMIT,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result = True
    status = EXECUTION_STATE_COMPLETED
    incident_ids = list(set(convert_comma_separated_to_list(incident_ids)))
    manager = None
    output_message = ""

    try:
        if limit < 1:
            raise Exception(
                f'Invalid value was provided for "Max Work Notes To Return": {limit}. '
                f"Positive number should be provided."
            )

        manager = BMCRemedyITSMManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        incidents_details = manager.get_incidents_details(
            incident_ids=incident_ids, fields=fields_to_return
        )

        if fetch_work_notes:
            for incident in incidents_details:
                incident.worknotes = manager.get_worknotes(
                    incident.incident_number, limit
                )

        failed_incidents = [
            inc_id
            for inc_id in incident_ids
            if inc_id
            not in [incident.incident_number for incident in incidents_details]
        ]

        if incidents_details:
            siemplify.result.add_result_json(
                [incident.to_json() for incident in incidents_details]
            )
            siemplify.result.add_data_table(
                TABLE_NAME,
                construct_csv([incident.to_table() for incident in incidents_details]),
            )
            for inc in incidents_details:
                siemplify.result.add_data_table(
                    f"Incident {inc.incident_number} Worknotes",
                    construct_csv([note.to_table() for note in inc.worknotes]),
                )
            output_message = (
                f"Successfully returned details regarding incidents in {INTEGRATION_DISPLAY_NAME} "
                f"for the following ids: {', '.join([incident.incident_number for incident in incidents_details])}.\n"
            )

            if failed_incidents:
                output_message += (
                    f"Action wasn't able to find details regarding incidents in {INTEGRATION_DISPLAY_NAME} "
                    f"for the following ids: {', '.join(failed_incidents)}.\n"
                )
        else:
            result = False
            output_message = f"No incidents were found."

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {GET_INCIDENT_DETAILS_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action {GET_INCIDENT_DETAILS_SCRIPT_NAME}. Reason: {e}"
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
