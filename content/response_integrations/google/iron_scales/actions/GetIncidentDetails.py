from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.IronScalesManager import IronScalesManager
from ..core.IronScalesExceptions import IronScalesNotFoundException
from ..core.IronScalesConstants import PROVIDER_NAME, GET_INCIDENT_DETAILS_NAME


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_INCIDENT_DETAILS_NAME
    siemplify.LOGGER.info("=" * 20 + " Main - Params Init " + "=" * 20)

    api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )

    api_token = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Token",
        is_mandatory=True,
        print_value=False,
    )

    company_id = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Company ID",
        is_mandatory=True,
        print_value=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    is_partner = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Is Partner",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    # Parameters
    incidents_ids = extract_action_param(
        siemplify, param_name="Incidents IDs", is_mandatory=True, print_value=True
    )

    siemplify.LOGGER.info("=" * 20 + " Main - Started " + "=" * 20)
    result_value = False
    output_messages = []
    status = EXECUTION_STATE_COMPLETED
    successful_incidents = []
    failed_incidents = []
    fetched_incidents = []

    try:
        manager = IronScalesManager(
            api_root=api_root,
            api_token=api_token,
            company_id=company_id,
            is_partner=is_partner,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        incidents_list = [
            inc.strip() for inc in incidents_ids.split(",") if inc.strip()
        ]

        for inc_id in incidents_list:
            try:
                incident_details = manager.get_incident_details(incident_id=inc_id)
                successful_incidents.append(inc_id)
                fetched_incidents.append(incident_details)
            except IronScalesNotFoundException as e:
                siemplify.LOGGER.error(e)
                failed_incidents.append(inc_id)

        if successful_incidents:
            output_messages.append(
                "Successfully fetched incidents details from IronScales. incident "
                "IDs: {}.".format(
                    "\n".join([inc_id for inc_id in successful_incidents])
                )
            )
            result_value = True
            siemplify.result.add_result_json(
                [incident.to_json() for incident in fetched_incidents]
            )

        if failed_incidents:
            output_messages.append(
                "Action wasn’t able to fetch incident details for incident IDs: {}. "
                "Reason: incident IDs weren’t found.".format(
                    "\n".join([inc_id for inc_id in failed_incidents])
                )
            )

        output_message = "\n".join(output_messages)

    except Exception as e:
        output_message = f'Error executing action "Get Incident Details". Reason: {e}'
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
