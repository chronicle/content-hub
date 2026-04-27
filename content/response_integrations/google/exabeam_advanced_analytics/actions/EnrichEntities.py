from __future__ import annotations
import datetime

from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

from ..core.ExabeamAdvancedAnalyticsManager import ExabeamAdvancedAnalyticsManager
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.Siemplify import InsightSeverity, InsightType
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    output_handler,
    utc_now,
    unix_now,
    convert_unixtime_to_datetime,
    convert_datetime_to_unix_time,
    convert_dict_to_json_result_dict,
)
from ..core.consts import (
    INTEGRATION_NAME,
    INTEGRATION_DISPLAY_NAME,
    ENRICH_ENTITIES_SCRIPT_NAME,
    DEFAULT_EVENT_TIME_FRAME_HOURS,
    DEFAULT_MAX_COMMENTS_TO_RETURN,
    LOWEST_EVENT_RISK_SCORE,
    ENTITY_USER_TYPE,
    ENTITY_ASSET_TYPE,
    EVENT_TIME_FRAME_BUFFER_HOURS,
)
from ..core.utils import convert_hours_to_milliseconds, is_notable_user, is_notable_asset

SUPPORTED_ENTITIES = [EntityTypes.USER, EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {ENRICH_ENTITIES_SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # Integration configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )

    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        is_mandatory=True,
        print_value=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    # Action configuration
    return_entity_timeline = extract_action_param(
        siemplify,
        param_name="Return Entity Timeline",
        is_mandatory=True,
        print_value=True,
        input_type=bool,
        default_value=True,
    )
    only_anomaly_events = extract_action_param(
        siemplify,
        param_name="Only Anomaly Events",
        is_mandatory=False,
        print_value=True,
        input_type=bool,
        default_value=True,
    )
    return_comments = extract_action_param(
        siemplify,
        param_name="Return Comments",
        is_mandatory=False,
        print_value=True,
        input_type=bool,
        default_value=True,
    )
    create_insight = extract_action_param(
        siemplify,
        param_name="Create Insight",
        is_mandatory=False,
        print_value=True,
        input_type=bool,
        default_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    enriched_entities = []
    failed_entities = []
    json_results = {}
    output_message = ""

    result_value = False
    status = EXECUTION_STATE_COMPLETED

    try:
        lowest_event_risk_score_to_fetch = extract_action_param(
            siemplify,
            param_name="Lowest Event Risk Score To Fetch",
            is_mandatory=False,
            print_value=True,
            input_type=int,
            default_value=None,
        )
        event_time_frame = extract_action_param(
            siemplify,
            param_name="Event Time Frame",
            is_mandatory=False,
            print_value=True,
            input_type=int,
            default_value=DEFAULT_EVENT_TIME_FRAME_HOURS,
        )
        max_events_to_return = extract_action_param(
            siemplify,
            param_name="Max Events To Return",
            is_mandatory=False,
            print_value=True,
            input_type=int,
            default_value=None,
        )

        max_comments_to_return = extract_action_param(
            siemplify,
            param_name="Max Comments To Return",
            is_mandatory=False,
            print_value=True,
            input_type=int,
            default_value=DEFAULT_MAX_COMMENTS_TO_RETURN,
        )

        if (
            return_entity_timeline
            and lowest_event_risk_score_to_fetch is not None
            and lowest_event_risk_score_to_fetch < 0
        ):
            siemplify.LOGGER.info(
                f'"Lowest Event Risk Score To Fetch" must be non-negative. Using value of {LOWEST_EVENT_RISK_SCORE}'
            )
            lowest_event_risk_score_to_fetch = LOWEST_EVENT_RISK_SCORE

        if (
            return_entity_timeline
            and max_events_to_return is not None
            and max_events_to_return < 0
        ):
            siemplify.LOGGER.info(
                f'"Max Events To Return" must be non-negative. Retrieving all available events'
            )
            max_events_to_return = None

        if return_comments and max_comments_to_return < 0:
            siemplify.LOGGER.info(
                f'"Max Comments To Return" must be non-negative. Using default of {DEFAULT_MAX_COMMENTS_TO_RETURN}'
            )
            max_comments_to_return = DEFAULT_MAX_COMMENTS_TO_RETURN

        if return_entity_timeline and event_time_frame < 0:
            siemplify.LOGGER.info(
                f'"Event Time Frame" must be non-negative. Using default of {DEFAULT_EVENT_TIME_FRAME_HOURS}'
            )
            event_time_frame = DEFAULT_EVENT_TIME_FRAME_HOURS

        manager = ExabeamAdvancedAnalyticsManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            logger=siemplify.LOGGER,
        )

        target_entity_types = [
            entity.entity_type for entity in siemplify.target_entities
        ]

        # Fetch notable users and assets
        notable_users = (
            manager.get_notable_users()
            if EntityTypes.USER in target_entity_types
            else []
        )
        notable_assets = (
            manager.get_notable_assets()
            if EntityTypes.ADDRESS in target_entity_types
            or EntityTypes.HOSTNAME in target_entity_types
            else []
        )

        for entity in siemplify.target_entities:
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            try:
                if entity.entity_type not in SUPPORTED_ENTITIES:
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} is of unsupported type. Skipping."
                    )
                    continue

                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")

                entity_type = (
                    ENTITY_USER_TYPE
                    if entity.entity_type == EntityTypes.USER
                    else ENTITY_ASSET_TYPE
                )
                siemplify.LOGGER.info(
                    f"Fetching details for entity {entity.identifier}"
                )

                if entity.entity_type == EntityTypes.ADDRESS:
                    # For IP entities we will user host name as asset identifier. Confirmed by product, to align with Exabeam UI
                    entity_details = manager.get_entity_details(
                        entity_type=entity_type, entity_identifier=entity.identifier
                    )
                    if not entity_details.exists:
                        siemplify.LOGGER.info(
                            f"Entity {entity.identifier} was not found in {INTEGRATION_DISPLAY_NAME}. Skipping..."
                        )
                        failed_entities.append(entity)
                        continue
                    entity_identifier = entity_details.host_name
                    siemplify.LOGGER.info(
                        f"Using hostname {entity_identifier} for entity {entity.identifier}"
                    )
                    entity_details = manager.get_entity_details(
                        entity_type=entity_type, entity_identifier=entity_identifier
                    )
                else:
                    entity_identifier = entity.identifier
                    entity_details = manager.get_entity_details(
                        entity_type=entity_type, entity_identifier=entity_identifier
                    )

                if not entity_details.exists:
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} was not found in {INTEGRATION_DISPLAY_NAME}. Skipping..."
                    )
                    failed_entities.append(entity)
                    continue

                siemplify.LOGGER.info(
                    f"Successfully retrieved details for entity {entity.identifier} of type {entity_type}"
                )

                # Fetch Entity Comments
                if return_comments:
                    try:
                        siemplify.LOGGER.info(
                            f"Fetching comments for entity {entity.identifier}"
                        )
                        entity_comments = manager.get_entity_comments(
                            entity_type=entity_type,
                            entity_identifier=entity_identifier.strip(),
                            limit=max_comments_to_return,
                        )
                        if entity_comments:
                            siemplify.LOGGER.info(
                                f"Found {len(entity_comments)} comments for entity {entity.identifier}"
                            )
                            entity_details.set_comments(entity_comments)
                            siemplify.result.add_data_table(
                                title=f"{entity.identifier} Comments",
                                data_table=construct_csv(
                                    [
                                        entity_comment.as_csv()
                                        for entity_comment in entity_comments
                                    ]
                                ),
                            )
                        else:
                            siemplify.LOGGER.info(
                                f"No comments found for entity {entity.identifier}"
                            )
                    except Exception as error:
                        siemplify.LOGGER.error(
                            f"Failed to fetch comments for entity {entity.identifier}"
                        )
                        siemplify.LOGGER.exception(error)

                # Check if entity is notable
                if entity_type == ENTITY_USER_TYPE:
                    entity_details.is_notable = is_notable_user(
                        entity.identifier, notable_users
                    )
                    siemplify.LOGGER.info(
                        f"User {entity.identifier} found as notable: {entity_details.is_notable}"
                    )
                else:
                    entity_details.is_notable = is_notable_asset(
                        entity.identifier, notable_assets
                    )
                    siemplify.LOGGER.info(
                        f"Asset {entity.identifier} found as notable: {entity_details.is_notable}"
                    )

                # Fetch Entity sequences
                if return_entity_timeline:
                    try:
                        sequence_start_time = utc_now() - datetime.timedelta(
                            hours=event_time_frame + EVENT_TIME_FRAME_BUFFER_HOURS
                        )
                        siemplify.LOGGER.info(
                            f"Fetching sequences from {sequence_start_time} ({convert_datetime_to_unix_time(sequence_start_time)})"
                        )
                        entity_sequences = manager.get_entity_sequences(
                            entity_type=entity_type,
                            entity_identifier=entity_identifier,
                            start_time=convert_datetime_to_unix_time(
                                sequence_start_time
                            ),
                            end_time=unix_now(),
                        )

                        # Process latest sequences first
                        entity_sequences = sorted(
                            entity_sequences.sequences,
                            key=lambda sequence: sequence.end_time,
                            reverse=True,
                        )

                        siemplify.LOGGER.info(
                            f"Successfully fetched {len(entity_sequences)} sequences"
                        )

                        if entity_sequences:
                            # Filter old sequences
                            event_time_frame_milliseconds = (
                                unix_now()
                                - convert_hours_to_milliseconds(event_time_frame)
                            )
                            siemplify.LOGGER.info(
                                f"Filtering old sequences from {event_time_frame_milliseconds}"
                            )

                            filtered_sequence_ids = [
                                sequence
                                for sequence in entity_sequences
                                if sequence.end_time > event_time_frame_milliseconds
                            ]

                            siemplify.LOGGER.info(
                                f"Successfully filtered {len(filtered_sequence_ids)} sequences"
                            )

                            if filtered_sequence_ids:
                                try:
                                    entity_sequence_events = []
                                    # Query for events for each sequence
                                    for sequence in filtered_sequence_ids:

                                        siemplify.LOGGER.info(
                                            f"Fetching {sequence.num_of_events} sequence events for sequence {sequence.sequence_id}"
                                        )

                                        entity_events = manager.get_entity_events(
                                            entity_type=entity_type,
                                            entity_identifier=entity_identifier,
                                            sequence_id=sequence.sequence_id,
                                            anomaly_only=only_anomaly_events,
                                            limit=sequence.num_of_events,
                                        )
                                        fetched_sequence_events = sorted(
                                            entity_events.entity_events,
                                            key=lambda event: event.time,
                                            reverse=True,
                                        )
                                        siemplify.LOGGER.info(
                                            f"Successfully fetched {len(fetched_sequence_events)} events for sequence "
                                            f"{sequence.sequence_id}"
                                        )

                                        siemplify.LOGGER.info(
                                            f"Filtering old and already seen events"
                                        )

                                        # Filter old events
                                        filtered_sequence_events = [
                                            sequence_event
                                            for sequence_event in fetched_sequence_events
                                            if sequence_event.time
                                            > event_time_frame_milliseconds
                                        ]
                                        # Filter seen events
                                        filtered_sequence_events = [
                                            sequence_event
                                            for sequence_event in filtered_sequence_events
                                            if sequence_event.event_id
                                            not in [
                                                seen_event.event_id
                                                for seen_event in entity_sequence_events
                                            ]
                                        ]

                                        siemplify.LOGGER.info(
                                            f"Successfully filtered {len(filtered_sequence_events)} events"
                                        )

                                        for sequence_event in filtered_sequence_events:
                                            event_risk_score, found_score = (
                                                entity_events.get_event_risk_score(
                                                    event_id=sequence_event.event_id
                                                )
                                            )
                                            if found_score:
                                                siemplify.LOGGER.info(
                                                    f"Event {sequence_event.event_id} found risk score of {event_risk_score}"
                                                )
                                                sequence_event.risk_score = (
                                                    event_risk_score
                                                )
                                            else:
                                                siemplify.LOGGER.info(
                                                    f"Event {sequence_event.event_id} risk score wasn't found"
                                                )

                                        if lowest_event_risk_score_to_fetch is not None:
                                            # Filter event's risk score
                                            siemplify.LOGGER.info(
                                                f"Filtering events with risk score bigger or equals then {lowest_event_risk_score_to_fetch}"
                                            )

                                            # Filter events that risk score wasn't found or risk score is lower than
                                            # lowest event risk score
                                            entity_sequence_events.extend(
                                                [
                                                    sequence_event
                                                    for sequence_event in filtered_sequence_events
                                                    if sequence_event.risk_score
                                                    is not None
                                                    and sequence_event.risk_score
                                                    >= lowest_event_risk_score_to_fetch
                                                ]
                                            )
                                        else:
                                            entity_sequence_events.extend(
                                                filtered_sequence_events
                                            )

                                    # Save newest sequence events that were found
                                    newest_sequence_events = sorted(
                                        entity_sequence_events,
                                        key=lambda sequence_event: sequence_event.time,
                                        reverse=True,
                                    )

                                    entity_details.set_events(
                                        newest_sequence_events[:max_events_to_return]
                                        if max_events_to_return is not None
                                        else newest_sequence_events
                                    )

                                    siemplify.LOGGER.info(
                                        f"Successfully found {len(entity_details.entity_events)} events for entity "
                                        f"{entity.identifier}"
                                    )
                                except Exception as error:
                                    siemplify.LOGGER.error(
                                        f"Failed to fetch timeline sequence events"
                                    )
                                    siemplify.LOGGER.exception(error)
                            else:
                                siemplify.LOGGER.info(
                                    f"No sequences were found for entity {entity.identifier} in event time frame of "
                                    f"{event_time_frame}"
                                )

                        else:
                            siemplify.LOGGER.info(
                                f"No sequences were found for entity {entity.identifier}"
                            )

                    except Exception as error:
                        siemplify.LOGGER.error(
                            f"Failed to fetch timeline sequences for entity {entity.identifier}"
                        )
                        siemplify.LOGGER.exception(error)

                if create_insight:
                    siemplify.create_case_insight(
                        triggered_by=INTEGRATION_NAME,
                        title=f"{entity_type.title()} Details",
                        content=entity_details.as_insight(
                            show_comments=return_comments,
                            show_events=return_entity_timeline,
                        ),
                        entity_identifier=entity.identifier,
                        severity=InsightSeverity.INFO,
                        insight_type=InsightType.Entity,
                    )

                json_results[entity.identifier] = entity_details.as_json()

                # Enrichment Table
                entity.is_enriched = True
                entity.additional_properties.update(entity_details.as_enrichment())

                # CSV Entity Events
                if entity_details.entity_events:
                    siemplify.result.add_data_table(
                        title=f"{entity.identifier} Events",
                        data_table=construct_csv(
                            [
                                entity_event.as_csv()
                                for entity_event in entity_details.entity_events
                            ]
                        ),
                    )

                # CSV Case wall table of enrichment data / report link
                siemplify.result.add_entity_table(
                    f"{entity.identifier}",
                    construct_csv(entity_details.as_enrichment_csv_table()),
                )
                siemplify.result.add_entity_link(
                    f"{entity.identifier}", entity_details.case_wall_report_link()
                )

                enriched_entities.append(entity)
            except Exception as error:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(error)

        if enriched_entities:
            output_message += "Successfully returned information about the following entities from {}:\n   {}\n\n".format(
                INTEGRATION_DISPLAY_NAME,
                "\n   ".join([entity.identifier for entity in enriched_entities]),
            )
            result_value = True
            siemplify.update_entities(enriched_entities)
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
        else:
            output_message += f"No entities were enriched using information from {INTEGRATION_DISPLAY_NAME}."

        if failed_entities and enriched_entities:
            output_message += "Action wasn't able to return information about the following entities from {}:\n   {}\n\n".format(
                INTEGRATION_DISPLAY_NAME,
                "\n   ".join([entity.identifier for entity in failed_entities]),
            )

    except Exception as error:
        output_message = (
            f'Error executing action "{ENRICH_ENTITIES_SCRIPT_NAME}". Reason: {error}'
        )
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
