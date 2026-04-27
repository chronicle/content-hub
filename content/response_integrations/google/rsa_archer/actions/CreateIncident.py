from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.RSAArcherManager import (
    RSAArcherManager,
    InvalidArgumentsError,
    NotFoundApplicationError,
    DEFAULT_APP_NAME,
)
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
import json

PROVIDER_NAME = "RSAArcher"
SCRIPT_NAME = "RSAArcher - CreateIncident"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration
    server_address = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Api Root",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    username = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    password = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Password",
        is_mandatory=True,
        input_type=str,
    )

    instance_name = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Instance Name",
        is_mandatory=True,
        print_value=True,
        input_type=str,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        print_value=True,
        input_type=bool,
    )

    # Parameters
    title = extract_action_param(
        siemplify,
        param_name="Incident Summary",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )

    description = extract_action_param(
        siemplify,
        param_name="Incident Details",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )

    owner = extract_action_param(
        siemplify,
        param_name="Incident Owner",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )

    status = extract_action_param(
        siemplify,
        param_name="Incident Status",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )

    priority = extract_action_param(
        siemplify,
        param_name="Priority",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )

    category = extract_action_param(
        siemplify,
        param_name="Category",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )

    custom_fields = extract_action_param(
        siemplify,
        param_name="Custom Fields",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )

    application_name = extract_action_param(
        siemplify,
        param_name="Application Name",
        is_mandatory=False,
        print_value=True,
        input_type=str,
        default_value=DEFAULT_APP_NAME,
    )

    mapping_file = extract_action_param(
        siemplify,
        param_name="Custom Mapping File",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )

    remote_file = extract_action_param(
        siemplify,
        param_name="Remote File",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result_value = None
    result_status = EXECUTION_STATE_FAILED

    try:
        archer_manager = RSAArcherManager(
            server_address,
            username,
            password,
            instance_name,
            verify_ssl,
            siemplify.LOGGER,
            siemplify,
        )

        custom_fields_dict = json.loads(custom_fields) if custom_fields else {}

        content_id, alias = archer_manager.create_incident(
            title=title,
            description=description,
            owner=owner,
            status=status,
            priority=priority,
            category=category,
            custom_fields=custom_fields_dict,
            app_name=application_name,
            map_file_path=mapping_file,
            remote_file=remote_file,
        )
        incident_details = archer_manager.get_incident_by_id(
            incident_id=content_id, alias=alias, check_content=False
        )
        siemplify.result.add_result_json(incident_details.to_json())
        output_message = f"Successfully created incident. Content ID: {content_id}"
        result_value = content_id
        result_status = EXECUTION_STATE_COMPLETED

    except NotFoundApplicationError as e:
        output_message = str(e)
        siemplify.LOGGER.error(output_message)

    except InvalidArgumentsError as e:
        output_message = f"Action wasn't able to create a new incident. Reason: {e}"
        siemplify.LOGGER.error(output_message)

    except Exception as e:
        output_message = f"Error executing action Create Incident. Reason: {e}"
        siemplify.LOGGER.error(f"Error executing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {result_status}\n  content_ID: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, result_status)


if __name__ == "__main__":
    main()
