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
from ..core import consts
from ..core.ThreatFuseManager import ThreatFuseManager
from ..core.consts import INTEGRATION_NAME
from ..core.exceptions import (
    ThreatFuseValidationException,
    ThreatFuseInvalidCredentialsException,
    ThreatFuseStatusCodeException,
)
from ..core.utils import (
    get_search_association_types,
    get_max_dict_value_size,
    convert_dict_values_from_set_to_list,
)

SCRIPT_NAME = "Get Related Hashes"
SUPPORTED_ENTITIES = (
    EntityTypes.FILEHASH,
    EntityTypes.ADDRESS,
    EntityTypes.URL,
    EntityTypes.USER,
    EntityTypes.CVE,
    EntityTypes.THREATACTOR,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    web_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Web Root",
        is_mandatory=True,
        print_value=True,
    )

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )

    email_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Email Address",
        is_mandatory=True,
    )

    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
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
    max_hashes_to_return = extract_action_param(
        siemplify,
        param_name="Max Hashes To Return",
        is_mandatory=False,
        print_value=True,
        default_value=consts.MAX_HASHES_TO_RETURN_DEFAULT,
        input_type=int,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    if max_hashes_to_return < 0:
        siemplify.LOGGER.info(
            f'"Max Hashes To Return" must be non-negative. Using default of {consts.MAX_HASHES_TO_RETURN_DEFAULT}.'
        )
        max_hashes_to_return = consts.MAX_HASHES_TO_RETURN_DEFAULT

    supported_entities = []  # list of supported entities
    actors_and_vulnerabilities = []

    status = EXECUTION_STATE_COMPLETED

    json_results = defaultdict(set)
    result_value = "false"

    try:
        if (
            confidence_threshold > consts.MAX_CONFIDENCE
            or confidence_threshold < consts.MIN_CONFIDENCE
        ):
            raise ThreatFuseValidationException(
                f"Confidence threshold' value should be in range from {consts.MIN_CONFIDENCE} to {consts.MAX_CONFIDENCE}"
            )

        manager = ThreatFuseManager(
            web_root=web_root,
            api_root=api_root,
            api_key=api_key,
            email_address=email_address,
            verify_ssl=verify_ssl,
        )

        for entity in siemplify.target_entities:
            if entity.entity_type not in SUPPORTED_ENTITIES:
                siemplify.LOGGER.info(
                    f"Entity {entity.identifier} is of unsupported type. Skipping."
                )
                continue

            if consts.SPACE_CHARACTER in entity.identifier.strip():
                siemplify.LOGGER.info(
                    "Entity {} contains a ' ' character (space), which is not supported for the action's "
                    "supported entities.".format(entity.identifier)
                )
                continue

            if entity.entity_type in [EntityTypes.CVE, EntityTypes.THREATACTOR]:
                actors_and_vulnerabilities.append(entity)
            else:
                supported_entities.append(entity.identifier.strip())

        siemplify.LOGGER.info(
            f"Supported entities are: {supported_entities + [entity.identifier for entity in actors_and_vulnerabilities]}"
        )
        search_association_types = get_search_association_types(
            {
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
        )

        siemplify.LOGGER.info(
            f"Querying search association types {search_association_types}"
        )

        for association_type in search_association_types:
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            if not supported_entities:
                siemplify.LOGGER.info("No supported entities found")
                break

            if get_max_dict_value_size(json_results) >= max_hashes_to_return:
                siemplify.LOGGER.info(
                    f"Json results size reached hashes max size of {max_hashes_to_return}"
                )
                break

            siemplify.LOGGER.info(
                f"Started making requests for association {association_type}"
            )

            try:
                # Get indicators for entities
                indicators = manager.get_indicators(entities=supported_entities)

                if not indicators:  # check if retrieved indicators
                    siemplify.LOGGER.info(
                        f"Didn't get indicators for association {association_type}"
                    )
                    continue

                siemplify.LOGGER.info(
                    f"Retrieved indicators {' '.join([str(indicator.id) for indicator in indicators])} for association {association_type}"
                )

                siemplify.LOGGER.info(
                    f"Getting related associations for indicator ids {' '.join([str(indicator.id) for indicator in indicators])}"
                )

                # Get latest related associations for indicators
                related_associations = manager.get_related_indicator_associations(
                    association_type=association_type,
                    ids=[indicator.id for indicator in indicators],
                    sort_by_key="modified_ts_ms",
                    limit=max_hashes_to_return,
                    asc=False,
                )
                if not related_associations:
                    siemplify.LOGGER.info(
                        f"Didn't retrieve associations of type {association_type} for ids {' '.join([str(indicator.id) for indicator in indicators])}"
                    )
                    continue

                siemplify.LOGGER.info(
                    f"Received related associations {[association.name for association in related_associations]}"
                )

                for association in related_associations:
                    if get_max_dict_value_size(json_results) >= max_hashes_to_return:
                        siemplify.LOGGER.info(
                            f"Json results size reached hashes max size of {max_hashes_to_return}. Skipping association {association.id}"
                        )
                        break

                    query_limit = max_hashes_to_return - get_max_dict_value_size(
                        json_results
                    )
                    association_indicators = manager.get_association_type_indicators(
                        association_type=association_type,
                        association_id=association.id,
                        indicator_type=consts.MD5_INDICATOR_TYPE,
                        confidence_threshold=confidence_threshold,
                        limit=query_limit,
                    )
                    if not association_indicators:
                        siemplify.LOGGER.info(
                            f"Didn't find {association_type} association indicator {association.id}"
                        )
                        continue

                    for indicator in association_indicators:
                        json_results[f"{indicator.subtype}_hashes"].add(indicator.value)
                        json_results["all_hashes"].add(indicator.value)

                    result_value = "true"
                    siemplify.LOGGER.info(
                        f"Successfully got file hashes for association {association_type} with name {association.name} and id {association.id}"
                    )

            except ThreatFuseInvalidCredentialsException as e:
                raise e

            except ThreatFuseStatusCodeException as e:
                siemplify.LOGGER.error(
                    f"An error occurred when querying association type {association_type}"
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
                model_type = consts.VULNERABILITY_ASSOCIATION_TYPE
            else:
                model_type = consts.ACTOR_ASSOCIATION_TYPE

            try:
                if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                    siemplify.LOGGER.error(
                        f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                    )
                    status = EXECUTION_STATE_TIMEDOUT
                    break

                if get_max_dict_value_size(json_results) >= max_hashes_to_return:
                    siemplify.LOGGER.info(
                        f"Json results size reached hashes max size of {max_hashes_to_return}"
                    )
                    break

                # Get latest related associations for entity
                related_associations = manager.get_related_associations_by_name(
                    association_type=model_type, value=entity.identifier.strip()
                )

                if not related_associations:
                    siemplify.LOGGER.info(
                        f"Didn't retrieve associations of type {model_type} for entity {entity.identifier}"
                    )
                    continue

                association = related_associations[0]

                siemplify.LOGGER.info(
                    f"Received related association {association.name}"
                )

                query_limit = max_hashes_to_return - get_max_dict_value_size(
                    json_results
                )
                association_indicators = manager.get_association_type_indicators(
                    association_type=model_type,
                    association_id=association.id,
                    indicator_type=consts.MD5_INDICATOR_TYPE,
                    confidence_threshold=confidence_threshold,
                    limit=query_limit,
                )
                if not association_indicators:
                    siemplify.LOGGER.info(
                        f"Didn't find {model_type} association indicator {association.id}"
                    )
                    continue

                for indicator in association_indicators:
                    json_results[f"{indicator.subtype}_hashes"].add(indicator.value)
                    json_results["all_hashes"].add(indicator.value)

                result_value = "true"
                siemplify.LOGGER.info(
                    f"Successfully got file hashes for association {model_type} with name {association.name} and id {association.id}"
                )

            except ThreatFuseInvalidCredentialsException as e:
                raise e

            except ThreatFuseStatusCodeException as e:
                siemplify.LOGGER.error(
                    f"An error occurred when processing entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

        if get_max_dict_value_size(json_results) > 0:
            siemplify.LOGGER.info(
                f"Successfully retrieved related hashes from {INTEGRATION_NAME}"
            )
            output_message = (
                f"Successfully retrieved related hashes from {INTEGRATION_NAME}"
            )
        else:
            siemplify.LOGGER.info("No related hashes were found")
            output_message = "No related hashes were found"

    except ThreatFuseValidationException as error:
        siemplify.LOGGER.error(error)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        output_message = f"{error}"

    except Exception as error:
        siemplify.LOGGER.error(
            f'Error executing action "{SCRIPT_NAME}". Reason: {error}'
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        output_message = f'Error executing action "{SCRIPT_NAME}". Reason: {error}'

    siemplify.result.add_result_json(convert_dict_values_from_set_to_list(json_results))
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
