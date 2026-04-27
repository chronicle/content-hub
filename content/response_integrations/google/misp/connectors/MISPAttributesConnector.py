from __future__ import annotations
import sys
from EnvironmentCommon import GetEnvironmentCommonFactory
from TIPCommon import (
    extract_connector_param,
    get_last_success_time,
    save_timestamp,
    is_overflowed,
    read_ids,
    write_ids,
)
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import output_handler, unix_now, convert_datetime_to_unix_time
from ..core.utils import is_approaching_timeout
from ..core.MISPManager import MISPManager
from ..core.constants import (
    CONNECTOR_NAME,
    DEFAULT_HOURS_BACKWARDS,
    STORED_IDS_LIMIT,
    TIMEOUT_THRESHOLD,
)


@output_handler
def main(is_test_run):
    connector_starting_time = unix_now()
    processed_alerts = []
    processed_attributes = []
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    api_root = extract_connector_param(
        siemplify, param_name="API Root", is_mandatory=True
    )

    api_key = extract_connector_param(
        siemplify, param_name="API Key", is_mandatory=True
    )

    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        print_value=True,
    )

    ca_certificate = extract_connector_param(
        siemplify, param_name="CA Certificate File - parsed into Base64 String"
    )

    environment_field_name = extract_connector_param(
        siemplify,
        param_name="Environment Field Name",
        default_value="",
        print_value=True,
    )

    environment_regex_pattern = extract_connector_param(
        siemplify,
        param_name="Environment Regex Pattern",
        default_value="",
        print_value=True,
    )

    max_attributes_per_cycle = extract_connector_param(
        siemplify,
        param_name="Max Attributes Per Cycle",
        input_type=int,
        is_mandatory=False,
    )

    hours_backwards = extract_connector_param(
        siemplify,
        param_name="Fetch Max Hours Backwards",
        input_type=int,
        is_mandatory=False,
        default_value=DEFAULT_HOURS_BACKWARDS,
        print_value=True,
    )

    attribute_type_filter = extract_connector_param(
        siemplify,
        param_name="Attribute Type Filter",
        is_mandatory=False,
        print_value=True,
    )
    attribute_type_filter = (
        [
            type_filter.lower().strip()
            for type_filter in attribute_type_filter.split(",")
        ]
        if attribute_type_filter
        else []
    )

    galaxies_filter = extract_connector_param(
        siemplify, param_name="Galaxy Filter", is_mandatory=False, print_value=True
    )
    galaxies_filter = (
        [galaxy_filter.lower().strip() for galaxy_filter in galaxies_filter.split(",")]
        if galaxies_filter
        else []
    )

    categories_filter = extract_connector_param(
        siemplify, param_name="Category Filter", is_mandatory=False, print_value=True
    )
    categories_filter = (
        [
            category_filter.lower().strip()
            for category_filter in categories_filter.split(",")
        ]
        if categories_filter
        else []
    )

    tags_filter = [tag.lower().strip() for tag in siemplify.whitelist]

    min_threat_level = extract_connector_param(
        siemplify,
        param_name="Lowest Threat Level To Fetch",
        is_mandatory=True,
        print_value=True,
        input_type=int,
    )

    if min_threat_level < 1 or min_threat_level > 4:
        # Severity value is invalid
        raise Exception(
            f"Threat level {min_threat_level} is invalid. Valid values are in range from 1 to 4."
        )

    python_process_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )

    device_product_field = extract_connector_param(
        siemplify, param_name="DeviceProductField", is_mandatory=True, print_value=True
    )

    try:
        siemplify.LOGGER.info("------------------- Main - Started -------------------")

        siemplify.LOGGER.info("Connecting to MISP")

        manager = MISPManager(api_root, api_key, verify_ssl, ca_certificate)

        siemplify.LOGGER.info("Successfully connected to MISP")

        # Read already existing alerts ids
        siemplify.LOGGER.info("Loading existing ids from IDS file.")
        existing_ids = read_and_repair_existing_ids(siemplify)
        siemplify.LOGGER.info(f"Found {len(existing_ids)} existing ids in ids.json")

        last_success_time = get_last_success_time(
            siemplify=siemplify, offset_with_metric={"hours": hours_backwards}
        )

        siemplify.LOGGER.info(
            f"Fetching attributes with timestamp greater than {last_success_time.isoformat()}"
        )

        # NOTICE - Paging doesn't work in the API, and there is no sorting in the API as well.
        # This means that the API might fetch the newest X attributes since timestamp (up to limit)
        # and we can't know if there are older ones and can't get them.
        # So a large enough fetch limit is mandatory.
        page = 0
        start_time = convert_datetime_to_unix_time(last_success_time) / 1000
        end_time = unix_now() / 1000

        misp_attributes = manager.search_attributes(
            payload={
                "timestamp": (start_time, end_time),
                "limit": max_attributes_per_cycle,
                "page": page,
            }
        )

        siemplify.LOGGER.info(
            f"Found {len(misp_attributes)} attributes since {last_success_time.isoformat()}."
        )

        filtered_attributes = []  # new fetched attributes that passed filters
        ignored_attributes = []  # attributes that exists in ids or didn't pass filters

        # Filter already seen alerts
        siemplify.LOGGER.info("Filtering already seen attributes.")
        new_attributes = [
            attribute
            for attribute in misp_attributes
            if attribute.id not in existing_ids
        ]
        siemplify.LOGGER.info(f"Found {len(new_attributes)} new attributes.")

        siemplify.LOGGER.info("Filtering attributes by category and type.")

        for attribute in new_attributes:
            if categories_filter and not filter_attributes_by_category_filter(
                siemplify, categories_filter, attribute
            ):
                # Save ID to prevent processing it in the future
                existing_ids.append(attribute.id)
                ignored_attributes.append(attribute)
                continue

            if attribute_type_filter and not filter_attributes_by_type_filter(
                siemplify, attribute_type_filter, attribute
            ):
                # Save ID to prevent processing it in the future
                existing_ids.append(attribute.id)
                ignored_attributes.append(attribute)
                continue

            filtered_attributes.append(attribute)

        siemplify.LOGGER.info(
            f"{len(filtered_attributes)} attributes have passed category and type filter."
        )

        siemplify.LOGGER.info("Grouping attributes by events and objects.")
        grouped_attributes = group_attributes_by_event(
            siemplify, manager, filtered_attributes
        )

        siemplify.LOGGER.info(
            "Filtering grouped attributes by their related event's galaxies, tags and threat level."
        )
        grouped_attributes, ignored_events = filter_events(
            siemplify,
            min_threat_level,
            galaxies_filter,
            tags_filter,
            grouped_attributes,
        )

        # Add the attribute of the ignored attribute groups to the ignored attributes list
        for ignored_event in ignored_events:
            for attribute in ignored_event["attributes"]:
                ignored_attributes.append(attribute)

            for object_id in ignored_event["objects"].keys():
                for attribute in ignored_event["objects"][object_id]["attributes"]:
                    ignored_attributes.append(attribute)

        siemplify.LOGGER.info(
            f"{len(grouped_attributes)} grouped attributes have passed filters."
        )

        if is_test_run:
            siemplify.LOGGER.info("This is a TEST run. Only 1 alert will be processed.")
            grouped_attributes = grouped_attributes[:1]

        # process alerts in connector cycle
        for attribute_group in grouped_attributes:
            try:
                event_id = attribute_group.get("event_id")

                if len(processed_alerts) >= max_attributes_per_cycle:
                    # Provide slicing for the alarms amount.
                    siemplify.LOGGER.info(
                        f"Reached max number of alerts cycle of value {max_attributes_per_cycle}. No more alerts will be processed in this cycle."
                    )
                    break

                if is_approaching_timeout(
                    python_process_timeout, connector_starting_time, TIMEOUT_THRESHOLD
                ):
                    siemplify.LOGGER.info(
                        "Timeout is approaching. Connector will gracefully exit"
                    )
                    break

                siemplify.LOGGER.info(
                    f"Started processing attributes of event {event_id}",
                    alert_id=event_id,
                )

                for attribute in attribute_group["attributes"]:
                    existing_ids.append(attribute.id)
                    processed_attributes.append(attribute)

                for object_id in attribute_group["objects"].keys():
                    for attribute in attribute_group["objects"][object_id][
                        "attributes"
                    ]:
                        existing_ids.append(attribute.id)
                        processed_attributes.append(attribute)

                alert_info = build_alert(
                    siemplify,
                    attribute_group,
                    device_product_field,
                    GetEnvironmentCommonFactory.create_environment_manager(
                        siemplify, environment_field_name, environment_regex_pattern
                    ),
                )

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{alert_info.rule_generator}-{alert_info.ticket_id}-{alert_info.environment}-{alert_info.device_product} found as overflow alert. Skipping."
                    )
                    # If is overflowed we should skip
                    continue

                processed_alerts.append(alert_info)

                siemplify.LOGGER.info(
                    f"Alerts for attributes of event {event_id} was created."
                )

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Failed to process attributes of event {event_id}",
                    alert_id=event_id,
                )
                siemplify.LOGGER.exception(e)

                if is_test_run:
                    raise

            siemplify.LOGGER.info(
                f"Finished processing attributes of event {event_id}", alert_id=event_id
            )

        if not is_test_run:
            siemplify.LOGGER.info("Saving existing ids.")
            write_ids(siemplify, existing_ids, stored_ids_limit=STORED_IDS_LIMIT)
            if misp_attributes:
                if not filtered_attributes:
                    # API call returned attributes, but all were filtered out and ignored. This means we might get stuck
                    # in an endless loop so add 1 second to timestamp to avoid that.
                    save_timestamp(
                        siemplify=siemplify,
                        alerts=misp_attributes,
                        timestamp_key="timestamp",
                        incrementation_value=1000,
                    )

                if not grouped_attributes and ignored_events:
                    # Found some attributes that pass the attributes filters, but all of them don't pass event filters
                    # In such case we might get stuck in an endless loop so add 1 second to timestamp to avoid that.
                    save_timestamp(
                        siemplify=siemplify,
                        alerts=misp_attributes,
                        timestamp_key="timestamp",
                        incrementation_value=1000,
                    )

                else:
                    # Save timestamp based on the processed attributes (processed = alert info created, regardless of overflow
                    # status) and the ignored attributes (= alerts that didn't pass filters). New timestamp
                    # should be the latest among all of those
                    save_timestamp(
                        siemplify=siemplify,
                        alerts=processed_attributes + ignored_attributes,
                        timestamp_key="timestamp",
                    )

    except Exception as err:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {err}")
        siemplify.LOGGER.exception(err)
        if is_test_run:
            raise

    siemplify.LOGGER.info(f"Created total of {len(processed_alerts)} cases")
    siemplify.LOGGER.info("------------------- Main - Finished -------------------")
    siemplify.return_package(processed_alerts)


def read_and_repair_existing_ids(siemplify):
    """Read existing ids and convert them to list, if it is a dict.
    This is needed to avoid regressions.

    Args:
        siemplify: (SiemplifyConnectorExecution)

    Returns:
        list
    """
    existing_ids_data = read_ids(siemplify)

    if isinstance(existing_ids_data, dict):
        return list(existing_ids_data.keys())

    return existing_ids_data


def group_attributes_by_event(siemplify, manager, misp_attributes):
    """
    Group attributes by their parent event and by their parrent object
    :param siemplify: {SiemplifyConnectorExecution}
    :param manager: {MISPManager}
    :param misp_attributes: {list} List of attributes to group
    :return: {list} List of dicts in the following format:
        {
            'event_id': int,  # the parent event ID
            'event': datamodels.Event,  # the parent event itself
            'attributes': [datamodels.Attribute]  # standalone attributes that dont belong to an object,
            'objects': {
                <object_id>: {
                    'object': datamodels.MISPObject  # The object itself,
                    'attributes': [datamodels.Attribute]  # attributes that belong to the object under the parent event
                }
            }
        }
    """
    misp_events = {}

    for attribute in misp_attributes:
        try:
            siemplify.LOGGER.info(f"Grouping attribute {attribute.id}")
            event_id = attribute.event_id

            siemplify.LOGGER.info(f"Attribute event ID: {event_id}")

            if event_id not in misp_events:
                misp_events[event_id] = {
                    "event_id": event_id,
                    "event": {},
                    "attributes": [],
                    "objects": {},
                }
                siemplify.LOGGER.info(f"Started fetching event {event_id}")
                misp_events[event_id]["event"] = manager.get_event_by_id(event_id)
                siemplify.LOGGER.info(f"Finished fetching event {event_id}")

            object_id = attribute.object_id
            siemplify.LOGGER.info(f"Attribute object ID: {object_id}")

            if object_id and int(object_id):
                # If the attribute is part of an object - group it under the object ID

                siemplify.LOGGER.info(
                    f"Attribute {attribute.id} is part of object {object_id}"
                )
                if attribute.object_id not in misp_events[event_id]["objects"]:
                    misp_events[event_id]["objects"][object_id] = {"attributes": []}
                    siemplify.LOGGER.info(f"Started fetching object {object_id}")
                    misp_events[event_id]["objects"][object_id]["object"] = (
                        manager.get_object_by_id(object_id)
                    )
                    siemplify.LOGGER.info(f"Finished fetching object {object_id}")

                misp_events[event_id]["objects"][object_id]["attributes"].append(
                    attribute
                )

            else:
                # The attribute is independent (not part of an object)
                siemplify.LOGGER.info(f"Attribute {attribute.id} is independent")
                misp_events[event_id]["attributes"].append(attribute)

        except Exception as e:
            siemplify.LOGGER.error(f"Failed to group attribute {attribute.id}")
            siemplify.LOGGER.exception(e)

    return misp_events.values()


def filter_events(siemplify, min_threat_level, galaxy_filter, tag_filter, misp_events):
    """
    Filter misp events (=grouped attributed)
    :param siemplify: {SiemplifyConnectorExecution}
    :param min_threat_level: {int} Min required threat level
    :param galaxy_filter: {list} Whitelist of galaxies
    :param tag_filter: {list} Whitelist of tags
    :param misp_events: {list} The grouped attributes
    :return: {tuple} Filtered events, ignored events (=did not pass filter)
    """
    filtered_events = []
    ignored_events = []

    for event in misp_events:
        if not filter_events_by_threat_level(siemplify, min_threat_level, event):
            ignored_events.append(event)
            continue

        siemplify.LOGGER.info(
            f'Event {event["event_id"]} has passed at threat level filter'
        )
        if galaxy_filter and not filter_events_by_galaxy_filter(
            siemplify, galaxy_filter, event
        ):
            ignored_events.append(event)
            continue

        if tag_filter and not filter_events_by_tag_filter(siemplify, tag_filter, event):
            ignored_events.append(event)
            continue

        siemplify.LOGGER.info(f'Event {event["event_id"]} has passed all filters.')
        filtered_events.append(event)

    return filtered_events, ignored_events


def filter_events_by_threat_level(siemplify, min_threat_level, misp_event):
    """
    Filter MISP group attributes (events) by threat level
    :param siemplify: {SiemplifyConnectorExecution}
    :param min_threat_level: {int} Min threat level required
    :param misp_event: {dict} The grouped attributes
    :return: {bool} True if the misp_event (= grouped attributes) passed the filter or not
    """
    # Filter by threat level
    if misp_event["event"].threat_level_id < min_threat_level:
        siemplify.LOGGER.info(
            f'Event {misp_event["event_id"]} did not pass threat level filter (current threat level: '
            f'{misp_event["event"].threat_level_id}, min threat level: {min_threat_level})'
        )
        return False

    return True


def filter_events_by_galaxy_filter(siemplify, galaxy_filter, misp_event):
    """
    Filter MISP group attributes (events) by galaxy filter
    :param siemplify: {SiemplifyConnectorExecution}
    :param galaxy_filter: {list} List of whitelisted galaxies
    :param misp_event: {dict} The grouped attributes
    :return: {bool} True if the misp_event (= grouped attributes) passed the filter or not
    """
    if not galaxy_filter:
        return True

    for galaxy in misp_event["event"].galaxies:
        # At least one galaxy must pass the filter
        if (
            str(galaxy.type).lower() in galaxy_filter
            or str(galaxy.name).lower() in galaxy_filter
        ):
            siemplify.LOGGER.info(
                f"Galaxy {galaxy.name} (type: {galaxy.type}) has passed filter."
            )
            return True

    siemplify.LOGGER.info(
        f'No whitelisted Galaxy was found for event {misp_event["event_id"]}'
    )
    return False


def filter_events_by_tag_filter(siemplify, tag_filter, misp_event):
    """
    Filter MISP group attributes (events) by tag filter
    :param siemplify: {SiemplifyConnectorExecution}
    :param tag_filter: {list} List of whitelisted tags
    :param misp_event: {dict} The grouped attributes
    :return: {bool} True if the misp_event (= grouped attributes) passed the filter or not
    """
    if not tag_filter:
        return True

    for tag in misp_event["event"].tags:
        # At least one galaxy must pass the filter
        if str(tag.name).lower() in tag_filter:
            siemplify.LOGGER.info(f"Tag {tag.name} has passed filter.")
            return True

    siemplify.LOGGER.info(
        f'No whitelisted tag was found for event {misp_event["event_id"]}'
    )
    return False


def filter_attributes_by_category_filter(siemplify, category_filter, misp_attribute):
    """
    Filter MISP attributes by category filter
    :param siemplify: {SiemplifyConnectorExecution}
    :param category_filter: {list} List of whitelisted categories
    :param misp_attribute: {dict} The attributes
    :return: {bool} True if the attribute passed the filter or not
    """
    if str(misp_attribute.category).lower() in category_filter:
        siemplify.LOGGER.info(
            f"Attribute {misp_attribute.id}  has passed category filter."
        )
        return True

    siemplify.LOGGER.info(
        f"Attribute {misp_attribute.id} did not pass category filter."
    )
    return False


def filter_attributes_by_type_filter(siemplify, type_filter, misp_attribute):
    """
    Filter MISP attributes by type filter
    :param siemplify: {SiemplifyConnectorExecution}
    :param type_filter: {list} List of whitelisted attribute types
    :param misp_attribute: {dict} The attributes
    :return: {bool} True if the attribute passed the filter or not
    """
    if str(misp_attribute.type).lower() in type_filter:
        siemplify.LOGGER.info(f"Attribute {misp_attribute.id}  has passed type filter.")
        return True

    siemplify.LOGGER.info(f"Attribute {misp_attribute.id} did not pass type filter.")
    return False


def build_events(siemplify, attribute_group, device_product_field_name):
    """
    BUild events from attribute group
    :param siemplify: {SiemplifyConnectorExecution}
    :param attribute_group: {dict} The grouped attributes info
    :param device_product_field_name: {str} The device product field name
    :return: {list} The created events
    """
    events = []

    siemplify.LOGGER.info(f"Creating events from objects.")
    for object_id, object_dict in attribute_group["objects"].items():
        try:
            siemplify.LOGGER.info(
                f"Creating event for attributes under object {object_id}"
            )
            events.append(
                object_dict["object"].as_event(
                    f'MISP event {attribute_group["event"].id}',
                    attribute_group["event"].timestamp_ms,
                    object_dict["attributes"],
                    attribute_group["event"].raw_data.get(device_product_field_name),
                )
            )
        except Exception as e:
            siemplify.LOGGER.error(
                f"Failed to create event for attributes under object {object_id}."
            )
            siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info(f"Creating events from stand alone attributes.")

    for attribute in attribute_group["attributes"]:
        try:
            siemplify.LOGGER.info(
                f"Creating event for stand alone attribute {attribute.id}"
            )
            events.append(
                attribute.as_event(
                    f'MISP event {attribute_group["event"].id}',
                    attribute_group["event"].timestamp_ms,
                    attribute_group["event"].raw_data.get(device_product_field_name),
                )
            )
        except Exception as e:
            siemplify.LOGGER.error(
                f"Failed to create event for attribute {attribute.id}."
            )
            siemplify.LOGGER.exception(e)

    return events


def build_alert(
    siemplify, attribute_group, device_product_field_name, environment_common
):
    """
    Create AlertInfos from attributes group
    :param siemplify: {SiemplifyConnectorExecution}
    :param attribute_group: {dict} The grouped attributes info
    :param device_product_field_name: {str} The device product field name
    :param environment_common: {EnvironmentHandle}
    :return: {AlertInfo} Created AlertInfo object
    """
    siemplify.LOGGER.info(
        f'Creating AlertInfo for event {attribute_group["event"].id}.'
    )

    siemplify.LOGGER.info(f"Building events from attribute group.")
    events = build_events(siemplify, attribute_group, device_product_field_name)

    siemplify.LOGGER.info(f"Created {len(events)} events.")

    siemplify.LOGGER.info(f"Building AlertInfo.")
    return attribute_group["event"].as_alert_info(events, environment_common)


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test)
