from __future__ import annotations
import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.validation import ParameterValidator
from TIPCommon.utils import is_empty_string_or_none

from google_cloud_iam.core.consts import (
    API_URL,
    INTEGRATION_IDENTIFIER,
    INTEGRATION_DISPLAY_NAME,
    CREATE_ROLE_SCRIPT_NAME,
)
from google_cloud_iam.core.exceptions import (
    GoogleCloudIAMRoleJSONError,
    GoogleCloudIAMRoleExistsError,
    GoogleCloudIAMRoleIDInvalidError,
)
from google_cloud_iam.core.GoogleCloudIAMManager import GoogleCloudIAMManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_IDENTIFIER} - {CREATE_ROLE_SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # Integration configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Root",
        print_value=True,
        default_value=API_URL,
    )
    account_type = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Account Type",
        print_value=True,
    )
    project_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Project ID",
        print_value=True,
    )
    quota_project_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Quota Project ID",
        print_value=True,
    )
    private_key_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Private Key ID",
        remove_whitespaces=False,
    )
    private_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Private Key",
        remove_whitespaces=False,
    )
    client_email = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Client Email",
        print_value=True,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Client ID",
        print_value=True,
    )
    auth_uri = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Auth URI",
        print_value=True,
    )
    token_uri = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Token URI",
        print_value=True,
    )
    auth_provider_x509_url = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Auth Provider X509 URL",
        print_value=True,
    )
    client_x509_url = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Client X509 URL",
        print_value=True,
    )
    service_account_json = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Service Account Json File Content",
        remove_whitespaces=False,
    )
    workload_identity_email = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Workload Identity Email",
        print_value=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )
    organization_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Organization ID",
        print_value=True,
    )

    # Action configuration
    target_project_id = extract_action_param(
        siemplify, param_name="Project ID", is_mandatory=False, print_value=True
    )
    role_id = extract_action_param(
        siemplify, param_name="Role ID", is_mandatory=True, print_value=True
    )
    role_definition_json = extract_action_param(
        siemplify, param_name="Role Definition", is_mandatory=True, print_value=True
    )
    role_definition_param = role_definition_json

    # Action results
    result_value = False
    status = EXECUTION_STATE_COMPLETED

    try:
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

        try:
            role_definition_json = json.loads(role_definition_json)
        except Exception as error:
            raise GoogleCloudIAMRoleJSONError(error)

        manager = GoogleCloudIAMManager(
            siemplify=siemplify,
            api_root=api_root,
            account_type=account_type,
            project_id=target_project_id or project_id,
            quota_project_id=quota_project_id,
            private_key_id=private_key_id,
            private_key=private_key,
            client_email=client_email,
            client_id=client_id,
            auth_uri=auth_uri,
            token_uri=token_uri,
            auth_provider_x509_url=auth_provider_x509_url,
            client_x509_cert_url=client_x509_url,
            organization_id=organization_id,
            service_account_json=service_account_json,
            verify_ssl=verify_ssl,
            workload_identity_email=workload_identity_email,
        )
        created_role = manager.create_resource_role(
            role_id=role_id, role_definition_json=role_definition_json
        )
        siemplify.result.add_result_json(created_role.to_json())
        output_message = (
            f"{INTEGRATION_DISPLAY_NAME} {role_id} was created successfully."
        )
        result_value = True

    except GoogleCloudIAMRoleIDInvalidError as error:
        output_message = f"{error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    except GoogleCloudIAMRoleExistsError as error:
        output_message = f"Provided role id {role_id} already exists."
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    except GoogleCloudIAMRoleJSONError as error:
        output_message = f"Provided role definition JSON document {role_definition_param} is not valid."
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    except Exception as error:
        output_message = (
            f'Error executing action "{CREATE_ROLE_SCRIPT_NAME}". Reason: {error}'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
