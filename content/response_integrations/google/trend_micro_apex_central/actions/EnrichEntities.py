from __future__ import annotations
from collections import defaultdict
from urllib.parse import urlparse

import requests
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes, InsightType, InsightSeverity
from soar_sdk.SiemplifyUtils import (
    output_handler,
    convert_dict_to_json_result_dict,
    unix_now,
    convert_unixtime_to_datetime,
)
from ..core.TrendMicroApexCentralManager import TrendMicroApexCentralManager
from ..core.consts import (
    INTEGRATION_DISPLAY_NAME,
    INTEGRATION_IDENTIFIER,
    ENRICH_ENTITIES_SCRIPT_NAME,
    SHA1_HASH_LENGTH,
    UDSO_DOMAIN_TYPE,
    SUPPORTED_UDSO_ENTITY_TYPES,
    SUPPORTED_ENDPOINTS_ENTITY_TYPES_LOWERED,
    ENTITY_TYPE_TO_UDSO_TYPE,
    FOUND_UDSO_CSV_TABLE_TITLE,
    FOUND_ENDPOINTS_CSV_TABLE_TITLE,
    UDSO_GENERAL_INSIGHT_TITLE,
    ENDPOINTS_GENERAL_INSIGHT_TITLE,
)
from ..core.exceptions import TrendMicroApexCentralAuthorizationError

# Fix of misalignment of MAC entity type
EntityTypes.MACADDRESS = EntityTypes.MACADDRESS.lower()
SUPPORTED_ENTITIES = [
    EntityTypes.URL,
    EntityTypes.ADDRESS,
    EntityTypes.FILEHASH,
    EntityTypes.HOSTNAME,
    EntityTypes.MACADDRESS,
]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_IDENTIFIER} - {ENRICH_ENTITIES_SCRIPT_NAME}"
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Integration configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    application_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Application ID",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Key",
        is_mandatory=True,
        print_value=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    # Action parameters
    create_endpoint_insight = extract_action_param(
        siemplify,
        param_name="Create Endpoint Insight",
        input_type=bool,
        is_mandatory=False,
        print_value=True,
        default_value=True,
    )
    create_udso_insight = extract_action_param(
        siemplify,
        param_name="Create UDSO Insight",
        input_type=bool,
        is_mandatory=False,
        print_value=True,
        default_value=True,
    )
    mark_udso_entities = extract_action_param(
        siemplify,
        param_name="Mark UDSO Entities",
        input_type=bool,
        is_mandatory=False,
        print_value=True,
        default_value=True,
    )
    extract_domain = extract_action_param(
        siemplify,
        param_name="Extract Domain",
        input_type=bool,
        is_mandatory=False,
        print_value=True,
        default_value=False,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = False
    output_message = ""

    successful_entities = []
    failed_entities = []
    json_results = defaultdict(dict)
    enriched_endpoints = []
    found_udso_csv_table = []
    found_endpoints_csv_table = []
    general_insight_for_udso = []
    general_insight_for_endpoints = []

    try:
        manager = TrendMicroApexCentralManager(
            api_root=api_root,
            application_id=application_id,
            api_key=api_key,
            verify_ssl=verify_ssl,
        )
        supported_entities = [
            entity
            for entity in siemplify.target_entities
            if (entity.entity_type in SUPPORTED_ENTITIES)
            or (entity.entity_type.lower() == EntityTypes.MACADDRESS)
        ]

        for entity in supported_entities:
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            if entity.entity_type == EntityTypes.FILEHASH:
                if len(entity.identifier) != SHA1_HASH_LENGTH:
                    siemplify.LOGGER.info(
                        f"File hash of {entity.identifier} is of unsupported hash type. Only SHA-1 hashes are supported. "
                        f"Skipping.."
                    )
                    continue
            entity.identifier = entity.identifier.strip()
            entity_enriched = False

            # Fetch UDSO entity details
            if entity.entity_type in SUPPORTED_UDSO_ENTITY_TYPES and entity.identifier:
                try:
                    if extract_domain and entity.entity_type == EntityTypes.URL:
                        udso_identifier = urlparse(entity.identifier).netloc
                        if not udso_identifier:
                            siemplify.LOGGER.info(
                                f"Failed to extract domain for entity {entity.identifier} - using entity identifier"
                            )
                            udso_identifier = entity.identifier
                        udso_type = UDSO_DOMAIN_TYPE
                    else:
                        udso_type = ENTITY_TYPE_TO_UDSO_TYPE.get(entity.entity_type)
                        udso_identifier = entity.identifier
                    siemplify.LOGGER.info(
                        f"Fetching UDSO details of entity: {udso_identifier}"
                    )
                    udso_details = manager.get_udso_entry(
                        udso_type=udso_type, udso_entity=udso_identifier
                    )
                    if udso_details:
                        siemplify.LOGGER.info(f"Successfully fetched UDSO details")
                        found_udso_csv_table.append(udso_details.to_csv())
                        json_results[entity.identifier] = udso_details.to_json()
                        entity.additional_properties.update(
                            udso_details.to_enrichment_data()
                        )
                        entity.is_enriched = True

                        if create_udso_insight:
                            general_insight_for_udso.append((udso_details.to_insight()))
                        if mark_udso_entities:
                            siemplify.LOGGER.info(
                                f"Marking entity {entity.identifier} as suspicious"
                            )
                            entity.is_suspicious = True
                        successful_entities.append(entity)
                        entity_enriched = True
                    else:
                        siemplify.LOGGER.info(f"No UDSO details were found")
                except (
                    requests.exceptions.ConnectionError,
                    TrendMicroApexCentralAuthorizationError,
                ):
                    raise
                except Exception as error:
                    siemplify.LOGGER.error(
                        f"Failed to fetch UDSO details for entity {entity.identifier}"
                    )
                    siemplify.LOGGER.exception(error)

            # Fetch endpoint details
            if entity.entity_type.lower() in SUPPORTED_ENDPOINTS_ENTITY_TYPES_LOWERED:
                try:
                    siemplify.LOGGER.info(
                        f"Fetching endpoint details of entity: {entity.identifier}"
                    )
                    endpoint_details = None
                    if entity.entity_type.lower() == EntityTypes.MACADDRESS:
                        endpoint_details = manager.get_security_agent(
                            mac_address=entity.identifier
                        )
                    if entity.entity_type == EntityTypes.HOSTNAME:
                        endpoint_details = manager.get_security_agent(
                            host_name=entity.identifier
                        )
                    if entity.entity_type == EntityTypes.ADDRESS:
                        endpoint_details = manager.get_security_agent(
                            ip_address=entity.identifier
                        )

                    if endpoint_details:
                        siemplify.LOGGER.info(f"Successfully fetched endpoint details")
                        endpoint_has_sensor_enabled = False
                        # Check if endpoint has sensor enabled/installed
                        if (
                            entity.entity_type.lower() == EntityTypes.MACADDRESS
                            or entity.entity_type == EntityTypes.HOSTNAME
                        ):
                            endpoints_with_enabled_sensors = manager.list_security_agents_with_sensor_enabled(
                                filters=[
                                    {
                                        "type": 1,
                                        "value": endpoint_details.host_name,  # partial match
                                    }
                                ]
                            )
                            for endpoint in endpoints_with_enabled_sensors:
                                if endpoint.machine_name == endpoint_details.host_name:
                                    endpoint_has_sensor_enabled = True

                        elif entity.entity_type == EntityTypes.ADDRESS:
                            endpoints_with_enabled_sensors = (
                                manager.list_security_agents_with_sensor_enabled(
                                    filters=[
                                        {
                                            "type": 4,
                                            "value": [
                                                entity.identifier,
                                                entity.identifier,
                                            ],
                                        }
                                    ]
                                )
                            )
                            if endpoints_with_enabled_sensors:
                                endpoint_has_sensor_enabled = True

                        endpoint_details.set_if_has_endpoint_sensor(
                            endpoint_has_sensor_enabled
                        )
                        entity.additional_properties.update(
                            endpoint_details.to_enrichment_data()
                        )
                        entity.is_enriched = True

                        if not entity_enriched:
                            successful_entities.append(entity)
                            entity_enriched = True

                        # Check if same endpoint was already created, don't create case wall tables, json results, insights
                        if (
                            endpoint_details.ip_address_list in enriched_endpoints
                            or endpoint_details.host_name in enriched_endpoints
                            or endpoint_details.mac_address_list in enriched_endpoints
                        ):
                            siemplify.LOGGER.info(
                                f"Results for endpoint {entity.identifier} were already created"
                            )
                            continue
                        enriched_endpoints.append(entity.identifier)
                        found_endpoints_csv_table.append(endpoint_details.to_csv())
                        json_results[entity.identifier].update(
                            endpoint_details.to_json()
                        )

                        if create_endpoint_insight:
                            general_insight_for_endpoints.append(
                                endpoint_details.to_insight(entity.identifier)
                            )

                    else:
                        siemplify.LOGGER.info("No endpoint details were found")
                except (
                    requests.exceptions.ConnectionError,
                    TrendMicroApexCentralAuthorizationError,
                ):
                    raise
                except Exception as error:
                    siemplify.LOGGER.error(
                        f"Failed to endpoint details for entity {entity.identifier}"
                    )
                    siemplify.LOGGER.exception(error)

            if not entity_enriched:
                failed_entities.append(entity)

        if successful_entities:
            output_message += "Successfully retrieved information about the following entities from {}:\n  {}\n\n".format(
                INTEGRATION_DISPLAY_NAME,
                "\n  ".join(entity.identifier for entity in successful_entities),
            )
            result_value = True
            siemplify.update_entities(successful_entities)

            if json_results:
                siemplify.result.add_result_json(
                    convert_dict_to_json_result_dict(json_results)
                )

            if general_insight_for_endpoints:
                endpoints_insight_title = f"\nFound information about {len(general_insight_for_endpoints)} {'endpoints' if len(general_insight_for_endpoints) > 1 else 'endpoint'}.\n"

                siemplify.create_case_insight(
                    triggered_by=INTEGRATION_IDENTIFIER,
                    title=ENDPOINTS_GENERAL_INSIGHT_TITLE,
                    content=endpoints_insight_title
                    + "".join(general_insight_for_endpoints),
                    entity_identifier="",
                    severity=InsightSeverity.INFO,
                    insight_type=InsightType.General,
                )

            if general_insight_for_udso:
                udso_insights_title = f"\nFound information about {len(general_insight_for_udso)} User-Defined Suspicious {'Objects' if len(general_insight_for_udso) > 1 else 'Object'}.\n"

                siemplify.create_case_insight(
                    triggered_by=INTEGRATION_IDENTIFIER,
                    title=UDSO_GENERAL_INSIGHT_TITLE,
                    content=udso_insights_title + "".join(general_insight_for_udso),
                    entity_identifier="",
                    severity=InsightSeverity.INFO,
                    insight_type=InsightType.General,
                )
            if found_udso_csv_table:
                siemplify.result.add_data_table(
                    FOUND_UDSO_CSV_TABLE_TITLE, construct_csv(found_udso_csv_table)
                )

            if found_endpoints_csv_table:
                siemplify.result.add_data_table(
                    FOUND_ENDPOINTS_CSV_TABLE_TITLE,
                    construct_csv(found_endpoints_csv_table),
                )
        else:
            output_message += f"No entities were enriched using information from {INTEGRATION_DISPLAY_NAME}."

        if successful_entities and failed_entities:
            output_message += "Action wasn't able to retrieve information about the following entities from {}:\n  {}\n\n".format(
                INTEGRATION_DISPLAY_NAME,
                "\n  ".join([entity.identifier for entity in failed_entities]),
            )

    except Exception as error:
        output_message = (
            f'Error executing action "{ENRICH_ENTITIES_SCRIPT_NAME}". Reason: {error}.'
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
