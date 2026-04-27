from __future__ import annotations
from collections import defaultdict
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, unix_now, convert_unixtime_to_datetime
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.AnomaliThreatStreamManager import AnomaliManager
from ..core.constants import (
    INTEGRATION_NAME,
    GET_RELATED_ENTITIES_SCRIPT_NAME,
    EMAIL_TYPE,
    MAX_ENTITIES_TO_RETURN_DEFAULT,
    MAX_CONFIDENCE,
    MIN_CONFIDENCE,
    ENDPOINTS_MAPPER,
    MD5_INDICATOR_TYPE,
    ENTITY_TYPES,
    VULNERABILITY_ASSOCIATION_TYPE,
    ACTOR_ASSOCIATION_TYPE,
)
from ..core.utils import (
    get_entity_type,
    get_entity_original_identifier,
    get_max_dict_value_size,
    convert_dict_values_from_set_to_list,
)
from ..core.exceptions import AnomaliThreatStreamInvalidCredentialsException

SUPPORTED_ENTITIES = [
    EntityTypes.FILEHASH,
    EntityTypes.ADDRESS,
    EntityTypes.URL,
    EMAIL_TYPE,
]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_RELATED_ENTITIES_SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    web_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Web Root",
        print_value=True,
    )
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        print_value=True,
    )
    email_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Email Address",
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    search_threat_bulletins = extract_action_param(
        siemplify,
        param_name="Search Threat Bulletins",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    search_actors = extract_action_param(
        siemplify,
        param_name="Search Actors",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    search_attack_patterns = extract_action_param(
        siemplify,
        param_name="Search Attack Patterns",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    search_campaigns = extract_action_param(
        siemplify,
        param_name="Search Campaigns",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    search_courses_of_action = extract_action_param(
        siemplify,
        param_name="Search Courses Of Action",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    search_identities = extract_action_param(
        siemplify,
        param_name="Search Identities",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    search_incidents = extract_action_param(
        siemplify,
        param_name="Search Incidents",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    search_infrastructures = extract_action_param(
        siemplify,
        param_name="Search Infrastructures",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    search_intrusion_sets = extract_action_param(
        siemplify,
        param_name="Search Intrusion Sets",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    search_malware = extract_action_param(
        siemplify,
        param_name="Search Malware",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    search_signatures = extract_action_param(
        siemplify,
        param_name="Search Signatures",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    search_tools = extract_action_param(
        siemplify,
        param_name="Search Tools",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    search_ttps = extract_action_param(
        siemplify,
        param_name="Search TTPs",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    search_vulnerabilities = extract_action_param(
        siemplify,
        param_name="Search Vulnerabilities",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
        default_value=True,
    )
    confidence_threshold = extract_action_param(
        siemplify,
        param_name="Confidence Threshold",
        is_mandatory=True,
        print_value=True,
        input_type=int,
    )
    max_entities_to_return = extract_action_param(
        siemplify,
        param_name="Max Entities To Return",
        print_value=True,
        default_value=MAX_ENTITIES_TO_RETURN_DEFAULT,
        input_type=int,
    )

    suitable_entities = []
    actors_and_vulnerabilities = []
    for entity in siemplify.target_entities:
        if get_entity_type(entity) in SUPPORTED_ENTITIES:
            suitable_entities.append(entity)
        elif get_entity_type(entity) in [EntityTypes.CVE, EntityTypes.THREATACTOR]:
            actors_and_vulnerabilities.append(entity)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    if max_entities_to_return < 0:
        siemplify.LOGGER.info(
            f'"Max Entities To Return" must be non-negative. '
            f"Using default of {MAX_ENTITIES_TO_RETURN_DEFAULT}."
        )
        max_entities_to_return = MAX_ENTITIES_TO_RETURN_DEFAULT

    status = EXECUTION_STATE_COMPLETED
    json_results = defaultdict(set)
    result_value = False

    try:
        if (
            confidence_threshold > MAX_CONFIDENCE
            or confidence_threshold < MIN_CONFIDENCE
        ):
            raise Exception(
                f"Confidence threshold' value should be in range from {MIN_CONFIDENCE} "
                f"to {MAX_CONFIDENCE}"
            )

        manager = AnomaliManager(
            web_root=web_root,
            api_root=api_root,
            api_key=api_key,
            username=email_address,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
            logger=siemplify.LOGGER,
        )

        siemplify.LOGGER.info(f"Supported entities are: {suitable_entities}")

        search_association_types = {
            "Threat Bulletins": search_threat_bulletins,
            "Actors": search_actors,
            "Attack Patterns": search_attack_patterns,
            "Campaigns": search_campaigns,
            "Courses Of Action": search_courses_of_action,
            "Identities": search_identities,
            "Incidents": search_incidents,
            "Infrastructure": search_infrastructures,
            "Intrusion Sets": search_intrusion_sets,
            "Malware": search_malware,
            "Signatures": search_signatures,
            "Tools": search_tools,
            "TTPs": search_ttps,
            "Vulnerabilities": search_vulnerabilities,
        }

        siemplify.LOGGER.info(
            f"Querying search association types {search_association_types}"
        )

        for association_type, value in search_association_types.items():
            if not value:
                continue

            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            if not suitable_entities:
                siemplify.LOGGER.info("No supported entities found")
                break

            siemplify.LOGGER.info(
                f"Started making requests for association {association_type}"
            )

            try:
                # Get indicators for entities
                indicators = manager.get_indicators(
                    entities=[
                        get_entity_original_identifier(entity)
                        for entity in suitable_entities
                    ]
                )

                if not indicators:  # check if retrieved indicators
                    siemplify.LOGGER.info(
                        f"Didn't get indicators for association {association_type}"
                    )
                    continue

                siemplify.LOGGER.info(
                    "Retrieved indicators "
                    f"{' '.join([str(indicator.id) for indicator in indicators])} for "
                    f"association {association_type}"
                )

                siemplify.LOGGER.info(
                    f"Getting related associations for indicator ids "
                    f"{' '.join([str(indicator.id) for indicator in indicators])}"
                )

                # Get the latest related associations for indicators
                related_associations = manager.get_related_indicator_associations(
                    association_type=ENDPOINTS_MAPPER[association_type],
                    ids=[indicator.id for indicator in indicators],
                    sort_by_key="modified_ts_ms",
                    limit=max_entities_to_return,
                    asc=False,
                )
                if not related_associations:
                    siemplify.LOGGER.info(
                        f"Didn't retrieve associations of type {association_type} "
                        "for ids "
                        f"{' '.join([str(indicator.id) for indicator in indicators])}"
                    )
                    continue

                siemplify.LOGGER.info(
                    "Received related associations "
                    f"{[association.name for association in related_associations]}"
                )

                for association in related_associations:
                    for entity_type, result_key in ENTITY_TYPES.items():
                        association_indicators = (
                            manager.get_association_type_indicators(
                                association_type=ENDPOINTS_MAPPER[association_type],
                                association_id=association.id,
                                indicator_type=entity_type,
                                confidence_threshold=confidence_threshold,
                                limit=max_entities_to_return,
                            )
                        )
                        if not association_indicators:
                            siemplify.LOGGER.info(
                                f"Didn't find {association_type} association indicator "
                                f"{association.id}"
                            )
                            continue

                        for indicator in association_indicators:
                            if len(json_results[result_key]) < max_entities_to_return:
                                if entity_type == MD5_INDICATOR_TYPE:
                                    json_results[f"{indicator.subtype}_hashes"].add(
                                        indicator.value
                                    )
                                json_results[result_key].add(indicator.value)

                    result_value = True
                    siemplify.LOGGER.info(
                        "Successfully got file hashes for association "
                        f"{association_type} with name {association.name} "
                        f"and id {association.id}"
                    )

            except AnomaliThreatStreamInvalidCredentialsException as e:
                raise e

            except Exception as e:
                siemplify.LOGGER.error(
                    "An error occurred when querying association type "
                    f"{association_type}"
                )
                siemplify.LOGGER.exception(e)

        siemplify.LOGGER.info(f"Processing threat actors and vulnerabilities")
        if not actors_and_vulnerabilities:
            siemplify.LOGGER.info(
                "No threat actors and vulnerabilities found in the scope"
            )

        for entity in actors_and_vulnerabilities:
            siemplify.LOGGER.info(f"Started processing entity {entity.identifier}")
            if entity.entity_type == EntityTypes.CVE:
                model_type = VULNERABILITY_ASSOCIATION_TYPE
            else:
                model_type = ACTOR_ASSOCIATION_TYPE

            try:
                if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                    siemplify.LOGGER.error(
                        "Timed out. execution deadline "
                        f"({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                    )
                    status = EXECUTION_STATE_TIMEDOUT
                    break

                # Get latest related associations for entity
                related_associations = manager.get_related_associations_by_name(
                    association_type=model_type, value=entity.identifier.strip()
                )

                if not related_associations:
                    siemplify.LOGGER.info(
                        f"Didn't retrieve associations of type {model_type} for entity "
                        f"{entity.identifier}"
                    )
                    continue

                association = related_associations[0]

                siemplify.LOGGER.info(
                    f"Received related association {association.name}"
                )

                for entity_type, result_key in ENTITY_TYPES.items():
                    association_indicators = manager.get_association_type_indicators(
                        association_type=model_type,
                        association_id=association.id,
                        indicator_type=entity_type,
                        confidence_threshold=confidence_threshold,
                        limit=max_entities_to_return,
                    )
                    if not association_indicators:
                        siemplify.LOGGER.info(
                            f"Didn't find {model_type} association indicator "
                            f"{association.id}"
                        )
                        continue

                    for indicator in association_indicators:
                        if len(json_results[result_key]) < max_entities_to_return:
                            if entity_type == MD5_INDICATOR_TYPE:
                                json_results[f"{indicator.subtype}_hashes"].add(
                                    indicator.value
                                )
                            json_results[result_key].add(indicator.value)

                result_value = True
                siemplify.LOGGER.info(
                    f"Successfully got file hashes for association {model_type} with "
                    f"name {association.name} and id {association.id}"
                )

            except AnomaliThreatStreamInvalidCredentialsException as e:
                raise e

            except Exception as e:
                siemplify.LOGGER.error(
                    f"An error occurred when processing entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

        if get_max_dict_value_size(json_results) > 0:
            output_message = (
                f"Successfully retrieved related entities from {INTEGRATION_NAME}"
            )
            siemplify.LOGGER.info(output_message)
            siemplify.result.add_result_json(
                convert_dict_values_from_set_to_list(json_results)
            )
        else:
            output_message = "No related entities were found"
            siemplify.LOGGER.info(output_message)

    except Exception as error:
        output_message = (
            f'Error executing action "{GET_RELATED_ENTITIES_SCRIPT_NAME}". '
            f'Reason: {error}'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
