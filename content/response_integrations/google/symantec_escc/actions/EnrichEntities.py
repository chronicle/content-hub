from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.Siemplify import InsightSeverity, InsightType
from symantec_escc.core.SymantecESCCManager import SymantecESCCManager
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    dict_to_flat,
    flat_dict_to_csv,
)
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyDataModel import EntityTypes
from symantec_escc.core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_IDENTIFIER,
    ENRICH_ENTITIES_ACTION,
    BAD_REPUTATION,
)

SUPPORTED_ENTITY_TYPES = [EntityTypes.URL, EntityTypes.FILEHASH, EntityTypes.ADDRESS]
ENRICHMENT_PREFIX = "SESC"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_ENTITIES_ACTION
    siemplify.LOGGER.info("================= Main - Param Init =================")

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        print_value=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    device_group = extract_action_param(
        siemplify, param_name="Device Group", is_mandatory=True, print_value=True
    )
    create_endpoint_insight = extract_action_param(
        siemplify,
        param_name="Create Endpoint Insight",
        print_value=True,
        input_type=bool,
    )
    create_ioc_insight = extract_action_param(
        siemplify, param_name="Create IOC Insight", print_value=True, input_type=bool
    )

    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]
    hostname_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.HOSTNAME
    ]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    json_results = {}
    successful_entities, failed_entities = [], []
    successful_endpoints, successful_iocs = [], []

    try:
        manager = SymantecESCCManager(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
        )

        device_groups = manager.get_device_groups()
        if device_group not in [dev_group.name for dev_group in device_groups]:
            raise Exception(
                "The provided device group wasn't found. Please check the spelling."
            )

        device_group = next(
            dev_gr for dev_gr in device_groups if dev_gr.name == device_group
        )
        devices = manager.get_devices_in_group(group_id=device_group.id)
        for entity in hostname_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
            device = next(
                (dev for dev in devices if dev.name == entity.identifier), None
            )
            if device:
                device_details = manager.get_device_by_id(device_id=device.id)
                json_results[entity.identifier] = device_details.to_json()
                entity.additional_properties.update(
                    device_details.to_enrichment_data(prefix=ENRICHMENT_PREFIX)
                )
                successful_entities.append(entity)
                successful_endpoints.append(
                    device_details.to_insight(identifier=entity.identifier)
                )
                entity.is_enriched = True

                siemplify.result.add_entity_table(
                    f"{entity.identifier}",
                    flat_dict_to_csv(dict_to_flat(device_details.to_csv())),
                )
                siemplify.result.add_entity_link(
                    f"Link to device {entity.identifier} details", device_details.link
                )
            else:
                failed_entities.append(entity)

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

        for entity in suitable_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
            if (
                entity.entity_type == EntityTypes.FILEHASH
                and len(entity.identifier) != 64
            ):
                siemplify.LOGGER.info(
                    f"Hash {entity.identifier} is not of type sha256. Skipping."
                )
                continue

            entity_details = manager.get_full_entity_details(entity)
            if entity_details:
                json_results[entity.identifier] = entity_details.to_json()
                entity.additional_properties.update(
                    entity_details.to_enrichment_data(prefix=ENRICHMENT_PREFIX)
                )
                successful_entities.append(entity)
                successful_iocs.append(
                    entity_details.to_insight(identifier=entity.identifier)
                )
                entity.is_enriched = True
                if entity_details.reputation == BAD_REPUTATION:
                    entity.is_suspicious = True

                siemplify.result.add_entity_table(
                    f"{entity.identifier}",
                    flat_dict_to_csv(dict_to_flat(entity_details.to_csv())),
                )
            else:
                failed_entities.append(entity)

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

        if successful_entities:
            output_message = (
                f"Successfully enriched the following entities using {INTEGRATION_NAME}: "
                f"{', '.join([entity.identifier for entity in successful_entities])}\n"
            )
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            siemplify.update_entities(successful_entities)

            if successful_endpoints and create_endpoint_insight:
                siemplify.create_case_insight(
                    triggered_by=INTEGRATION_IDENTIFIER,
                    title="Enriched Endpoints",
                    content="".join(successful_endpoints),
                    entity_identifier="",
                    severity=InsightSeverity.INFO,
                    insight_type=InsightType.General,
                )

            if successful_iocs and create_ioc_insight:
                siemplify.create_case_insight(
                    triggered_by=INTEGRATION_IDENTIFIER,
                    title="Enriched IOCs",
                    content="".join(successful_iocs),
                    entity_identifier="",
                    severity=InsightSeverity.INFO,
                    insight_type=InsightType.General,
                )

            if failed_entities:
                output_message += (
                    f"Action wasn't able to enrich the following entities using {INTEGRATION_NAME}: "
                    f"{', '.join([entity.identifier for entity in failed_entities])}"
                )
        else:
            output_message = "No entities were enriched."
            result_value = False

    except Exception as e:
        output_message = f'Error executing action "Enrich Entities". Reason: {e}.'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
