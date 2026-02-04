from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.constants import INTEGRATION_NAME, UPDATE_INCIDENT_SCRIPT_NAME
from ..core.exceptions import (
    InvalidParameterException,
    ServiceNowIncidentNotFoundException,
    ServiceNowNotFoundException,
)
from ..core.ServiceNowManager import DEFAULT_TABLE, ServiceNowManager
from ..core.UtilsManager import get_custom_fields_data


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_INCIDENT_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

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
    incident_number = extract_action_param(
        siemplify, param_name="Incident Number", print_value=True, is_mandatory=True
    )
    short_description = extract_action_param(
        siemplify, param_name="Short Description", print_value=True
    )
    impact = extract_action_param(siemplify, param_name="Impact", print_value=True)
    urgency = extract_action_param(siemplify, param_name="Urgency", print_value=True)
    category = extract_action_param(siemplify, param_name="Category", print_value=True)
    assignment_group = extract_action_param(
        siemplify, param_name="Assignment group ID", print_value=True
    )
    assigned_to = extract_action_param(siemplify, param_name="Assigned User ID", print_value=True)
    description = extract_action_param(siemplify, param_name="Description", print_value=True)
    incident_state = extract_action_param(siemplify, param_name="Incident State", print_value=True)
    custom_fields_str = extract_action_param(
        siemplify, param_name="Custom Fields", print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    status = EXECUTION_STATE_COMPLETED
    user_full_name = ""

    try:
        try:
            custom_fields_dict = get_custom_fields_data(
                custom_fields=custom_fields_str,
                logger=siemplify.LOGGER,
            )

        except ValueError as e:
            raise InvalidParameterException(
                "Invalid value was found in the 'Custom Fields' parameter. Please check the format."
            ) from e

        service_now_manager = ServiceNowManager(
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

        if assigned_to:
            try:
                user_data = service_now_manager.get_user_data(usernames=[assigned_to])
                user_full_name = vars(user_data[0])["raw_data"]["name"]

            except ServiceNowNotFoundException:
                user_full_name = assigned_to

            except IndexError as err:
                raise TypeError(
                    f"User '{assigned_to}' wasn't found in ServiceNow. Please check the spelling."
                ) from err

        incident, not_used_custom_fields = service_now_manager.update_incident(
            incident_number,
            short_description=short_description,
            impact=impact,
            urgency=urgency,
            category=category,
            assignment_group=assignment_group,
            assigned_to=user_full_name,
            description=description,
            incident_state=incident_state,
            custom_fields=custom_fields_dict,
        )

        output_message = f"Successfully updated incident with number {incident.number}."
        result_value = incident.number
        siemplify.result.add_result_json(incident.to_json())

        if not_used_custom_fields:
            output_message += f"The following fields were not processed, when updating a incident: {', '.join(not_used_custom_fields)}"

    except ServiceNowIncidentNotFoundException as e:
        output_message = f'Incident with number "{incident_number}" was not found'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except ServiceNowNotFoundException as e:
        output_message = str(e)
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = f"Error executing action {UPDATE_INCIDENT_SCRIPT_NAME}. Reason: {e}"
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
