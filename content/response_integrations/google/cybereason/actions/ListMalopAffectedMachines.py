from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, construct_csv
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.CybereasonManager import CybereasonManager
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import (
    INTEGRATION_NAME,
    LIST_MALOP_AFFECTED_MACHINES_SCRIPT_NAME,
    MACHINES_CASE_WALL_NAME,
)
from ..core.utils import validate_positive_integer
from soar_sdk.SiemplifyDataModel import EntityTypes


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_MALOP_AFFECTED_MACHINES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
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
        default_value=False,
        input_type=bool,
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate Base64",
    )

    malop_guid = extract_action_param(
        siemplify, param_name="Malop ID", is_mandatory=True, print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Results Limit",
        is_mandatory=True,
        input_type=int,
        print_value=True,
    )
    create_hostname_entity = extract_action_param(
        siemplify,
        param_name="Create Hostname Entity",
        input_type=bool,
        default_value=False,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    output_message = (
        f"Successfully retrieved affected machines for the malop with ID {malop_guid} "
        f"in {INTEGRATION_NAME}."
    )

    try:
        validate_positive_integer(limit)
        manager = CybereasonManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            ca_certificate_b64=ca_certificate,
            force_check_connectivity=True,
        )

        machines = manager.get_malop_machines_or_raise(
            malop_guid=malop_guid, limit=limit
        )

        result_value = len(machines)
        siemplify.result.add_data_table(
            MACHINES_CASE_WALL_NAME,
            construct_csv([machine.to_csv() for machine in machines]),
        )
        siemplify.result.add_result_json([machine.to_json() for machine in machines])

        if create_hostname_entity:
            for machine in machines:
                siemplify.add_entity_to_case(
                    entity_identifier=machine.element_name,
                    entity_type=EntityTypes.HOSTNAME,
                    is_internal=False,
                    is_suspicous=False,
                    is_enriched=False,
                    is_vulnerable=True,
                    properties={"is_new_entity": True},
                )
    except Exception as e:
        output_message = f"Error executing action {LIST_MALOP_AFFECTED_MACHINES_SCRIPT_NAME}. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = 0

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
