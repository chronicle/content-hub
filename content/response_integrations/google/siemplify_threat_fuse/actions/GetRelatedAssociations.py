from __future__ import annotations
import json
import sys
from collections import defaultdict

from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core import consts
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes, InsightType, InsightSeverity
from soar_sdk.SiemplifyUtils import output_handler, unix_now, convert_unixtime_to_datetime
from ..core.ThreatFuseManager import ThreatFuseManager
from ..core.consts import (
    INTEGRATION_NAME,
    INTEGRATION_IDENTIFIER,
    GET_RELATED_ASSOCIATION_SCRIPT_NAME,
)
from ..core.exceptions import ThreatFuseValidationException
from ..core.utils import get_search_association_types, append_association_type_to_entities

SUPPORTED_ENTITIES = (
    EntityTypes.FILEHASH,
    EntityTypes.ADDRESS,
    EntityTypes.URL,
    EntityTypes.USER,
)


def get_association_detailed_information(
    manager: ThreatFuseManager, association_type: str, association_id: int
):
    """
    Get detailed information about an association type with an association id
    :param association_type: {str} association type to get detailed information from
    :param association_id: {int} id of the association to get information from
    :return: {datamodels.<association_type>} the matching datamodel for the association_type
        for example if association_type='campaign' -> CampaignDetails datamodel will be returned
    """
    if association_type == consts.CAMPAIGN_ASSOCIATION_TYPE:
        return manager.get_campaign_details(association_id)
    elif association_type == consts.SIGNATURE_ASSOCIATION_TYPE:
        return manager.get_signature_details(association_id)
    elif association_type == consts.ACTOR_ASSOCIATION_TYPE:
        return manager.get_actor_details(association_id)
    elif association_type == consts.VULNERABILITY_ASSOCIATION_TYPE:
        return manager.get_vulnerability_details(association_id)
    elif association_type == consts.THREAT_BULLETINS_ASSOCIATION_TYPE:
        return manager.get_tipreport_details(association_id)
    elif association_type == consts.ATTACK_PATTERNS_ASSOCIATION_TYPE:
        return manager.get_attackpattern_details(association_id)
    elif association_type == consts.COURSES_OF_ACTION_ASSOCIATION_TYPE:
        return manager.get_courseofaction_details(association_id)
    elif association_type == consts.IDENTITY_ASSOCIATION_TYPE:
        return manager.get_identity_details(association_id)
    elif association_type == consts.INCIDENT_ASSOCIATION_TYPE:
        return manager.get_incident_details(association_id)
    elif association_type == consts.INFRASTRUCTURE_ASSOCIATION_TYPE:
        return manager.get_infrastructure_details(association_id)
    elif association_type == consts.MALWARE_ASSOCIATION_TYPE:
        return manager.get_malware_details(association_id)
    elif association_type == consts.INTRUSION_SET_ASSOCIATION_TYPE:
        return manager.get_intrusionset_details(association_id)
    elif association_type == consts.TOOL_ASSOCIATION_TYPE:
        return manager.get_tool_details(association_id)
    elif association_type == consts.TTP_ASSOCIATION_TYPE:
        return manager.get_ttp_details(association_id)


def continue_operation(
    siemplify: SiemplifyAction,
    manager: ThreatFuseManager,
    create_campaign_entity: bool,
    create_actors_entity: bool,
    create_signature_entity: bool,
    create_vulnerability_entity: bool,
    create_insight: bool,
    create_case_tag: bool,
    stats_limit: int,
):
    """
    Continue fetching association details
    :param siemplify: {SiemplifyAction} SiemplifyAction object
    :param manager: {ThreatFuseManager} ThreatFuse manager object
    :param create_campaign_entity: {bool} True if action should create campaign entities out of founded associations
    :param create_signature_entity: {bool} True if action should create signature entities out of founded associations
    :param create_actors_entity: {bool} True if action should create actor entities out of founded actors
    :param create_vulnerability_entity: {bool} True if action should create CVE entities out of founded actors
    :param create_insight: {bool} True if action should create insight
    :param create_case_tag: {bool} True if action should crate case tags
    :param stats_limit: {int} Max Statistics To Return
    :return: {output message, json result, execution_state}
    """
    json_results = json.loads(siemplify.extract_action_param("additional_data"))
    association_types = json_results["association_type"]

    # Maps association types to True if an entity should be created out of the association type, otherwise map to False
    supported_association_types_mapper = {
        consts.VULNERABILITY_ASSOCIATION_TYPE: create_vulnerability_entity,
        consts.CAMPAIGN_ASSOCIATION_TYPE: create_campaign_entity,
        consts.ACTOR_ASSOCIATION_TYPE: create_actors_entity,
        consts.SIGNATURE_ASSOCIATION_TYPE: create_signature_entity,
    }

    # Total non-fetched associations to process in this run cycle
    num_unprocessed_ids = sum(
        len(association_types[association_type].get("unprocessed_ids", []))
        for association_type in association_types.keys()
    )

    if num_unprocessed_ids > 0:  # continue fetching details
        siemplify.LOGGER.info(
            f"Fetching total of {num_unprocessed_ids} unprocessed related associations. "
        )

        for association_type in association_types.keys():
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                )
                break
            processed = 0  # how many related association processed for association type

            # Get association unprocessed ids
            unprocessed_ids = (
                json_results["association_type"][association_type]
                .get("unprocessed_ids", [])
                .copy()
            )

            if (
                len(unprocessed_ids) <= 0
            ):  # Check if new related association needs to be fetched
                continue

            siemplify.LOGGER.info(
                f"Fetching {len(unprocessed_ids)} related association of type {association_type}"
            )

            for association_id in unprocessed_ids:
                if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                    siemplify.LOGGER.error(
                        f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                    )
                    break
                try:

                    siemplify.LOGGER.info(
                        f"Retrieving details for {association_type} with id {association_id}"
                    )

                    association_details = get_association_detailed_information(
                        manager=manager,
                        association_type=association_type,
                        association_id=association_id,
                    )

                    if stats_limit != 0:  # fetch statistics only if limit is above 0
                        if association_details:
                            try:
                                association_indicators_json = (
                                    manager.get_association_type_indicators_stats(
                                        association_type=association_type,
                                        association_id=association_id,
                                        limit=stats_limit,
                                    )
                                )

                            except Exception as e:
                                siemplify.LOGGER.info(
                                    f"Coudn't fetch IOC details for {association_type} with ID {association_id}. Reason: {e}"
                                )
                                continue
                    else:
                        association_indicators_json = {"statistics": {}}

                    siemplify.LOGGER.info(
                        f"Successfully retrieved details for {association_type} with id {association_id}"
                    )

                    # Mark association as fetched and processed
                    json_results["association_type"][association_type][
                        "unprocessed_ids"
                    ].remove(association_id)

                    # Save association insight
                    if create_insight:
                        json_results["association_type"][association_type][
                            "insights"
                        ].append(
                            association_details.as_insight(
                                number=len(
                                    json_results["association_type"][association_type][
                                        "json_results"
                                    ]
                                )
                                + 1
                            )
                        )

                    # Save json results
                    association_details_json = association_details.as_json()
                    association_details_json.update(association_indicators_json)

                    json_results["association_type"][association_type][
                        "json_results"
                    ].append(association_details_json)

                    # Save csv row
                    json_results["csv"].append(association_details.as_csv())

                    # If association of type Vulnerability, Signatures, Actors, Campaign save identifier and type
                    json_results["entities"] = append_association_type_to_entities(
                        json_results["entities"],
                        supported_association_types_mapper,
                        association_type,
                        association_details.name,
                    )

                    processed += 1
                    json_results["successfully_processed"] += 1
                except Exception as error:
                    # marked as processed event if failed to process
                    siemplify.LOGGER.info(
                        f"Failed to fetch details for association {association_type} with id {association_id}"
                    )
                    siemplify.LOGGER.info(error)
                    processed += 1
                    json_results["association_type"][association_type][
                        "unprocessed_ids"
                    ].remove(association_id)

            if unprocessed_ids:
                siemplify.LOGGER.info(
                    f"Processed {processed} {association_type} details"
                )
                json_results[
                    "total_processed"
                ] += processed  # update total processed associations

        status = EXECUTION_STATE_INPROGRESS
        result_value = json.dumps(json_results)
        output_message = "Waiting for all of the association details to be retrieved"

    else:  # all associations were processed, create CSV table/ Json Results/ insights / Entities/ Case tags and end action execution
        status = EXECUTION_STATE_COMPLETED
        successfully_processed = json_results["successfully_processed"]

        # Create final csv table
        csv_table = json_results.get("csv", [])
        if csv_table:
            siemplify.result.add_data_table(
                title=f"Related Associations", data_table=construct_csv(csv_table)
            )

        # Create final json result for the action
        final_json_results = defaultdict(list)
        for association_type in association_types.keys():
            final_json_results[association_type].extend(
                association_types[association_type].get("json_results", [])
            )

        # Check if json_results exist
        if successfully_processed > 0:
            siemplify.result.add_result_json(final_json_results)

        # Create Entities
        entities = json_results.get("entities")
        if entities:
            for entity in entities:
                siemplify.add_entity_to_case(
                    entity.get("identifier", ""),
                    entity.get("type", ""),
                    is_internal=False,
                    is_suspicous=False,
                    is_enriched=False,
                    is_vulnerable=True,
                    properties={"is_new_entity": True},
                )

        # Create case tags. Tags are the found related associations.
        # Take association names from CSV table. Association name must be assigned
        if create_case_tag and csv_table:
            for tag in csv_table:
                if tag.get("Name", "") and tag.get("Name", "") != consts.NOT_ASSIGNED:
                    siemplify.add_tag(tag.get("Name", ""))

        if (
            create_insight and successfully_processed > 0
        ):  # Create insight if successfully retrieved details
            insight_title = f"Found {len(csv_table)} related associations"
            insight_content = ""
            for association_type in association_types.keys():
                insight_content += "".join(
                    association_types[association_type].get("insights", [])
                )
            siemplify.create_case_insight(
                triggered_by=INTEGRATION_IDENTIFIER,
                title=insight_title,
                content=insight_content,
                entity_identifier="",
                severity=InsightSeverity.INFO,
                insight_type=InsightType.General,
            )

        if (
            successfully_processed > 0
        ):  # check if successfully retrieved some related association details
            result_value = True
            output_message = (
                f"Successfully retrieved related associations from {INTEGRATION_NAME}"
            )
        else:
            result_value = False
            output_message = "No related associations were found."

    return output_message, result_value, status


def start_operation(
    siemplify: SiemplifyAction,
    manager: ThreatFuseManager,
    supported_entities: list,
    search_association_types: list,
    max_associations_to_return: int,
):
    """
    Initial part of the action that get indicator ids for supported entities and fetch related associations ids on the first run.
    :param siemplify: {SiemplifyAction}
    :param manager: {ThreatFuseManager} ThreatFuse manager object
    :param supported_entities: {list} list of supported entities
    :param search_association_types: {list} list of association types
    :param max_associations_to_return: {int} max associations to return per association type
    :return: {output message, json result, execution_state}
    """
    result_value = {
        "association_type": defaultdict(lambda: defaultdict(list)),
        # example:
        #   'association_type': {
        #       <association_type>:{
        #           'unprocessed_ids': [], list of unprocessed ids for association type
        #           'json_results': [], # list of json results of all association that were found for the association type
        #           'insights': [], # list of insights of all associations for the association type <association_type>
        #       }
        #   }
        # list of dictionaries. Each dictionary is a row in a final CSV table for all the associations
        "csv": [],
        # list of dictionaries. Each dictionary has 'identifier' and 'type' keys, representing entity identifier and type
        "entities": [],
        "successfully_processed": 0,  # successfully fetched related associations
        "total_processed": 0,  # total of processed related associations
    }
    associations_to_process = 0
    entity_identifiers = [entity.identifier.strip() for entity in supported_entities]
    siemplify.LOGGER.info(
        f"Retrieving indicators for entities {', '.join(entity_identifiers)}"
    )

    # Get indicators for entities
    indicators = manager.get_indicators(entities=entity_identifiers)
    siemplify.LOGGER.info(
        f"Retrieved indicators {' '.join([str(indicator.id) for indicator in indicators])} for supported entities {', '.join(entity_identifiers)}"
    )
    indicator_ids = [indicator.id for indicator in indicators]

    if indicator_ids:
        # Retrieve latest related associations for each association type
        for association_type in search_association_types:
            siemplify.LOGGER.info(
                f"Getting related associations for association {association_type}"
            )
            try:
                # Get latest related associations for association type
                related_associations = manager.get_related_indicator_associations(
                    association_type=association_type,
                    ids=indicator_ids,
                    sort_by_key="modified_ts_ms",
                    limit=max_associations_to_return,
                    asc=False,
                )
                siemplify.LOGGER.info(
                    f"Successfully received {len(related_associations)} related association ids of type {association_type}"
                )
                if related_associations:
                    associations_to_process += len(related_associations)
                    result_value["association_type"][association_type][
                        "unprocessed_ids"
                    ] = [association.id for association in related_associations]
                    result_value["association_type"][association_type][
                        "json_results"
                    ] = []
                    result_value["association_type"][association_type]["insights"] = []
            except Exception as e:
                siemplify.LOGGER.info(
                    f"Failed to get related associations for association type {association_type}"
                )
                siemplify.LOGGER.info(e)

        if associations_to_process > 0:  # check if some related association was found
            siemplify.LOGGER.info(
                f"Received total of {associations_to_process} related associations to fetch"
            )
            status = EXECUTION_STATE_INPROGRESS
            result_value = json.dumps(result_value)
            output_message = (
                "Waiting for all of the association details to be retrieved"
            )
        else:
            status = EXECUTION_STATE_COMPLETED
            result_value = False
            output_message = "No related associations were found."
    else:
        siemplify.LOGGER.info(
            f"Didn't get indicators for supported entities {', '.join(entity_identifiers)}"
        )
        status = EXECUTION_STATE_COMPLETED
        result_value = False
        output_message = "No related associations were found."

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = (
        f"{INTEGRATION_NAME} - {GET_RELATED_ASSOCIATION_SCRIPT_NAME}"
    )
    mode = "Main" if is_first_run else "Check changes"
    siemplify.LOGGER.info(f"================= {mode} - Param Init =================")

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

    # Action Parameters
    return_campaigns = extract_action_param(
        siemplify,
        param_name="Return Campaigns",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
        default_value=True,
    )

    return_threat_bulletins = extract_action_param(
        siemplify,
        param_name="Return Threat Bulletins",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
        default_value=False,
    )

    return_actors = extract_action_param(
        siemplify,
        param_name="Return Actors",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
        default_value=False,
    )

    return_attack_patterns = extract_action_param(
        siemplify,
        param_name="Return Attack Patterns",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
        default_value=False,
    )

    return_courses_of_action = extract_action_param(
        siemplify,
        param_name="Return Courses Of Action",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
        default_value=False,
    )

    return_identities = extract_action_param(
        siemplify,
        param_name="Return Identities",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
        default_value=False,
    )

    return_incidents = extract_action_param(
        siemplify,
        param_name="Return Incidents",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
        default_value=False,
    )

    return_infrastructure = extract_action_param(
        siemplify,
        param_name="Return Infrastructure",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
        default_value=False,
    )

    return_intrusion_sets = extract_action_param(
        siemplify,
        param_name="Return Intrusion Sets",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
        default_value=False,
    )

    return_malware = extract_action_param(
        siemplify,
        param_name="Return Malware",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
        default_value=False,
    )

    return_signatures = extract_action_param(
        siemplify,
        param_name="Return Signatures",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
        default_value=False,
    )

    return_tools = extract_action_param(
        siemplify,
        param_name="Return Tools",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
        default_value=False,
    )

    return_ttps = extract_action_param(
        siemplify,
        param_name="Return TTPs",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
        default_value=False,
    )

    return_vulnerabilities = extract_action_param(
        siemplify,
        param_name="Return Vulnerabilities",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
        default_value=True,
    )

    create_campaign_entity = extract_action_param(
        siemplify,
        param_name="Create Campaign Entity",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
        default_value=False,
    )

    create_actors_entity = extract_action_param(
        siemplify,
        param_name="Create Actors Entity",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
        default_value=False,
    )

    create_signature_entity = extract_action_param(
        siemplify,
        param_name="Create Signature Entity",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
        default_value=False,
    )

    create_vulnerability_entity = extract_action_param(
        siemplify,
        param_name="Create Vulnerability Entity",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
        default_value=False,
    )

    create_insight = extract_action_param(
        siemplify,
        param_name="Create Insight",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
        default_value=True,
    )

    create_case_tag = extract_action_param(
        siemplify,
        param_name="Create Case Tag",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
        default_value=True,
    )

    max_associations_to_return = extract_action_param(
        siemplify,
        param_name="Max Associations To Return",
        is_mandatory=False,
        print_value=True,
        default_value=consts.MAX_ASSOCIATIONS_TO_RETURN_DEFAULT,
        input_type=int,
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    if max_associations_to_return < 0:
        siemplify.LOGGER.info(
            f'"Max Associations To Return" must be non-negative. Using default of {consts.MAX_ASSOCIATIONS_TO_RETURN_DEFAULT}.'
        )
        max_associations_to_return = consts.MAX_ASSOCIATIONS_TO_RETURN_DEFAULT

    result_value = False

    try:
        max_stats_to_return = extract_action_param(
            siemplify,
            param_name="Max Statistics To Return",
            is_mandatory=False,
            print_value=True,
            input_type=int,
        )

        if max_stats_to_return and max_stats_to_return < 0:
            siemplify.LOGGER.info(
                f'"Max Statistics To Return" must be non-negative. Using default of {consts.MAX_STATICSTICS_TO_RETURN_DEFAULT}.'
            )
            max_stats_to_return = consts.MAX_STATICSTICS_TO_RETURN_DEFAULT

        manager = ThreatFuseManager(
            web_root=web_root,
            api_root=api_root,
            api_key=api_key,
            email_address=email_address,
            verify_ssl=verify_ssl,
        )

        if is_first_run:
            # Return list of association types to search
            search_association_types = get_search_association_types(
                {
                    "Threat Bulletins": return_threat_bulletins,
                    "Actors": return_actors,
                    "Attack Patterns": return_attack_patterns,
                    "Campaigns": return_campaigns,
                    "Courses Of Action": return_courses_of_action,
                    "Identities": return_identities,
                    "Incidents": return_incidents,
                    "Infrastructure": return_infrastructure,
                    "Intrusion Sets": return_intrusion_sets,
                    "Malware": return_malware,
                    "Signatures": return_signatures,
                    "Tools": return_tools,
                    "TTPs": return_ttps,
                    "Vulnerabilities": return_vulnerabilities,
                }
            )

            supported_entities = []  # list of supported entities.

            # Process entities on first run
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
                supported_entities.append(entity)

            if supported_entities:
                siemplify.LOGGER.info(
                    f"Supported entities are: {','.join([entity.identifier for entity in supported_entities])}"
                )
                output_message, result_value, status = start_operation(
                    siemplify=siemplify,
                    manager=manager,
                    supported_entities=supported_entities,
                    search_association_types=search_association_types,
                    max_associations_to_return=max_associations_to_return,
                )
            else:
                siemplify.LOGGER.info("No related associations were found")
                output_message = "No related associations were found"
                status = EXECUTION_STATE_COMPLETED

        else:
            output_message, result_value, status = continue_operation(
                siemplify=siemplify,
                manager=manager,
                create_campaign_entity=create_campaign_entity,
                create_actors_entity=create_actors_entity,
                create_signature_entity=create_signature_entity,
                create_vulnerability_entity=create_vulnerability_entity,
                create_insight=create_insight,
                create_case_tag=create_case_tag,
                stats_limit=max_stats_to_return,
            )

    except ThreatFuseValidationException as error:
        siemplify.LOGGER.error(error)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        output_message = f"{error}"

    except Exception as error:
        siemplify.LOGGER.error(
            f'Error executing action "{GET_RELATED_ASSOCIATION_SCRIPT_NAME}". Reason: {error}'
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        output_message = f'Error executing action "{GET_RELATED_ASSOCIATION_SCRIPT_NAME}". Reason: {error}'

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
