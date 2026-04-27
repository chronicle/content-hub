from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.MISPManager import MISPManager
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.constants import (
    INTEGRATION_NAME,
    CREATE_VTREPORT_OBJECT_SCRIPT_NAME,
    VTREPORT_TABLE_NAME,
)
from ..core.exceptions import MISPManagerEventIdNotFoundError


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_VTREPORT_OBJECT_SCRIPT_NAME
    status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Root"
    )
    api_token = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Key"
    )
    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Use SSL",
        default_value=False,
        input_type=bool,
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File - parsed into Base64 String",
    )
    # INIT ACTION PARAMETERS:
    event_id = extract_action_param(
        siemplify, param_name="Event ID", is_mandatory=True, print_value=True
    )
    permalink = extract_action_param(
        siemplify, param_name="Permalink", is_mandatory=True, print_value=True
    )
    comment = extract_action_param(siemplify, param_name="Comment", print_value=True)
    detection_ratio = extract_action_param(
        siemplify, param_name="Detection Ratio", print_value=True
    )
    community_score = extract_action_param(
        siemplify, param_name="Community Score", print_value=True
    )
    first_submission = extract_action_param(
        siemplify, param_name="First Submission", print_value=True
    )
    last_submission = extract_action_param(
        siemplify, param_name="Last Submission", print_value=True
    )
    id_type = "ID" if event_id.isdigit() else "UUID"

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result_value = True

    try:
        manager = MISPManager(api_root, api_token, use_ssl, ca_certificate)
        manager.get_event_by_id_or_raise(event_id)

        try:
            misp_obj = manager.add_virus_total_report_object(
                event_id,
                permalink,
                comment,
                detection_ratio,
                community_score,
                first_submission,
                last_submission,
            )

            siemplify.result.add_data_table(
                VTREPORT_TABLE_NAME.format(event_id),
                construct_csv(misp_obj.to_attributes_csv()),
            )
            siemplify.result.add_result_json(misp_obj.to_json())
            output_message = f"Successfully created new Virustotal-Report object for event with {id_type} {event_id} in {INTEGRATION_NAME}."
        except Exception as e:
            output_message = (
                "Action wasn’t able to created Virustotal-Report object for event with {} {} in {}. "
                "Reason: {}".format(
                    id_type, event_id, CREATE_VTREPORT_OBJECT_SCRIPT_NAME, e
                )
            )
            siemplify.LOGGER.error(output_message)
            siemplify.LOGGER.exception(e)
            result_value = False

    except Exception as e:
        output_message = (
            f"Error executing action  “{CREATE_VTREPORT_OBJECT_SCRIPT_NAME}“. Reason: "
        )
        output_message += (
            f"Event with {id_type} {event_id} was not found in {INTEGRATION_NAME}"
            if isinstance(e, MISPManagerEventIdNotFoundError)
            else str(e)
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
