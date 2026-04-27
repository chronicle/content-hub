from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.IronScalesManager import IronScalesManager
from ..core.IronScalesExceptions import IronScalesNotFoundException
from ..core.IronScalesConstants import (
    PROVIDER_NAME,
    CLASSIFY_INCIDENT_NAME,
    DEFAULT_CLASSIFICATION_VALUE,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CLASSIFY_INCIDENT_NAME
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
    new_classification = extract_action_param(
        siemplify,
        param_name="New Classification",
        is_mandatory=True,
        default_value=DEFAULT_CLASSIFICATION_VALUE,
        print_value=True,
    )
    user_email = extract_action_param(
        siemplify,
        param_name="Classifying User Email",
        is_mandatory=True,
        print_value=True,
    )

    siemplify.LOGGER.info("=" * 20 + " Main - Started " + "=" * 20)
    result_value = False
    output_messages = []
    status = EXECUTION_STATE_COMPLETED
    successful_incidents = []
    failed_incidents = []

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
                if incident_details:
                    try:
                        manager.classify_incident(
                            incident_id=inc_id,
                            new_classification=new_classification,
                            old_classification=incident_details.classification,
                            user_email=user_email,
                        )
                        successful_incidents.append(inc_id)
                    except:
                        failed_incidents.append(inc_id)
                else:
                    failed_incidents.append(inc_id)
            except IronScalesNotFoundException as e:
                siemplify.LOGGER.error(e)
                failed_incidents.append(inc_id)

        if successful_incidents:
            output_messages.append(
                "Successfully classified incidents to {}. Incident IDs: {}.".format(
                    new_classification,
                    "\n".join([inc_id for inc_id in successful_incidents]),
                )
            )
            result_value = True

        if failed_incidents:
            output_messages.append(
                "Couldn’t classify the following incident IDs: {}.".format(
                    "\n".join([inc_id for inc_id in failed_incidents])
                )
            )

        output_message = "\n".join(output_messages)

    except Exception as e:
        output_message = f'Error executing action "Classify Incident". Reason: {e}'
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
