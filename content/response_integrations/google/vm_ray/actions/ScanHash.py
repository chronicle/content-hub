from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.VMRayClientManager import VMRayClient
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    SCAN_HASH_SCRIPT_NAME,
    SUSPICIOUS_STATUSES,
    DEFAULT_THREAT_INDICATOR_SCORE_THRESHOLD,
    MAX_THREAT_INDICATOR_SCORE_THRESHOLD,
    DEFAULT_LIMIT,
    IOC_TYPE_DEFAULT_VALUES,
    IOC_VERDICT_MAPPING,
    IOC_VERDICT_DEFAULT_VALUES,
    ENRICHMENT_PREFIX,
    IOC_TYPE_POSSIBLE_VALUES,
)
from ..core.UtilsManager import (
    convert_list_to_comma_string,
    convert_comma_separated_to_list,
    get_system_versions,
)


SUPPORTED_ENTITY_TYPES = [EntityTypes.FILEHASH]


# Enrich target entity with vmray info and add web link with full details to entity
def enrich_entity(
    siemplify, entity, report, web_link, is_suspicious, iocs_object, threat_indicators
):
    siemplify.result.add_entity_table(entity.identifier, report.to_table())
    siemplify.result.add_entity_link(entity.identifier, web_link)
    entity.additional_properties.update(
        report.to_enrichment_data(
            iocs_object, threat_indicators, prefix=ENRICHMENT_PREFIX
        )
    )
    entity.is_enriched = True

    if is_suspicious:
        entity.is_suspicious = True


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCAN_HASH_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")
    # integration configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Key"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    # action parameters
    threat_indicator_score_threshold = extract_action_param(
        siemplify,
        param_name="Threat Indicator Score Threshold",
        is_mandatory=True,
        default_value=DEFAULT_THREAT_INDICATOR_SCORE_THRESHOLD,
        input_type=int,
        print_value=True,
    )
    ioc_type_filter_string = extract_action_param(
        siemplify,
        param_name="IOC Type Filter",
        is_mandatory=True,
        default_value=convert_list_to_comma_string(IOC_TYPE_DEFAULT_VALUES),
        print_value=True,
    )
    ioc_verdict_filter_string = extract_action_param(
        siemplify,
        param_name="IOC Verdict Filter",
        is_mandatory=True,
        default_value=convert_list_to_comma_string(IOC_VERDICT_DEFAULT_VALUES),
        print_value=True,
    )
    iocs_limit = extract_action_param(
        siemplify,
        param_name="Max IOCs To Return",
        default_value=DEFAULT_LIMIT,
        input_type=int,
        print_value=True,
    )
    threat_indicators_limit = extract_action_param(
        siemplify,
        param_name="Max Threat Indicators To Return",
        input_type=int,
        default_value=DEFAULT_LIMIT,
        print_value=True,
    )
    create_insight = extract_action_param(
        siemplify, param_name="Create Insight", input_type=bool, print_value=True
    )
    only_suspicious_insight = extract_action_param(
        siemplify,
        param_name="Only Suspicious Insight",
        input_type=bool,
        print_value=True,
    )

    ioc_type_filter = list(
        map(
            lambda item: item.lower(),
            convert_comma_separated_to_list(ioc_type_filter_string),
        )
    )
    ioc_verdict_filter = list(
        map(
            lambda item: item.lower(),
            convert_comma_separated_to_list(ioc_verdict_filter_string),
        )
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    successful_entities = []
    failed_entities = []
    json_results = {}

    try:
        if (
            threat_indicator_score_threshold < 0
            or threat_indicator_score_threshold > MAX_THREAT_INDICATOR_SCORE_THRESHOLD
        ):
            raise Exception(
                f'invalid value provided in the parameter "Threat Indicator Score Threshold". Only '
                f"integers in range from 0 to {MAX_THREAT_INDICATOR_SCORE_THRESHOLD} are supported."
            )

        if list(set(ioc_type_filter) - set(IOC_TYPE_POSSIBLE_VALUES)):
            raise Exception(
                f'invalid value provided in the parameter "IOC Type Filter". Possible values: '
                f"{convert_list_to_comma_string(IOC_TYPE_POSSIBLE_VALUES)}."
            )

        if list(set(ioc_verdict_filter) - set(list(IOC_VERDICT_MAPPING.values()))):
            raise Exception(
                f'invalid value provided in the parameter "IOC Verdict Filter". Possible values: '
                f"{convert_list_to_comma_string(list(map(lambda value: value.title(), IOC_VERDICT_MAPPING.values())))}."
            )

        vmray_manager = VMRayClient(
            api_root, api_key, verify_ssl, **get_system_versions(siemplify)
        )
        target_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type in SUPPORTED_ENTITY_TYPES
        ]

        for entity in target_entities:
            siemplify.LOGGER.info(f"\nStarted processing entity: {entity.identifier}")

            try:
                hash_lower = entity.identifier.lower()
                # Get complete sample by type of hash (md5, sha1, sha256) file hash
                siemplify.LOGGER.info(f"Getting Sample for hash: {hash_lower}")
                sample_analyses_obj = vmray_manager.get_sample_by_hash(hash_lower)

                if sample_analyses_obj:
                    # Get Sample IOCS
                    siemplify.LOGGER.info("Getting IOCS")
                    iocs_object = vmray_manager.get_sample_iocs(
                        sample_analyses_obj.sample_id,
                        ioc_type_filter,
                        ioc_verdict_filter,
                        iocs_limit,
                    )

                    if iocs_object:
                        if iocs_object.ioc_files:
                            siemplify.result.add_entity_table(
                                f"{entity.identifier} - IOCS - Files",
                                construct_csv(
                                    list(
                                        map(
                                            lambda ioc_file: ioc_file.to_table(),
                                            iocs_object.ioc_files,
                                        )
                                    )
                                ),
                            )

                        if iocs_object.ioc_domains:
                            siemplify.result.add_entity_table(
                                f"{entity.identifier} - IOCS - Domains",
                                construct_csv(
                                    list(
                                        map(
                                            lambda ioc_domain: ioc_domain.to_table(),
                                            iocs_object.ioc_domains,
                                        )
                                    )
                                ),
                            )

                        if iocs_object.ioc_ips:
                            siemplify.result.add_entity_table(
                                f"{entity.identifier} - IOCS - IPs",
                                construct_csv(
                                    list(
                                        map(
                                            lambda ioc_ip: ioc_ip.to_table(),
                                            iocs_object.ioc_ips,
                                        )
                                    )
                                ),
                            )

                        if iocs_object.ioc_urls:
                            siemplify.result.add_entity_table(
                                f"{entity.identifier} - IOCS - URLs",
                                construct_csv(
                                    list(
                                        map(
                                            lambda ioc_url: ioc_url.to_table(),
                                            iocs_object.ioc_urls,
                                        )
                                    )
                                ),
                            )

                        if iocs_object.ioc_registries:
                            siemplify.result.add_entity_table(
                                f"{entity.identifier} - IOCS - Registry Keys",
                                construct_csv(
                                    list(
                                        map(
                                            lambda ioc_registry: ioc_registry.to_table(),
                                            iocs_object.ioc_registries,
                                        )
                                    )
                                ),
                            )

                        if iocs_object.ioc_mutexes:
                            siemplify.result.add_entity_table(
                                f"{entity.identifier} - IOCS - Mutexes",
                                construct_csv(
                                    list(
                                        map(
                                            lambda ioc_mutex: ioc_mutex.to_table(),
                                            iocs_object.ioc_mutexes,
                                        )
                                    )
                                ),
                            )

                    # Get Sample Threat Indicators
                    siemplify.LOGGER.info("Getting Threat Indicators")
                    threat_indicators = vmray_manager.get_sample_threat_indicators(
                        sample_analyses_obj.sample_id,
                        threat_indicator_score_threshold,
                        threat_indicators_limit,
                    )

                    if threat_indicators:
                        siemplify.result.add_entity_table(
                            f"{entity.identifier} - Threat Indicators",
                            construct_csv(
                                list(
                                    map(
                                        lambda threat_indicator: threat_indicator.to_table(),
                                        threat_indicators,
                                    )
                                )
                            ),
                        )

                    is_suspicious = (
                        sample_analyses_obj.sample_verdict in SUSPICIOUS_STATUSES
                    )
                    link = sample_analyses_obj.sample_webif_url
                    json_results[entity.identifier] = sample_analyses_obj.to_json()
                    json_results[entity.identifier].update(
                        {"iocs": iocs_object.to_json()}
                    )
                    json_results[entity.identifier].update(
                        {
                            "threat_indicators": [
                                threat_indicator.to_json()
                                for threat_indicator in threat_indicators
                            ]
                        }
                    )

                    if create_insight:
                        if not only_suspicious_insight or is_suspicious:
                            siemplify.add_entity_insight(
                                entity,
                                sample_analyses_obj.to_insight(
                                    iocs_object,
                                    threat_indicators,
                                    additional_info=True,
                                    ioc_types=ioc_type_filter,
                                ),
                                triggered_by=INTEGRATION_DISPLAY_NAME,
                            )

                    enrich_entity(
                        siemplify,
                        entity,
                        sample_analyses_obj,
                        link,
                        is_suspicious,
                        iocs_object,
                        threat_indicators,
                    )
                    successful_entities.append(entity)

            except Exception as e:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}\n")

        if successful_entities:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            siemplify.update_entities(successful_entities)
            output_message += "Successfully enriched the following entities using information from {}: \n{}".format(
                INTEGRATION_DISPLAY_NAME,
                "\n".join([entity.identifier for entity in successful_entities]),
            )

        if failed_entities:
            output_message += "\nAction wasn't able to enrich the following entities using information from {}: \n{}".format(
                INTEGRATION_DISPLAY_NAME,
                "\n".join([entity.identifier for entity in failed_entities]),
            )

        if not successful_entities:
            result_value = False
            output_message = "None of the provided entities were enriched."

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {SCAN_HASH_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = (
            f'Error executing action "{SCAN_HASH_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
