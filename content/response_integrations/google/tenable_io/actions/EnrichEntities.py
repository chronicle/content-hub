from __future__ import annotations

from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    flat_dict_to_csv,
)
from tenable_io.core.TenableIOManager import TenableIOManager
from tenable_io.core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    ENRICH_ENTITIES_SCRIPT_NAME,
    ENRICHMENT_PREFIX,
)
from soar_sdk.SiemplifyDataModel import EntityTypes
from tenable_io.core.UtilsManager import build_identifier_to_asset_map


SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


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
        print_value=True,
    )
    secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Secret Key",
        is_mandatory=True,
    )
    access_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Access Key",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    # Action parameters
    create_insight = extract_action_param(
        siemplify, param_name="Create Insight", input_type=bool, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    successful_entities = []
    failed_entities = []
    json_results = {}
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        manager = TenableIOManager(
            api_root=api_root,
            secret_key=secret_key,
            access_key=access_key,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
            siemplify=siemplify,
        )

        siemplify.LOGGER.info("Fetching all assets from Tenable.io.")
        all_assets_list = manager.get_all_assets()
        asset_map = build_identifier_to_asset_map(all_assets_list)

        for entity in suitable_entities:
            siemplify.LOGGER.info(f"\nStarted processing entity: {entity.identifier}")
            normalized_entity = entity.identifier.lower()

            asset = asset_map.get(normalized_entity)

            if not asset and entity.entity_type == EntityTypes.HOSTNAME:
                short_name = normalized_entity.split(".")[0]
                asset = asset_map.get(short_name)

            if asset:
                try:
                    successful_entities.append(entity)
                    json_results[entity.identifier] = asset.to_json()
                    entity.additional_properties.update(
                        asset.to_enrichment_data(prefix=ENRICHMENT_PREFIX)
                    )
                    entity.is_enriched = True

                    siemplify.result.add_entity_table(
                        entity.identifier, flat_dict_to_csv(asset.to_table())
                    )

                    if create_insight:
                        siemplify.add_entity_insight(
                            entity,
                            asset.as_insight(),
                            triggered_by=INTEGRATION_DISPLAY_NAME,
                        )
                    siemplify.LOGGER.info(
                        f"Successfully enriched entity {entity.identifier}"
                    )
                except (AttributeError, KeyError, TypeError, ValueError) as error:
                    failed_entities.append(entity)
                    siemplify.LOGGER.error(
                        f"Failed processing entity: {entity.identifier}"
                    )
                    siemplify.LOGGER.exception(error)
            else:
                failed_entities.append(entity)
                siemplify.LOGGER.warn(
                    f"Entity {entity.identifier} not found "
                    f"in {INTEGRATION_DISPLAY_NAME}."
                )

        if successful_entities:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            siemplify.update_entities(successful_entities)
            enriched_entities_str = "\n".join(
                [entity.identifier for entity in successful_entities]
            )
            output_message += (
                "Successfully enriched the following entities using information "
                f"from {INTEGRATION_DISPLAY_NAME}: \n{enriched_entities_str}"
            )

        if failed_entities:
            failed_entities_str = "\n".join(
                [entity.identifier for entity in failed_entities]
            )
            output_message += (
                "\nAction wasn't able to enrich the following entities using "
                f"information from {INTEGRATION_DISPLAY_NAME}: \n{failed_entities_str}"
            )

        if not successful_entities:
            result = False
            output_message = "None of the provided entities were enriched."

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {ENRICH_ENTITIES_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{ENRICH_ENTITIES_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
