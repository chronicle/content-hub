from __future__ import annotations
from collections import defaultdict

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    output_handler,
    unix_now,
    convert_unixtime_to_datetime,
    convert_dict_to_json_result_dict,
    construct_csv,
)
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.validation import ParameterValidator
from TIPCommon.utils import is_empty_string_or_none

from google_cloud_iam.core.consts import (
    API_URL,
    INTEGRATION_IDENTIFIER,
    INTEGRATION_DISPLAY_NAME,
    ENRICH_ENTITIES_SCRIPT_NAME,
)
from google_cloud_iam.core.exceptions import GoogleCloudIAMManagerError, GoogleCloudIAMValidationError
from google_cloud_iam.core.GoogleCloudIAMManager import GoogleCloudIAMManager
from google_cloud_iam.core.utils import extract_service_account_resource_path


SUPPORTED_ENTITIES = [EntityTypes.USER, EntityTypes.DEPLOYMENT]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_IDENTIFIER} - {ENRICH_ENTITIES_SCRIPT_NAME}"
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

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    # Action results
    result_value = False
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    json_results = defaultdict(dict)

    # Processing
    successful_entities = []
    failed_entities = []

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

        manager = GoogleCloudIAMManager(
            siemplify=siemplify,
            api_root=api_root,
            account_type=account_type,
            project_id=project_id,
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
        supported_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type in SUPPORTED_ENTITIES
        ]

        if not supported_entities:
            siemplify.LOGGER.info("No suitable entities were found")
            siemplify.end("No entities were enriched", False, EXECUTION_STATE_COMPLETED)

        for entity in supported_entities:
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break
            try:
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")

                entity_identifier = entity.identifier.strip().casefold()
                try:
                    sa_project, entity_identifier = (
                        extract_service_account_resource_path(entity_identifier)
                    )
                except GoogleCloudIAMValidationError:
                    sa_project = None

                try:
                    entity_service_account = manager.get_service_account(
                        sa_identifier=entity_identifier, sa_project=sa_project
                    )
                except GoogleCloudIAMManagerError:
                    siemplify.LOGGER.info(f"No matched service account")
                    failed_entities.append(entity)
                    continue

                entity_enrichment_table = {}
                siemplify.LOGGER.info(
                    f"Successfully matched service account for entity"
                )
                json_results[entity.identifier].update(entity_service_account.to_json())
                entity_enrichment_table.update(entity_service_account.to_enrichment())

                siemplify.result.add_data_table(
                    title=f"{entity.identifier} Enrichment Table",
                    data_table=construct_csv(
                        [
                            {"Key": k, "Value": v}
                            for k, v in entity_enrichment_table.items()
                            if v or isinstance(v, int)
                        ]
                    ),
                )
                entity.additional_properties.update(entity_enrichment_table)
                entity.is_enriched = True
                successful_entities.append(entity)
                siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")
            except Exception as error:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(error)

        if successful_entities:
            output_message += "Successfully enriched entities:\n   {}".format(
                "\n   ".join([entity.identifier for entity in successful_entities])
            )
            siemplify.update_entities(successful_entities)
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            result_value = True
            if failed_entities:
                output_message += "\n\nAction was not able to find a match in {} to enrich provided entities:\n   {}".format(
                    INTEGRATION_DISPLAY_NAME,
                    "\n   ".join([entity.identifier for entity in failed_entities]),
                )
        else:
            output_message += "No entities were enriched"

    except Exception as error:
        output_message = (
            f'Error executing action "{ENRICH_ENTITIES_SCRIPT_NAME}". Reason: {error}'
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
