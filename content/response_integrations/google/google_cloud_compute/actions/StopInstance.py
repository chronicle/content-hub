from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.validation import ParameterValidator
from TIPCommon.utils import is_empty_string_or_none

from google_cloud_compute.core.GoogleCloudComputeConstants import (
    INSTANCE_RESOURCE_NAME,
    INTEGRATION_NAME,
    API_URL,
)
from google_cloud_compute.core.GoogleCloudComputeExceptions import (
    GoogleCloudComputeInvalidInstanceID,
    GoogleCloudComputeInvalidZone,
    GoogleCloudComputeValidationError,
)
from google_cloud_compute.core.GoogleCloudComputeManager import GoogleCloudComputeManager
from google_cloud_compute.core.GoogleCloudComputeUtils import (
    extract_name_from_address,
    extract_instance_resource_path,
)


SCRIPT_NAME = "Stop Instance"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # Integration configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        print_value=True,
        default_value=API_URL
    )
    account_type = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Account Type",
        print_value=True,
    )
    project_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Project ID",
        print_value=True,
    )
    private_key_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Private Key ID",
        remove_whitespaces=False,
    )
    private_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Private Key",
        remove_whitespaces=False,
    )
    client_email = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Email",
        print_value=True,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        print_value=True,
    )
    auth_uri = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Auth URI",
        print_value=True,
    )
    token_uri = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Token URI",
        print_value=True,
    )
    auth_provider_x509_url = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Auth Provider X509 URL",
        print_value=True,
    )
    client_x509_url = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client X509 URL",
        print_value=True,
    )
    service_account_json = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Service Account Json File Content",
        remove_whitespaces=False,
    )
    workload_identity_email = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Workload Identity Email",
        print_value=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    # Action params
    resource_name = extract_action_param(
        siemplify, param_name="Resource Name", print_value=True
    )
    target_project_id = extract_action_param(
        siemplify,
        param_name="Project ID",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )
    instance_zone = extract_action_param(
        siemplify, param_name="Instance Zone", print_value=True
    )
    instance_id = extract_action_param(
        siemplify, param_name="Instance ID", print_value=True
    )

    result_value = True
    status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        if not (resource_name or (instance_zone and instance_id)):
            raise GoogleCloudComputeValidationError(
                "You should provide either 'Resource name' or "
                "'Instance Zone' and 'Instance ID' parameters"
            )

        param_validator = ParameterValidator(siemplify)
        if not is_empty_string_or_none(workload_identity_email):
            param_validator.validate_email(
                param_name="Workload Identity Email", email=workload_identity_email
            )
        if not is_empty_string_or_none(service_account_json):
            param_validator.validate_json(
                param_name="Service Account Json File Content",
                json_string=service_account_json,
                print_value=False,
            )

        manager = GoogleCloudComputeManager(
            api_root=api_root,
            account_type=account_type,
            project_id=target_project_id or project_id,
            private_key_id=private_key_id,
            private_key=private_key,
            client_email=client_email,
            client_id=client_id,
            auth_uri=auth_uri,
            token_uri=token_uri,
            auth_provider_x509_url=auth_provider_x509_url,
            client_x509_cert_url=client_x509_url,
            service_account_json=service_account_json,
            workload_identity_email=workload_identity_email,
            verify_ssl=verify_ssl,
        )

        resource_path = (
            extract_instance_resource_path(resource_name)
            if resource_name is not None
            else INSTANCE_RESOURCE_NAME.format(
                project_id=manager.project_id,
                zone=instance_zone,
                resource_id=instance_id,
            )
        )

        siemplify.LOGGER.info(f"Stopping instance: {resource_path}")
        operation_raw_data = manager.stop_instance(resource_path=resource_path)
        siemplify.LOGGER.info(f"Successfully stopped instance: {resource_path}")

        if operation_raw_data:
            operation_raw_data["zone"] = extract_name_from_address(
                operation_raw_data.get("zone", "")
            )

        siemplify.result.add_result_json(operation_raw_data)
        output_message = (
            f"{INTEGRATION_NAME} instance {resource_path} was stopped successfully."
        )

    except GoogleCloudComputeInvalidZone as error:
        output_message = "Provided instance zone is not valid."
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        result_value = False

    except GoogleCloudComputeInvalidInstanceID as error:
        output_message = "Provided instance id is not valid."
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        result_value = False

    except Exception as error:
        siemplify.LOGGER.error(f"Error executing action {SCRIPT_NAME} Reason: {error}")
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = f"Error executing action {SCRIPT_NAME} Reason: {error}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
