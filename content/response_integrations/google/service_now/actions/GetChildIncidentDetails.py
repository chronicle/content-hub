from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.transformation import construct_csv

from ..core.constants import (
    CHILD_INCIDENTS_TABLE_NAME,
    DEFAULT_MAX_RECORDS_TO_RETURN,
    GET_CHILD_INCIDENT_DETAILS_SCRIPT_NAME,
    INTEGRATION_NAME,
)
from ..core.exceptions import ChildIncidentsNotExists, ServiceNowNotFoundException
from ..core.ServiceNowManager import DEFAULT_TABLE, ServiceNowManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_CHILD_INCIDENT_DETAILS_SCRIPT_NAME

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        print_value=False,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        print_value=False,
    )
    default_incident_table = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Incident Table",
        print_value=True,
        default_value=DEFAULT_TABLE,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        print_value=False,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        print_value=False,
    )
    refresh_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Refresh Token",
        print_value=False,
    )
    use_oauth = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Use Oauth Authentication",
        default_value=False,
        input_type=bool,
    )
    # Parameters
    number = extract_action_param(
        siemplify,
        param_name="Parent Incident Number",
        print_value=True,
        is_mandatory=True,
    )
    max_records = extract_action_param(
        siemplify,
        param_name="Max Child Incident To Return",
        print_value=True,
        is_mandatory=False,
        input_type=int,
        default_value=DEFAULT_MAX_RECORDS_TO_RETURN,
    )

    output_message = ""
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = ServiceNowManager(
            api_root=api_root,
            username=username,
            password=password,
            default_incident_table=default_incident_table,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            use_oauth=use_oauth,
        )
        incident = manager.get_incident(number=number)

        if int(incident.child_incidents) <= 0:
            raise ChildIncidentsNotExists

        # In existing incident case get the child incidents
        child_incidents = manager.get_child_incidents(
            sys_id=incident.sys_id, max_records=max_records
        )

        if not child_incidents:
            raise ChildIncidentsNotExists

        # Add data to table
        siemplify.result.add_data_table(
            title=CHILD_INCIDENTS_TABLE_NAME,
            data_table=construct_csv([
                child_incident.to_table() for child_incident in child_incidents
            ]),
        )
        # Add JSON result
        siemplify.result.add_result_json([
            child_incident.to_json() for child_incident in child_incidents
        ])
        output_message = (
            "Successfully retrieved information about child incidents related to the {} "
            "incident in ServiceNow.".format(number)
        )

    except ServiceNowNotFoundException as err:
        output_message = (
            "Action wasn't able to retrieve information about the child incidents in ServiceNow. "
            "Reason: incident {} was not found.".format(number)
        )
        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    except ChildIncidentsNotExists as err:
        output_message = "No child incidents were found."
        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    except Exception as err:
        output_message = (
            f"Error executing action '{GET_CHILD_INCIDENT_DETAILS_SCRIPT_NAME}'. Reason: {err}"
        )
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
