from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.validation import ParameterValidator
from TIPCommon.utils import is_empty_string_or_none

from google_cloud_compute.core.GoogleCloudComputeConstants import (
    INSTANCE_RESOURCE_NAME,
    INTEGRATION_NAME,
    ADD_LABELS_TO_INSTANCE_SCRIPT_NAME,
    API_URL,
)
from google_cloud_compute.core.GoogleCloudComputeExceptions import (
    GoogleCloudComputeInvalidZone,
    GoogleCloudComputeInvalidInstanceID,
    GoogleCloudComputeLabelsValidationError,
    GoogleCloudComputeResourceNameValidationError,
    GoogleCloudComputeValidationError,
)
from google_cloud_compute.core.GoogleCloudComputeManager import GoogleCloudComputeManager
from google_cloud_compute.core.GoogleCloudComputeUtils import (
    extract_instance_resource_path,
    load_dict_from_csv_kv_list,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {ADD_LABELS_TO_INSTANCE_SCRIPT_NAME}"
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
    instance_labels = extract_action_param(
        siemplify, param_name="Instance Labels", is_mandatory=True, print_value=True
    )
    instance_labels_param = instance_labels
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = False
    output_message = ""

    try:
        if not (resource_name or (instance_zone and instance_id)):
            raise GoogleCloudComputeResourceNameValidationError(
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

        instance_labels = load_dict_from_csv_kv_list(
            kv_csv=instance_labels, param_name="Instance Labels"
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
        instance_data = manager.get_instance(resource_path=resource_path)

        duplicated_label_keys = [
            label for label in instance_data.labels if label in instance_labels
        ]
        keys_to_update = [
            label for label in instance_labels if label not in duplicated_label_keys
        ]

        if keys_to_update:
            instance_data.labels.update(
                {k: v for k, v in instance_labels.items() if k in keys_to_update}
            )
            updated_instance = manager.set_labels_to_instance(
                resource_path=resource_path,
                labels=instance_data.labels,
                label_fingerprint=instance_data.label_fingerprint,
            )
            siemplify.result.add_result_json(updated_instance.to_json())
            result_value = True
            labels_str = ",  ".join(
                ":".join([key, instance_labels[key]]) for key in keys_to_update
            )
            output_message += (
                f"Labels: {labels_str} were successfully added to "
                f"{INTEGRATION_NAME} instance {resource_path}\n\n"
            )

        if duplicated_label_keys:
            duplicated_labels_str = ",  ".join(
                ":".join([key, instance_labels[key]]) for key in duplicated_label_keys
            )
            output_message += (
                "Labels were not added because provided labels: "
                f"{duplicated_labels_str} have keys that already exist for the "
                f"{INTEGRATION_NAME} instance {resource_path}"
            )

    except (
        GoogleCloudComputeValidationError,
        GoogleCloudComputeLabelsValidationError,
    ) as e:
        output_message = (
            f"Provided instance labels: {instance_labels_param} "
            f"are not in a valid format."
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except GoogleCloudComputeInvalidInstanceID as e:
        output_message = "Provided instance id is not valid."
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except GoogleCloudComputeInvalidZone as e:
        siemplify.LOGGER.error("Provided instance zone is not valid.")
        siemplify.LOGGER.exception(e)
        output_message = "Provided instance zone is not valid."

    except Exception as e:
        output_message = (
            f'Error executing action "{ADD_LABELS_TO_INSTANCE_SCRIPT_NAME}" '
            f"Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
