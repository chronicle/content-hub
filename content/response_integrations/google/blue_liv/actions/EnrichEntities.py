from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.BlueLivManager import BlueLivManager
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    flat_dict_to_csv,
)
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.consts import (
    INTEGRATION_NAME,
    ENRICH_ENTITIES,
    ENRICHMENT_PREFIX,
    MD5_LENGTH,
    SHA1_LENGTH,
    SHA256_LENGTH,
    SHA512_LENGTH,
    MAX_LOWEST_SCORE,
)
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.Siemplify import InsightSeverity, InsightType

SUPPORTED_ENTITY_TYPES = [
    EntityTypes.THREATACTOR,
    EntityTypes.THREATCAMPAIGN,
    EntityTypes.THREATSIGNATURE,
    EntityTypes.ADDRESS,
    EntityTypes.FILEHASH,
    EntityTypes.URL,
    EntityTypes.CVE,
]
RISK_SUPPORTED_ENTITIES = [EntityTypes.ADDRESS, EntityTypes.FILEHASH, EntityTypes.URL]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_ENTITIES
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="User Name",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
        print_value=False,
    )
    organization_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Organization ID",
        is_mandatory=True,
        print_value=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
    )

    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""
    json_result = {}
    successful_entities = []
    failed_entities = []
    successful_endpoints = []

    try:
        siemplify.LOGGER.info("----------------- Main - Started -----------------")
        create_intsight = extract_action_param(
            siemplify,
            param_name="Create Insight",
            is_mandatory=False,
            print_value=True,
            default_value=False,
            input_type=bool,
        )
        lowest_score = extract_action_param(
            siemplify,
            param_name="Lowest Score To Mark as Suspicious",
            default_value=5,
            is_mandatory=True,
            print_value=True,
            input_type=int,
        )

        if lowest_score > MAX_LOWEST_SCORE:
            siemplify.LOGGER.info(
                f'Maximum value for parameter "Lowest Score To Mark as Suspicious" is {MAX_LOWEST_SCORE}. The action will use maximum value.'
            )
            lowest_score = MAX_LOWEST_SCORE

        if lowest_score < 0:
            siemplify.LOGGER.error(
                f'Given value of {lowest_score} for parameter "Lowest Score To Mark as Suspicious" is non positive.'
            )
            raise Exception(
                f'Given value of {lowest_score} for parameter "Lowest Score To Mark as Suspicious" is non positive.'
            )

        blueliv_manager = BlueLivManager(
            api_root=api_root,
            username=username,
            password=password,
            organization_id=organization_id,
            verify_ssl=verify_ssl,
        )

        module_id = blueliv_manager.get_blueliv_context_information()

        if module_id is None:
            raise Exception('Your instance doesn\'t support "Threat Context" module.')

        blueliv_manager.module_id_setter(module_id=module_id)

        suitable_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type in SUPPORTED_ENTITY_TYPES
        ]

        for entity in suitable_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
            try:

                if entity.entity_type == EntityTypes.ADDRESS:
                    entity_details = blueliv_manager.enrich_ip_address(
                        entity_id=entity.identifier
                    )

                if entity.entity_type == EntityTypes.FILEHASH:
                    if len(entity.identifier) in [
                        MD5_LENGTH,
                        SHA1_LENGTH,
                        SHA256_LENGTH,
                        SHA512_LENGTH,
                    ]:
                        entity_details = blueliv_manager.enrich_hash(
                            entity_id=entity.identifier
                        )
                    else:
                        raise Exception("Provided hash value is not supported.")

                if entity.entity_type == EntityTypes.CVE:
                    entity_details = blueliv_manager.enrich_cve(
                        entity_id=entity.identifier
                    )

                if entity.entity_type == EntityTypes.URL:
                    threat_details = blueliv_manager.get_crime_server_details(
                        entity_id=entity.identifier
                    )
                    entity_details = blueliv_manager.enrich_url(
                        entity_id=threat_details.id
                    )

                if entity.entity_type == EntityTypes.THREATACTOR:
                    threat_details = blueliv_manager.get_threat_actor_details(
                        entity_id=entity.identifier
                    )
                    entity_details = blueliv_manager.enrich_threatactor(
                        entity_id=threat_details.id
                    )

                if entity.entity_type == EntityTypes.THREATCAMPAIGN:
                    threat_details = blueliv_manager.get_threat_campaign_details(
                        entity_id=entity.identifier
                    )
                    entity_details = blueliv_manager.enrich_threatcampaign(
                        entity_id=threat_details.id
                    )

                if entity.entity_type == EntityTypes.THREATSIGNATURE:
                    threat_details = blueliv_manager.get_threat_signature_details(
                        entity_id=entity.identifier
                    )
                    entity_details = blueliv_manager.enrich_threatsignature(
                        entity_id=threat_details.id
                    )

            except Exception as e:
                failed_entities.append(entity)
                siemplify.LOGGER.info(
                    f"Failed processing entity {entity.identifier}. Reason: {e}"
                )
                continue

            if entity_details and entity_details.raw_data:
                json_result[entity.identifier] = entity_details.to_json()
                entity.additional_properties.update(
                    entity_details.to_enrichment_data(prefix=ENRICHMENT_PREFIX)
                )
                entity.is_enriched = True
                if (
                    entity.entity_type in RISK_SUPPORTED_ENTITIES
                    and entity_details.risk >= lowest_score
                ):
                    entity.is_suspicious = True
                successful_entities.append(entity)
                successful_endpoints.append(
                    entity_details.to_insight(identifier=entity.identifier)
                )

                link = (
                    entity_details.to_table().get("link")
                    if entity_details.to_table().get("link")
                    else None
                )
                if link is not None:
                    siemplify.result.add_entity_link(entity.identifier, link)

                siemplify.result.add_entity_table(
                    entity.identifier, flat_dict_to_csv(entity_details.to_table())
                )

            else:
                failed_entities.append(entity)

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

        if successful_entities:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_result)
            )

            if create_intsight:
                siemplify.create_case_insight(
                    triggered_by=INTEGRATION_NAME,
                    title="Enriched Entities",
                    content="".join(successful_endpoints),
                    entity_identifier="",
                    severity=InsightSeverity.INFO,
                    insight_type=InsightType.General,
                )

            siemplify.update_entities(successful_entities)
            output_message += (
                "Successfully enriched the following entities using {}: \n{}".format(
                    INTEGRATION_NAME,
                    "\n".join([entity.identifier for entity in successful_entities]),
                )
            )

        if failed_entities:
            output_message += "\nAction wasn't able to enrich the following entities using {}: \n{}".format(
                INTEGRATION_NAME,
                "\n".join([entity.identifier for entity in failed_entities]),
            )

        if not successful_entities:
            result_value = False
            output_message = "No entities were enriched"

    except Exception as e:
        output_message += f"Error executing action {ENRICH_ENTITIES}. Reason: {e}"
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
