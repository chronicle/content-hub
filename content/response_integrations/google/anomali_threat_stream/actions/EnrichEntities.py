from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from TIPCommon import flat_dict_to_csv
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.Siemplify import InsightSeverity, InsightType
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from ..core.AnomaliThreatStreamManager import AnomaliManager
from ..core.exceptions import (
    AnomaliManagerException,
    AnomaliThreatStreamInvalidCredentialsException,
)
from ..core.constants import (
    INTEGRATION_NAME,
    ENRICH_ENTITIES_SCRIPT_NAME,
    MAX_CONFIDENCE,
    MIN_CONFIDENCE,
    SEVERITIES,
    SPACE_CHARACTER,
    SEVERITIES_ORDER,
    INTEGRATION_IDENTIFIER,
    URL_INDICATOR_TYPE,
)
from ..core.utils import get_entity_original_identifier

SUPPORTED_ENTITIES = [
    EntityTypes.FILEHASH,
    EntityTypes.ADDRESS,
    EntityTypes.URL,
    EntityTypes.USER,
    EntityTypes.DOMAIN,
    EntityTypes.HOSTNAME,
]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_ENTITIES_SCRIPT_NAME
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
        param_name="Api Root",
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

    severity_threshold = extract_action_param(
        siemplify, param_name="Severity Threshold", is_mandatory=True, print_value=True
    )
    confidence_threshold = extract_action_param(
        siemplify,
        param_name="Confidence Threshold",
        is_mandatory=True,
        input_type=int,
        print_value=True,
    )
    ignore_false_positive_status = extract_action_param(
        siemplify,
        param_name="Ignore False Positive Status",
        input_type=bool,
        print_value=True,
        default_value=False,
    )
    add_threat_type_to_case = extract_action_param(
        siemplify,
        param_name="Add Threat Type To Case",
        input_type=bool,
        print_value=True,
        default_value=False,
    )
    create_insight = extract_action_param(
        siemplify,
        param_name="Create Insight",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
        default_value=False,
    )
    suspicious_insight_only = extract_action_param(
        siemplify,
        param_name="Only Suspicious Entity Insight",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
        default_value=False,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    supported_entities, indicators, enriched_entities, failed_entities = [], [], [], []

    json_results = {"results": {}, "is_risky": False}
    status = EXECUTION_STATE_COMPLETED
    result_value = False
    output_message = ""

    try:
        if (
            confidence_threshold > MAX_CONFIDENCE
            or confidence_threshold < MIN_CONFIDENCE
        ):
            raise Exception(
                "'Confidence Threshold' value should be in range from "
                f"{MIN_CONFIDENCE} to {MAX_CONFIDENCE}"
            )

        if severity_threshold not in SEVERITIES:
            raise Exception(
                f"Severity Threshold' value should be one of {SEVERITIES.keys()}"
            )

        # translate to numeric severity
        numeric_severity_threshold = SEVERITIES_ORDER[SEVERITIES[severity_threshold]]

        manager = AnomaliManager(
            web_root=web_root,
            api_root=api_root,
            api_key=api_key,
            username=email_address,
            verify_ssl=verify_ssl,
        )

        for entity in siemplify.target_entities:
            entity_identifier = get_entity_original_identifier(entity)
            if entity.entity_type not in SUPPORTED_ENTITIES:
                siemplify.LOGGER.info(
                    f"Entity {entity_identifier} is of unsupported type. Skipping."
                )
                continue

            if SPACE_CHARACTER in entity.identifier.strip():
                siemplify.LOGGER.info(
                    f"Entity {entity_identifier} contains a ' ' character (space), "
                    "which is not supported for the action's supported entities."
                )
                continue

            supported_entities.append(entity)

        siemplify.LOGGER.info(
            "Supported entities are: "
            f"{', '.join([get_entity_original_identifier(entity) for entity in supported_entities])}"
        )

        if supported_entities:
            try:
                siemplify.LOGGER.info(f"Retrieving indicators.")

                # Get indicators for entities
                indicators = manager.get_indicators(
                    entities=[
                        get_entity_original_identifier(entity)
                        for entity in supported_entities
                    ]
                )

            except AnomaliThreatStreamInvalidCredentialsException as e:
                raise e

            except AnomaliManagerException as e:
                siemplify.LOGGER.error(f"Failed to get indicators.")
                siemplify.LOGGER.exception(e)

        else:
            siemplify.LOGGER.info("No supported entities found.")

        if indicators:  # check if retrieved indicators
            # Map each entity to its indicators
            indicator_groups = manager.parser.match_entity_to_indicators(
                indicators, supported_entities
            )

            for indicator_group in indicator_groups:
                try:
                    # Process each indicator group separately
                    siemplify.LOGGER.info(
                        "Processing indicators of entity "
                        f"{indicator_group.entity.identifier}"
                    )
                    is_suspicious = False

                    if not indicator_group.indicators:
                        siemplify.LOGGER.info(
                            "No indicators were found for entity "
                            f"{indicator_group.entity.identifier}. Skipping."
                        )
                        failed_entities.append(indicator_group.entity)
                        continue

                    indicator_group.entity.additional_properties.update(
                        indicator_group.as_enrichment()
                    )
                    indicator_group.entity.is_enriched = True
                    siemplify.result.add_entity_table(
                        indicator_group.entity.identifier,
                        flat_dict_to_csv(indicator_group.as_csv()),
                    )
                    enriched_entities.append(indicator_group.entity)

                    siemplify.LOGGER.info(
                        "Successfully enriched entity "
                        f"{indicator_group.entity.identifier} with indicators data."
                    )

                    # If enabled, false positive status gets ignored and mark
                    # the entity as suspicious based on the “Severity
                    # Threshold” and “Confidence Threshold”. If disabled,
                    # entities are never labeled as suspicious, even if they
                    # meet the threshold.
                    if (
                        indicator_group.is_false_positive
                        and not ignore_false_positive_status
                    ):
                        siemplify.LOGGER.info(
                            "Latest indicator for entity "
                            f"{indicator_group.entity.identifier} "
                            "is false positive. Entity won't be checked if "
                            "suspicious."
                        )

                    else:
                        if (
                            indicator_group.numeric_severity
                            >= numeric_severity_threshold
                            and indicator_group.confidence >= confidence_threshold
                        ):
                            siemplify.LOGGER.info(
                                "Severity and confidence passed threshold. "
                                f"Marking {indicator_group.entity.identifier} as "
                                "suspicious."
                            )
                            indicator_group.entity.is_suspicious = True
                            is_suspicious = True
                            json_results["is_risky"] = True

                    json_results["results"][indicator_group.entity.identifier] = [
                        {**indicator.as_json(), "is_risky": is_suspicious}
                        for indicator in indicator_group.indicators
                    ]
                    siemplify.LOGGER.info(
                        "Fetching analysis links for entity "
                        f"{indicator_group.entity.identifier}"
                    )
                    analysis_links = manager.get_analysis_links(
                        indicator_group.entity.identifier
                    )

                    siemplify.LOGGER.info(
                        f"Found {len(analysis_links)} analysis links."
                    )

                    if analysis_links:
                        siemplify.result.add_data_table(
                            "Related Analysis Links: "
                            f"{indicator_group.entity.identifier}",
                            construct_csv([link.as_csv() for link in analysis_links]),
                        )

                    if add_threat_type_to_case:
                        siemplify.LOGGER.info(
                            "Adding threat types of the indicators of "
                            f"{indicator_group.entity.identifier} as tags to case."
                        )
                        for indicator in indicator_group.indicators:
                            siemplify.add_tag(indicator.threat_type)

                    if create_insight and (
                        not suspicious_insight_only or is_suspicious
                    ):
                        try:
                            if (
                                indicator_group.entity.entity_type
                                == EntityTypes.ADDRESS
                            ):
                                siemplify.LOGGER.info(
                                    "Fetching intel details for "
                                    f"{indicator_group.entity.identifier}"
                                )
                                intel_details = manager.get_intel_details(
                                    type=indicator_group.latest_indicator.type,
                                    value=indicator_group.entity.identifier,
                                )

                                siemplify.LOGGER.info(
                                    "Adding insight for entity "
                                    f"{indicator_group.entity.identifier}"
                                )
                                siemplify.create_case_insight(
                                    triggered_by=INTEGRATION_IDENTIFIER,
                                    title="IP Details",
                                    content=indicator_group.as_ip_insight(
                                        intel_details
                                    ),
                                    entity_identifier=indicator_group.entity.identifier,
                                    severity=InsightSeverity.INFO,
                                    insight_type=InsightType.Entity,
                                )

                            elif indicator_group.entity.entity_type == EntityTypes.URL:
                                siemplify.LOGGER.info(
                                    "Fetching intel details for "
                                    f"{indicator_group.entity.identifier} "
                                    f"{indicator_group.latest_indicator.type}"
                                )
                                intel_details = manager.get_intel_details(
                                    type=indicator_group.latest_indicator.type,
                                    value=indicator_group.entity.identifier,
                                )

                                siemplify.LOGGER.info(
                                    "Adding insight for entity "
                                    f"{indicator_group.entity.identifier}"
                                )

                                if (
                                    indicator_group.latest_indicator.type
                                    == URL_INDICATOR_TYPE
                                ):
                                    # Indicator is of type URL
                                    siemplify.create_case_insight(
                                        triggered_by=INTEGRATION_IDENTIFIER,
                                        title="URL Details",
                                        content=indicator_group.as_url_insight(
                                            intel_details
                                        ),
                                        entity_identifier=indicator_group.entity.identifier,
                                        severity=InsightSeverity.INFO,
                                        insight_type=InsightType.Entity,
                                    )

                                else:
                                    # Indicator is of type domain
                                    siemplify.create_case_insight(
                                        triggered_by=INTEGRATION_IDENTIFIER,
                                        title="Domain Details",
                                        content=indicator_group.as_domain_insight(
                                            intel_details
                                        ),
                                        entity_identifier=indicator_group.entity.identifier,
                                        severity=InsightSeverity.INFO,
                                        insight_type=InsightType.Entity,
                                    )

                            elif (
                                indicator_group.entity.entity_type
                                == EntityTypes.FILEHASH
                            ):
                                siemplify.LOGGER.info(
                                    "Adding insight for entity "
                                    f"{indicator_group.entity.identifier}"
                                )
                                siemplify.create_case_insight(
                                    triggered_by=INTEGRATION_IDENTIFIER,
                                    title="Hash Details",
                                    content=indicator_group.as_hash_insight(),
                                    entity_identifier=indicator_group.entity.identifier,
                                    severity=InsightSeverity.INFO,
                                    insight_type=InsightType.Entity,
                                )

                            else:
                                # Entity is an email address
                                siemplify.LOGGER.info(
                                    "Adding insight for entity "
                                    f"{indicator_group.entity.identifier}"
                                )
                                siemplify.create_case_insight(
                                    triggered_by=INTEGRATION_IDENTIFIER,
                                    title="Email Address Details",
                                    content=indicator_group.as_email_insight(),
                                    entity_identifier=indicator_group.entity.identifier,
                                    severity=InsightSeverity.INFO,
                                    insight_type=InsightType.Entity,
                                )

                        except Exception as e:
                            siemplify.LOGGER.error(
                                "Failed to add insight for entity "
                                f"{indicator_group.entity.identifier}"
                            )
                            siemplify.LOGGER.exception(e)

                except Exception as e:
                    siemplify.LOGGER.error(
                        "An error occurred on entity "
                        f"{indicator_group.entity.identifier}"
                    )
                    siemplify.LOGGER.exception(e)
                    failed_entities.append(indicator_group.entity)

        else:
            siemplify.LOGGER.info("No indicators were found.")

        if enriched_entities:
            output_message += (
                "Successfully enriched the following entities using {}: \n{}".format(
                    INTEGRATION_NAME,
                    "\n".join([entity.identifier for entity in enriched_entities]),
                )
            )
            siemplify.update_entities(enriched_entities)
            result_value = "true"

            if failed_entities:
                output_message += (
                    "\n\nAction was not able to enrich the following entities "
                    "using {}: \n{}\n"
                ).format(
                    INTEGRATION_NAME,
                    "\n".join([entity.identifier for entity in failed_entities]),
                )

        else:
            siemplify.LOGGER.info("\n No entities were enriched.")
            output_message = "No entities were enriched."

        json_results["results"] = convert_dict_to_json_result_dict(
            json_results["results"]
        )
        siemplify.result.add_result_json(json_results)

    except Exception as error:
        output_message = (
            f'Error executing action "{ENRICH_ENTITIES_SCRIPT_NAME}". Reason: {error}'
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
