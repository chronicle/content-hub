from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.AnomaliManager import AnomaliManager
from ..core.constants import INTEGRATION_NAME, GET_THREAT_INFO_SCRIPT_NAME, EMAIL_TYPE
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.utils import (
    get_entity_original_identifier,
    extend_list,
    get_existing_list,
    get_entity_type,
    get_severity_score,
)

ENTITY_TYPE_WITH_KEY_MAPPING = {
    EntityTypes.ADDRESS: "ip_addresses",
    EntityTypes.URL: "urls",
    EntityTypes.FILEHASH: "hashes",
    EMAIL_TYPE: "emails",
}

SUPPORTED_ENTITY_TYPES = list(ENTITY_TYPE_WITH_KEY_MAPPING.keys())
SEVERITY_KEY = "severity"
CONFIDENCE_KEY = "confidence"
ENRICHMENT_TABLE_PREFIX = "Anomali_Info"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_THREAT_INFO_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Root"
    )
    username = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Username"
    )
    api_key = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Key"
    )
    limit = (
        extract_action_param(
            siemplify,
            param_name="Limit",
            default_value=10,
            is_mandatory=True,
            print_value=True,
            input_type=int,
        )
        or None
    )
    severity = extract_action_param(
        siemplify, param_name="Severity Threshold", print_value=True
    )
    confidence_threshold = extract_action_param(
        siemplify,
        param_name="Confidence Threshold",
        default_value=50,
        print_value=True,
        input_type=int,
    )
    ignore_falsepos_status = extract_action_param(
        siemplify,
        param_name="Ignore False Positive Status",
        default_value=False,
        print_value=True,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    success_entities, failed_entities, entities_to_update, json_result, csv_result = (
        [],
        [],
        [],
        {},
        {},
    )

    try:
        severity_threshold = get_severity_score(severity)

        manager = AnomaliManager(
            api_root=api_root,
            username=username,
            api_key=api_key,
            logger=siemplify.LOGGER,
        )

        suitable_entities = {
            get_entity_original_identifier(entity): entity
            for entity in siemplify.target_entities
            if get_entity_type(entity) in SUPPORTED_ENTITY_TYPES
        }

        entities_with_keys = {key: [] for key in ENTITY_TYPE_WITH_KEY_MAPPING.values()}

        for entity_identifier, entity in suitable_entities.items():
            get_existing_list(
                entities_with_keys,
                ENTITY_TYPE_WITH_KEY_MAPPING[get_entity_type(entity)],
            ).append(entity_identifier)

        for entities in entities_with_keys.values():
            for entity_identifier in entities:
                entity = suitable_entities[entity_identifier]
                active_threats = []

                siemplify.LOGGER.info(f"Started processing entity: {entity_identifier}")

                threats = manager.get_threat_info(entity_identifier, limit=limit)

                if not threats:
                    failed_entities.append(entity_identifier)
                    siemplify.LOGGER.info(
                        f"Finish processing entity: {entity_identifier}"
                    )
                    continue

                for count, threat in enumerate(threats, 1):
                    if threat.is_active:
                        active_threats.append(threat)

                    get_existing_list(csv_result, entity_identifier).append(
                        threat.to_csv()
                    )

                entity_data_ref = json_result[entity_identifier] = {}

                extend_list(
                    entity_data_ref,
                    key="Info",
                    extend_with=[threat.to_json() for threat in threats],
                )

                success_entities.append(entity_identifier)

                if not threats:
                    siemplify.LOGGER.info("No threats found after filtering by status.")
                    siemplify.LOGGER.info(
                        f"Finish processing entity: {entity_identifier}"
                    )
                    continue

                threats_for_enrichment = []

                if len(threats) == 1:
                    threat = threats[-1]
                    threat_severity, threat_confidence = (
                        threat.severity_score,
                        threat.confidence,
                    )
                    threats_for_enrichment.append(threat)

                elif bool(active_threats):
                    active_threats.sort(key=lambda _threat: _threat.severity_score)
                    # threat with highest severity
                    threat_severity = active_threats[-1].severity_score
                    active_threats_confidence = sum(
                        [active_threat.confidence for active_threat in active_threats]
                    )
                    # average confidence
                    threat_confidence = active_threats_confidence / len(active_threats)
                    threats_for_enrichment.extend(active_threats)

                # if we have multiple threats but no one is active: use the newest threat
                else:
                    threat = sorted(threats, key=lambda _threat: _threat.modified_ts)[
                        -1
                    ]
                    threat_severity, threat_confidence = (
                        threat.severity_score,
                        threat.confidence,
                    )
                    threats_for_enrichment.append(threat)

                if (
                    threat_confidence >= confidence_threshold
                    and threat_severity >= severity_threshold
                    and ignore_falsepos_status
                ):
                    entity.is_suspicious = True
                if threats_for_enrichment:
                    entity.additional_properties.update(
                        add_enrichment_table_prefix(
                            get_enrichment_table_from_threads(threats_for_enrichment)
                        )
                    )
                    entity.is_enriched = True
                entities_to_update.append(entity)

                siemplify.LOGGER.info(f"Finish processing entity: {entity_identifier}")

        if entities_to_update:
            siemplify.update_entities(entities_to_update)

        if success_entities:
            for entity_identifier, threats in csv_result.items():
                siemplify.result.add_entity_table(
                    f"Anomali Info {entity_identifier}", construct_csv(threats)
                )
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_result)
            )

            output_message = (
                f"Successfully returned information about the following entities from {INTEGRATION_NAME}"
                f' ThreatStream: {", ".join(success_entities)}\n'
            )
            if failed_entities:
                output_message += (
                    "Action wasn't able to return information about the following entities from "
                    f'{INTEGRATION_NAME} ThreatStream: {", ".join(failed_entities)}\n'
                )
        else:
            result_value = False
            output_message = "No entities were enriched."
    except Exception as e:
        output_message = (
            f"Error executing action '{GET_THREAT_INFO_SCRIPT_NAME}'. Reason: {e}"
        )
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


def add_enrichment_table_prefix(table_data):
    result = {}
    for key, value in table_data.items():
        result[f"{ENRICHMENT_TABLE_PREFIX}_{key}"] = value

    return result


def get_enrichment_table_from_threads(threats_for_enrichment):
    multi_value_dict = {}
    result = {}
    for threat in threats_for_enrichment:
        for key, value in threat.get_enrichment_table().items():
            if not multi_value_dict.get(key):
                multi_value_dict[key] = []
            multi_value_dict[key].append(value)

    for key, values in multi_value_dict.items():
        if key == SEVERITY_KEY:
            result[key] = max(
                {severity: get_severity_score(severity) for severity in set(values)}
            )
        elif key == CONFIDENCE_KEY:
            result[key] = int(sum(values) / len(values))
        else:
            result[key] = ", ".join([str(value) for value in set(values) if value])
    return result


if __name__ == "__main__":
    main()
