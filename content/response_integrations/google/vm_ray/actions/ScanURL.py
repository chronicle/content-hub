from __future__ import annotations
import json
import sys
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.VMRayClientManager import VMRayClient
from ..core.constants import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    SCAN_URL_SCRIPT_NAME,
    SUSPICIOUS_STATUSES,
    DEFAULT_THREAT_INDICATOR_SCORE_THRESHOLD,
    MAX_THREAT_INDICATOR_SCORE_THRESHOLD,
    DEFAULT_LIMIT,
    URL_IOC_TYPE_DEFAULT_VALUES,
    IOC_VERDICT_MAPPING,
    IOC_VERDICT_DEFAULT_VALUES,
    ENRICHMENT_PREFIX,
    URL_IOC_TYPE_POSSIBLE_VALUES,
)
from ..core.UtilsManager import (
    convert_list_to_comma_string,
    convert_comma_separated_to_list,
    get_system_versions,
    get_entity_original_identifier,
)
from ..core.VMRayExceptions import NotFoundException


SUPPORTED_ENTITY_TYPES = [EntityTypes.URL]


def submit_url(siemplify, manager, target_entities, tag_names, comment):
    """
    Submit url
    :param siemplify: {siemplify} Siemplify object
    :param manager: {VMRayClientManager} VMRayClientManager manager object
    :param target_entities: {list} list of siemplify entities
    :param tag_names: {list} list of tags to add
    :param comment: {str} comment to add
    :return: {tuple} entities data containing sample_id and job_id, failed entity identifiers
    """
    entities_data = {}
    failed_entity_identifiers = []

    for entity in target_entities:
        entity_identifier = get_entity_original_identifier(entity)
        siemplify.LOGGER.info(f"\n\nStarted submitting entity: {entity_identifier}")

        try:
            # Submit url for analysis
            sample = manager.submit_url_for_browser_analysis(
                entity_identifier, tag_names, comment
            )

            if sample:
                entities_data[entity_identifier] = {
                    "sample_id": sample.sample_id,
                    "job_id": sample.job_id,
                }

        except Exception as e:
            failed_entity_identifiers.append(entity_identifier)
            siemplify.LOGGER.error(f"An error occurred on entity {entity_identifier}")
            siemplify.LOGGER.exception(e)

        siemplify.LOGGER.info(f"Finished submitting entity {entity_identifier}")

    return entities_data, failed_entity_identifiers


def get_job_details(
    siemplify, manager, entities_data, successful_entities, failed_entity_identifiers
):
    """
    Get job details
    :param siemplify: {siemplify} Siemplify object
    :param manager: {VMRayClientManager} VMRayClientManager manager object
    :param entities_data: {dict} entities data containing sample_id and job_id
    :param successful_entities: {dict} successful entities data containing sample_id
    :param failed_entity_identifiers: {list} list of failed entity identifiers
    :return: {tuple} successful entities, pending entities, failed entity identifiers
    """
    pending_entities = {}

    for key, value in entities_data.items():
        siemplify.LOGGER.info(f"\n\nGetting job details for entity: {key}")

        try:
            manager.get_job_details(value.get("job_id"))
            pending_entities[key] = value
            siemplify.LOGGER.info(f"Job for entity {key} is in progress")
        except NotFoundException:
            # if job request throws not found error it means job finished execution
            successful_entities[key] = value.get("sample_id")
            siemplify.LOGGER.info(f"Job for entity {key} finished execution")
        except Exception as e:
            failed_entity_identifiers.append(key)
            siemplify.LOGGER.error(
                f"An error occurred on entity {key} while waiting for job to finish execution"
            )
            siemplify.LOGGER.exception(e)

    return successful_entities, pending_entities, failed_entity_identifiers


def get_data(
    siemplify,
    manager,
    target_entities,
    entities_data,
    ioc_type_filter,
    ioc_verdict_filter,
    iocs_limit,
    threat_indicator_score_threshold,
    threat_indicators_limit,
    create_insight,
    only_suspicious_insight,
):
    """
    Get data for entity
    :param siemplify: {siemplify} Siemplify object
    :param manager: {VMRayClientManager} VMRayClientManager manager object
    :param target_entities: {list} list of siemplify entities
    :param entities_data: {dict} entities data containing sample_id
    :param ioc_type_filter: {list} list of ioc types for filtering
    :param ioc_verdict_filter: {list} list of ioc verdicts for filtering
    :param iocs_limit: {int} limit for results per ioc type
    :param threat_indicator_score_threshold: {int} lowest threat indicator score for filtering
    :param threat_indicators_limit: {int} limit for threat indicators
    :param create_insight: {bool} specifies if insight should be created
    :param only_suspicious_insight: {bool} specifies if insight should be created only for suspicious entities
    :return: {tuple} output message, result value, status
    """
    successful_entities = []
    failed_entity_identifiers = []
    json_results = {}
    output_message = ""
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    for entity in target_entities:
        entity_identifier = get_entity_original_identifier(entity)
        siemplify.LOGGER.info(
            f"\n\nStarted getting results for entity: {entity_identifier}"
        )

        try:
            sample_id = entities_data.get(entity_identifier)

            if sample_id:
                siemplify.LOGGER.info(
                    f"Getting Sample Analysis for URL: {entity_identifier}"
                )
                sample_analyses = manager.get_sample_by_id(sample_id)

                if sample_analyses:
                    # Get Sample IOCS
                    siemplify.LOGGER.info("Getting IOCS")
                    iocs_object = manager.get_sample_iocs(
                        sample_id, ioc_type_filter, ioc_verdict_filter, iocs_limit
                    )

                    if iocs_object:
                        if iocs_object.ioc_ips:
                            siemplify.result.add_entity_table(
                                f"{entity_identifier} - IOCS - IPs",
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
                                f"{entity_identifier} - IOCS - URLs",
                                construct_csv(
                                    list(
                                        map(
                                            lambda ioc_url: ioc_url.to_table(),
                                            iocs_object.ioc_urls,
                                        )
                                    )
                                ),
                            )

                        if iocs_object.ioc_domains:
                            siemplify.result.add_entity_table(
                                f"{entity_identifier} - IOCS - Domains",
                                construct_csv(
                                    list(
                                        map(
                                            lambda ioc_url: ioc_url.to_table(),
                                            iocs_object.ioc_urls,
                                        )
                                    )
                                ),
                            )

                    # Get Sample Threat Indicators
                    siemplify.LOGGER.info("Getting Threat Indicators")
                    threat_indicators = manager.get_sample_threat_indicators(
                        sample_id,
                        threat_indicator_score_threshold,
                        threat_indicators_limit,
                    )

                    if threat_indicators:
                        siemplify.result.add_entity_table(
                            f"{entity_identifier} - Threat Indicators",
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
                        sample_analyses.sample_verdict in SUSPICIOUS_STATUSES
                    )
                    link = sample_analyses.sample_webif_url
                    json_results[entity_identifier] = sample_analyses.to_json()
                    json_results[entity_identifier].update(
                        {"iocs": iocs_object.to_json()}
                    )
                    json_results[entity_identifier].update(
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
                                sample_analyses.to_insight(
                                    iocs_object,
                                    threat_indicators,
                                    ioc_types=ioc_type_filter,
                                ),
                                triggered_by=INTEGRATION_DISPLAY_NAME,
                            )

                    enrich_entity(
                        siemplify,
                        entity,
                        sample_analyses,
                        link,
                        is_suspicious,
                        iocs_object,
                        threat_indicators,
                    )
                    successful_entities.append(entity)
        except Exception as e:
            failed_entity_identifiers.append(entity_identifier)
            siemplify.LOGGER.error(f"An error occurred on entity {entity_identifier}")
            siemplify.LOGGER.exception(e)

    if successful_entities:
        siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
        siemplify.update_entities(successful_entities)
        successful_entities_str = "\n".join(
            get_entity_original_identifier(entity)
            for entity in successful_entities
        )
        output_message += (
            "Successfully enriched the following entities using information "
            f"from {INTEGRATION_DISPLAY_NAME}: \n{successful_entities_str}"
        )

    if failed_entity_identifiers:
        output_message += "\nAction wasn't able to enrich the following entities using information from {}: \n{}".format(
            INTEGRATION_DISPLAY_NAME, "\n".join(failed_entity_identifiers)
        )

    if not successful_entities:
        result_value = False
        output_message = "None of the provided entities were enriched."

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = SCAN_URL_SCRIPT_NAME

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
        default_value=convert_list_to_comma_string(URL_IOC_TYPE_DEFAULT_VALUES),
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
    tag_names = extract_action_param(
        siemplify, param_name="Tag Names", print_value=True
    )
    comment = extract_action_param(siemplify, param_name="Comment", print_value=True)

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
    additional_data = json.loads(
        extract_action_param(
            siemplify, param_name="additional_data", default_value="{}"
        )
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    initial_target_entity_identifiers = additional_data.get(
        "initial_target_entity_identifiers", []
    )
    pending_entities = additional_data.get("pending_entities", {})
    successful_entities = additional_data.get("successful_entities", {})
    failed_entity_identifiers = additional_data.get("failed_entity_identifiers", [])

    if is_first_run:
        target_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type in SUPPORTED_ENTITY_TYPES
        ]
    else:
        target_entities = [
            entity
            for entity in siemplify.target_entities
            if get_entity_original_identifier(entity)
            in initial_target_entity_identifiers
        ]

    try:
        if (
            threat_indicator_score_threshold < 0
            or threat_indicator_score_threshold > MAX_THREAT_INDICATOR_SCORE_THRESHOLD
        ):
            raise Exception(
                f'invalid value provided in the parameter "Threat Indicator Score Threshold". Only '
                f"integers in range from 0 to {MAX_THREAT_INDICATOR_SCORE_THRESHOLD} are supported."
            )

        if list(set(ioc_type_filter) - set(URL_IOC_TYPE_POSSIBLE_VALUES)):
            raise Exception(
                f'invalid value provided in the parameter "IOC Type Filter". Possible values: '
                f"{convert_list_to_comma_string(URL_IOC_TYPE_POSSIBLE_VALUES)}."
            )

        if list(set(ioc_verdict_filter) - set(list(IOC_VERDICT_MAPPING.values()))):
            raise Exception(
                f'invalid value provided in the parameter "IOC Verdict Filter". Possible values: '
                f"{convert_list_to_comma_string(list(map(lambda value: value.title(), IOC_VERDICT_MAPPING.values())))}."
            )

        vmray_manager = VMRayClient(
            api_root, api_key, verify_ssl, **get_system_versions(siemplify)
        )

        if is_first_run:
            pending_entities, failed_entity_identifiers = submit_url(
                siemplify, vmray_manager, target_entities, tag_names, comment
            )

        successful_entities, pending_entities, failed_entity_identifiers = (
            get_job_details(
                siemplify,
                vmray_manager,
                pending_entities,
                successful_entities,
                failed_entity_identifiers,
            )
        )

        if not pending_entities:
            output_message, result_value, status = get_data(
                siemplify,
                vmray_manager,
                target_entities,
                successful_entities,
                ioc_type_filter,
                ioc_verdict_filter,
                iocs_limit,
                threat_indicator_score_threshold,
                threat_indicators_limit,
                create_insight,
                only_suspicious_insight,
            )
        else:
            status = EXECUTION_STATE_INPROGRESS
            result_value = json.dumps(
                {
                    "successful_entities": successful_entities,
                    "pending_entities": pending_entities,
                    "failed_entity_identifiers": failed_entity_identifiers,
                    "initial_target_entity_identifiers": [
                        get_entity_original_identifier(entity)
                        for entity in target_entities
                    ],
                }
            )
            output_message = "Pending entities: \n{}".format(
                "\n".join(pending_entities.keys())
            )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {SCAN_URL_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = f'Error executing action "{SCAN_URL_SCRIPT_NAME}". Reason: {e}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


# Enrich target entity with vmray info and add web link with full details to entity
def enrich_entity(
    siemplify, entity, report, web_link, is_suspicious, iocs_object, threat_indicators
):
    entity_identifier = get_entity_original_identifier(entity)
    siemplify.result.add_entity_table(entity_identifier, report.to_table())
    siemplify.result.add_entity_link(entity_identifier, web_link)
    entity.additional_properties.update(
        report.to_enrichment_data(
            iocs_object,
            threat_indicators,
            prefix=ENRICHMENT_PREFIX,
            ioc_types=URL_IOC_TYPE_POSSIBLE_VALUES,
        )
    )
    entity.is_enriched = True

    if is_suspicious:
        entity.is_suspicious = True


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
