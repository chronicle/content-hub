from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from sentinel_one_v2.core.SentinelOneV2Factory import SentinelOneV2ManagerFactory
from sentinel_one_v2.core.constants import (
    UPDATE_INCIDENT_STATUS_SCRIPT_NAME,
    INTEGRATION_NAME,
    PRODUCT_NAME,
    INCIDENT_STATUS_MAPPING,
)
from sentinel_one_v2.core.utils import string_to_multi_value
from sentinel_one_v2.core.exceptions import SentinelOneV2NotFoundError


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_INCIDENT_STATUS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    threat_ids = extract_action_param(
        siemplify, param_name="Threat ID", is_mandatory=True, print_value=True
    )
    threat_ids = string_to_multi_value(threat_ids)
    incident_status = extract_action_param(
        siemplify, param_name="Status", is_mandatory=True, print_value=True
    )
    incident_status = INCIDENT_STATUS_MAPPING[incident_status]

    status = EXECUTION_STATE_COMPLETED
    result_value = True
    successful_threats = []
    failed_threats = []
    output_message = ""

    try:
        manager = SentinelOneV2ManagerFactory().get_manager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )
        for threat_id in threat_ids:
            try:
                threat = manager.get_threat_or_raise(threat_id)

                if threat.incident_status.lower() != incident_status.lower():
                    if manager.update_incident_status([threat_id], incident_status):
                        successful_threats.append(threat_id)
                    else:
                        failed_threats.append(threat_id)
                else:
                    siemplify.LOGGER.info(
                        f"Incident status of the threat {threat_id} is already equal to the "
                        f"status provided"
                    )
                    successful_threats.append(threat_id)
            except SentinelOneV2NotFoundError as e:
                failed_threats.append(threat_id)
                siemplify.LOGGER.error(e)

        if successful_threats:
            output_message += "Successfully updated incident status for the following threats in {}: \n{}".format(
                PRODUCT_NAME, "\n".join([threat for threat in successful_threats])
            )

        if failed_threats:
            output_message += "\nAction wasn't able to update incident status for the following threats in {}: \n{}".format(
                PRODUCT_NAME, "\n".join([threat for threat in failed_threats])
            )

        if not successful_threats:
            result_value = False
            output_message = "Action wasn't able to update incident status for the provided threats in SentinelOne."

    except Exception as e:
        output_message = f"Error executing action '{UPDATE_INCIDENT_STATUS_SCRIPT_NAME}'. Reason: {e}"
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
