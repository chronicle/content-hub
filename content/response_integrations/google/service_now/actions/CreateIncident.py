from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.constants import CREATE_INCIDENT_SCRIPT_NAME, INTEGRATION_NAME, TICKET_ID
from ..core.exceptions import (
    InvalidParameterException,
    ServiceNowNotFoundException,
    ServiceNowRecordNotFoundException,
)
from ..core.ServiceNowManager import DEFAULT_TABLE, ServiceNowManager
from ..core.UtilsManager import get_custom_fields_data


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_INCIDENT_SCRIPT_NAME

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

    short_description = extract_action_param(
        siemplify, param_name="Short Description", print_value=True, is_mandatory=True
    )
    impact = extract_action_param(
        siemplify, param_name="Impact", print_value=True, is_mandatory=True
    )
    urgency = extract_action_param(
        siemplify, param_name="Urgency", print_value=True, is_mandatory=True
    )
    category = extract_action_param(siemplify, param_name="Category", print_value=True)
    assignment_group = extract_action_param(
        siemplify, param_name="Assignment group ID", print_value=True
    )
    assigned_to = extract_action_param(siemplify, param_name="Assigned User ID", print_value=True)
    description = extract_action_param(siemplify, param_name="Description", print_value=True)
    custom_fields_str = extract_action_param(
        siemplify, param_name="Custom Fields", print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    status = EXECUTION_STATE_COMPLETED

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
        # The "Assigned User ID" parameter actually takes user Full Name instead of User ID
        if assigned_to:
            user_error_msg = f'Unable to find user "{assigned_to}"'
            try:
                user_data = service_now_manager.get_user_data(usernames=[assigned_to])
            except ServiceNowRecordNotFoundException as e:
                raise ServiceNowNotFoundException(user_error_msg) from e

            if not user_data:
                raise ServiceNowNotFoundException(user_error_msg)

            assigned_to = user_data[0].name

        incident, not_used_custom_fields = service_now_manager.create_ticket(
            short_description=short_description,
            impact=impact,
            urgency=urgency,
            category=category,
            assignment_group=assignment_group,
            assigned_to=assigned_to,
            description=description,
            custom_fields=custom_fields_dict,
        )

        if incident.is_empty():
            output_message = "Failed to create ServiceNow incident."

        else:
            siemplify.add_tag(INTEGRATION_NAME)
            siemplify.set_alert_context_property(TICKET_ID, incident.number)
            output_message = f"Successfully created incident with number {incident.number}."
            result_value = incident.number
            if not_used_custom_fields:
                output_message += f"The following fields were not processed, when creating an incident: {', '.join(not_used_custom_fields)}"
            siemplify.result.add_result_json(incident.to_json())

    except Exception as e:
        output_message = f"Error executing action {CREATE_INCIDENT_SCRIPT_NAME}. Reason: {e}"
        result_value = False
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
