from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    unix_now,
    convert_unixtime_to_datetime,
    output_handler,
    convert_dict_to_json_result_dict,
)
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from ..core.CybereasonManager import CybereasonManager, CybereasonManagerNotFoundError
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    add_prefix_to_dict,
    flat_dict_to_csv,
)
from ..core.constants import (
    INTEGRATION_NAME,
    ENRICH_ENTITIES_SCRIPT_NAME,
    SUPPORTED_FILE_HASH_TYPES,
    SUSPICIOUS_TYPES,
)
from ..core.utils import get_entity_original_identifier, get_domain_from_entity, get_hash_type

SUPPORTED_ENTITY_TYPES = [
    EntityTypes.HOSTNAME,
    EntityTypes.ADDRESS,
    EntityTypes.URL,
    EntityTypes.FILEHASH,
]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_ENTITIES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

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
    create_insights = extract_action_param(
        siemplify,
        param_name="Create Insights",
        default_value=True,
        print_value=True,
        input_type=bool,
    )
    only_malicious_entity_insights = extract_action_param(
        siemplify,
        param_name="Only Malicious Entity Insight",
        default_value=True,
        print_value=True,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    (
        successful_entities,
        suspicious_entities,
        failed_entities,
        csv_output,
        json_results,
    ) = ([], [], [], [], {})
    result_value = True
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        manager = CybereasonManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            ca_certificate_b64=ca_certificate,
            logger=siemplify.LOGGER,
            force_check_connectivity=True,
        )

        for entity in suitable_entities:
            entity_identifier = get_entity_original_identifier(entity)

            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline "
                    f"({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) "
                    f"has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            try:

                siemplify.LOGGER.info(f"Started processing entity: {entity_identifier}")
                siemplify.LOGGER.info(f"Fetching machine guid for {entity_identifier}")
                if entity.entity_type == EntityTypes.HOSTNAME:
                    try:
                        machine_guid = manager.get_machine_guid_by_name_or_fqdn(
                            entity_identifier
                        )
                    except CybereasonManagerNotFoundError as e:
                        siemplify.LOGGER.info(str(e))
                        siemplify.LOGGER.info(f"Skipping entity {entity_identifier}")
                        failed_entities.append(entity_identifier)
                        continue

                    siemplify.LOGGER.info(f"Found GUID: {machine_guid}")
                    siemplify.LOGGER.info(
                        f"Fetching information for machine {entity_identifier}"
                    )

                    entity_info = manager.get_machine(machine_guid)
                    enrichment_table = entity_info.as_enrichment_data()
                    entity.additional_properties.update(
                        add_prefix_to_dict(enrichment_table, INTEGRATION_NAME)
                    )
                    csv_output = enrichment_table
                    json_results[entity_identifier] = entity_info.to_json()
                    entity.is_enriched = True
                    if entity_info.is_malicious:
                        entity.is_suspicious = True
                    successful_entities.append(entity)
                    if create_insights:
                        siemplify.add_entity_insight(entity, entity_info.to_insight())
                    siemplify.LOGGER.info(
                        f"Finished processing entity {entity_identifier}"
                    )
                else:
                    if entity.entity_type == EntityTypes.FILEHASH:
                        hash_type = get_hash_type(entity_identifier)
                        if hash_type not in SUPPORTED_FILE_HASH_TYPES:
                            siemplify.LOGGER.info(
                                f"Hash {entity_identifier} is not supported. Supported types are MD5, SHA1. Skipping"
                            )
                            continue
                    entity_identifier_for_api = (
                        entity_identifier
                        if entity.entity_type != EntityTypes.URL
                        else get_domain_from_entity(entity_identifier)
                    )
                    entity_details = manager.get_entity_details(
                        entity_identifier_for_api, entity_type=entity.entity_type
                    )
                    if entity_details:
                        data = entity_details.to_json()
                        successful_entities.append(entity)
                        if entity_details.type in SUSPICIOUS_TYPES:
                            entity.is_suspicious = True
                            suspicious_entities.append(entity_identifier)
                        if entity.entity_type == EntityTypes.FILEHASH:
                            files = manager.get_files(file_hash=entity_identifier)
                            owner_machine = []
                            if files:
                                data.update({"additional_data": []})
                                for file in files:
                                    data["additional_data"].append(file.to_json())
                                for file in files:
                                    owner_machine.append(file.owner_machine)
                            files.append(entity_details)
                            json_results[entity_identifier] = data
                            enrichment_table = files[0].as_enrichment_data(
                                type=entity_details.type,
                                owner_machine=set(owner_machine),
                            )
                            entity.additional_properties.update(
                                add_prefix_to_dict(enrichment_table, INTEGRATION_NAME)
                            )
                            csv_output = enrichment_table
                            if create_insights:
                                if (
                                    not only_malicious_entity_insights
                                    or only_malicious_entity_insights
                                    and entity_identifier in suspicious_entities
                                ):
                                    siemplify.add_entity_insight(
                                        entity,
                                        files[0].to_insight(
                                            type=entity_details.type,
                                            owner_machine=set(owner_machine),
                                        ),
                                    )
                        else:
                            if create_insights:
                                if (
                                    not only_malicious_entity_insights
                                    or only_malicious_entity_insights
                                    and entity_identifier in suspicious_entities
                                ):
                                    siemplify.add_entity_insight(
                                        entity, entity_details.to_insight()
                                    )
                            enrichment_table = entity_details.as_enrichment_data()
                            entity.additional_properties.update(
                                add_prefix_to_dict(enrichment_table, INTEGRATION_NAME)
                            )
                            csv_output = enrichment_table
                            json_results[entity_identifier] = entity_details.to_json()
                        entity.is_enriched = True
                    else:
                        failed_entities.append(entity_identifier)
                if csv_output:
                    siemplify.result.add_data_table(
                        entity_identifier, flat_dict_to_csv(csv_output)
                    )
            except Exception as e:
                failed_entities.append(entity_identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity_identifier}"
                )
                siemplify.LOGGER.exception(e)
                raise
        if successful_entities:
            output_message = (
                f"Successfully enriched the following entities in {INTEGRATION_NAME}: "
                f'{", ".join([get_entity_original_identifier(entity) for entity in successful_entities])}\n'
            )
            siemplify.update_entities(successful_entities)
            if failed_entities:
                output_message += (
                    f"Action wasn't able to enrich the following entities in {INTEGRATION_NAME}: "
                    f'{", ".join(failed_entities)}\n'
                )
        else:
            output_message = "None of the entities were enriched."
            result_value = False
        if json_results:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
    except Exception as e:
        output_message = (
            f'Error executing action "{ENRICH_ENTITIES_SCRIPT_NAME}". Reason: {e}'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        raise
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
