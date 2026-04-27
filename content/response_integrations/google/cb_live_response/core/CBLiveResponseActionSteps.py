from __future__ import annotations
from .AsyncActionStepHandler import (
    FAILED_ENTITY_STATE,
    IN_PROGRESS_ENTITY_STATE,
    ENTITY_FILENAME_CONCAT_CHAR,
    SOME_FAILED_MSG,
    ENTITY_KEY_FOR_FORMAT,
    SOME_COMPLETED_MSG,
    IN_PROGRESS_MSG,
    COMPLETED_ENTITY_STATE,
    TIMEOUT_REACHED_MSG,
)
from soar_sdk.SiemplifyDataModel import EntityTypes
from .constants import VENDOR_NAME

SESSION_CHECKER = "session_status"
MULTIPLE_DEVICES = "multiple_devices"
DUPLICATED_DEVICES = "duplicated_devices"
MISSING_DEVICES = "missing_devices"
FAILED_SESSION_INIT = "session_init_failed"
FAILED_COMMAND_INIT = "command_init_failed"


def initial_step(step_handler, suitable_entities):
    for entity_identifier in suitable_entities:
        step_handler.logger.info(f"Initiating entity {entity_identifier}")
        step_handler.add_entity_data_to_step(entity_identifier, entity_identifier)
        step_handler.logger.info(f"Entity {entity_identifier} is ready.")


def initial_step_for_multiple_data(
    step_handler, suitable_entities, additional_entities
):
    for entity_identifier in suitable_entities:
        for entity in additional_entities:
            step_handler.logger.info(f"Initiating entity {entity_identifier}")
            step_handler.add_entity_data_to_step(
                f"{entity_identifier}{ENTITY_FILENAME_CONCAT_CHAR}{entity}",
                entity_identifier,
            )
            step_handler.logger.info(f"Entity {entity_identifier} is ready.")


def add_items_data_by_entity(
    step_handler, entity_identifier, in_progress_items, data, step=None
):
    for item in in_progress_items:
        if entity_identifier == step_handler.extract_entities_from_item(item):
            step_handler.add_entity_data_to_step(item, data, step)


def add_items_failed_data_by_entity(
    step_handler, entity_identifier, in_progress_items, data, step=None
):
    for item in in_progress_items:
        if entity_identifier == step_handler.extract_entities_from_item(item):
            step_handler.fail_entity(item, step, data)


def remove_items_data_by_entity(step_handler, entity_identifier, in_progress_items):
    for item in in_progress_items:
        if entity_identifier == step_handler.extract_entities_from_item(item):
            step_handler.remove_entity(item)


def get_first_item_for_entity(step_handler, entity, items):
    for item in items:
        if entity == step_handler.extract_entities_from_item(item):
            return item


def get_device_id(step_handler):
    step_handler.add_output_messages(
        {
            SOME_FAILED_MSG: f"Action was not able to find corresponding VMware CB Cloud agent for the following entities: "
            f"{{{ENTITY_KEY_FOR_FORMAT}}}"
        }
    )
    hosts_internal_ip_map = {}
    duplicated_entities = []
    items_to_process = step_handler.get_entities_by_state(
        state=IN_PROGRESS_ENTITY_STATE
    )
    entity_identifiers = list(
        set(
            [step_handler.extract_entities_from_item(item) for item in items_to_process]
        )
    )
    entity_identifier_with_type = {
        entity_identifier: step_handler.get_entity(entity_identifier).entity_type
        for entity_identifier in entity_identifiers
    }
    entity_identifier_with_type = dict(
        sorted(
            entity_identifier_with_type.items(),
            key=lambda item: item[1] == EntityTypes.HOSTNAME,
            reverse=True,
        )
    )
    for entity_identifier, entity_type in entity_identifier_with_type.items():
        if step_handler.is_approaching_timeout():
            step_handler.logger.info("Action timeout is near.")
            break

        duplicated_entity = is_entity_from_duplicated(
            step_handler, entity_identifier, hosts_internal_ip_map
        )
        if duplicated_entity:
            remove_items_data_by_entity(
                step_handler, entity_identifier, items_to_process
            )
            duplicated_entities.append((duplicated_entity, entity_identifier))
            continue

        try:
            step_handler.logger.info(f"Start process entity {entity_identifier}")
            step_handler.logger.info(
                f"Fetching device info for entity {entity_identifier}"
            )
            step_handler.logger.info("Getting device")
            devices = step_handler.manager.get_devices(query=entity_identifier, limit=3)
            validate_empty_devices(
                step_handler, items_to_process, devices, entity_identifier
            )
            validate_multiple_devices(
                step_handler, items_to_process, devices, entity_identifier
            )
            device_id = devices[0].id
            if entity_type == EntityTypes.HOSTNAME:
                hosts_internal_ip_map[entity_identifier] = devices[
                    0
                ].last_internal_ip_address
            add_items_data_by_entity(
                step_handler, entity_identifier, items_to_process, device_id
            )
        except Exception as e:
            err_msg = f"Unable to get device for {entity_identifier}. Error is {e}"
            step_handler.logger.info(err_msg)
            step_handler.logger.exception(e)
            add_items_failed_data_by_entity(
                step_handler, entity_identifier, items_to_process, err_msg
            )
        step_handler.logger.info(f"Finishing processing entity {entity_identifier}")

    add_custom_data(step_handler, DUPLICATED_DEVICES, duplicated_entities)


def get_device_id_by_item(step_handler):
    get_device_id(step_handler)
    entities = ", ".join(
        list(
            set(
                [
                    step_handler.extract_entities_from_item(item)
                    for item in step_handler.get_entities_by_state(
                        state=FAILED_ENTITY_STATE
                    )
                ]
            )
        )
    )
    step_handler.add_output_messages(
        {
            SOME_FAILED_MSG: f"Action was not able to find corresponding VMware CB Cloud agent for the following entities: "
            f"{entities}"
        }
    )


def session_start(step_handler, previous_step):
    items_to_process = step_handler.get_entities_by_state(
        state=IN_PROGRESS_ENTITY_STATE
    )
    entity_identifiers = list(
        set(
            [step_handler.extract_entities_from_item(item) for item in items_to_process]
        )
    )
    for entity_identifier in entity_identifiers:
        item = get_first_item_for_entity(
            step_handler, entity_identifier, items_to_process
        )
        step_handler.logger.info(f"Start process entity {entity_identifier}")
        device_id = step_handler.get_entity_data(item, previous_step)
        session_id = FAILED_ENTITY_STATE
        session_status = None

        if not device_id:
            step_handler.logger.info("Device did not found.")
            continue

        try:
            step_handler.logger.info("Starting session")
            session = step_handler.manager.start_session(device_id=device_id)
            session_id = session.id
            if session.is_active:
                session_status = session.status

        except Exception as err:
            err_msg = f"Failed to initiate session for device {device_id}, entity {entity_identifier}."
            step_handler.logger.error(err_msg)
            step_handler.logger.exception(err)
            add_items_failed_data_by_entity(
                step_handler, entity_identifier, items_to_process, err_msg
            )
            for item in items_to_process:
                if entity_identifier == step_handler.extract_entities_from_item(item):
                    add_custom_data(
                        step_handler, FAILED_SESSION_INIT, entity_identifier
                    )
        step_handler.logger.info(f"Finishing processing entity {entity_identifier}")

        add_items_data_by_entity(
            step_handler, entity_identifier, items_to_process, session_id
        )
        if session_status:
            add_items_data_by_entity(
                step_handler,
                entity_identifier,
                items_to_process,
                session_status,
                SESSION_CHECKER,
            )


def session_status_check(step_handler, previous_step):
    step_handler.add_output_messages(
        {
            SOME_FAILED_MSG: f"Failed to initiate Live Response session for entities below. Consider increasing the value "
            f'of "Check for active session x times" parameter.\n{{{ENTITY_KEY_FOR_FORMAT}}}'
        }
    )
    items_to_process = step_handler.get_entities_by_state(
        state=IN_PROGRESS_ENTITY_STATE
    )
    entity_identifiers = list(
        set(
            [step_handler.extract_entities_from_item(item) for item in items_to_process]
        )
    )

    for entity_identifier in entity_identifiers:
        step_handler.logger.info(f"Start process entity {entity_identifier} ")
        item = get_first_item_for_entity(
            step_handler, entity_identifier, items_to_process
        )
        session_id = step_handler.get_entity_data(item, previous_step)

        try:
            step_handler.logger.info("Get session")
            session = step_handler.manager.get_session(session_id=session_id)
            step_handler.logger.info(f"Session is active: {session.is_active}")
            if session.is_active:
                session_status = session.status
                add_items_data_by_entity(
                    step_handler, entity_identifier, items_to_process, session_status
                )
        except Exception as err:
            err_msg = (
                f"An error occurred while getting data about session {session_id}."
            )
            step_handler.logger.error(err_msg)
            step_handler.logger.exception(err)
            add_items_failed_data_by_entity(
                step_handler, entity_identifier, items_to_process, err_msg
            )


def session_status_check_by_item(step_handler, previous_step):
    session_status_check(step_handler, previous_step)
    entities = ", ".join(
        list(
            set(
                [
                    step_handler.extract_entities_from_item(item)
                    for item in step_handler.failed_on_step()
                ]
            )
        )
    )
    in_progress_entities = ", ".join(
        list(
            set(
                [
                    step_handler.extract_entities_from_item(item)
                    for item in step_handler.get_entities_by_state(
                        state=IN_PROGRESS_ENTITY_STATE
                    )
                ]
            )
        )
    )
    completed_entities = ", ".join(
        list(
            set(
                [
                    step_handler.extract_entities_from_item(item)
                    for item in step_handler.get_entities_by_state(
                        state=COMPLETED_ENTITY_STATE
                    )
                ]
            )
        )
    )
    step_label = step_handler.get_step_data_by(
        step_id=step_handler.get_current_step()
    ).step_label
    step_handler.add_output_messages(
        {
            SOME_FAILED_MSG: f"Failed to initiate Live Response session for entities below. Consider increasing the value "
            f'of "Check for active session x times" parameter. {entities}',
            SOME_COMPLETED_MSG: f"The following entities are successful to {step_label}: {completed_entities}",
            IN_PROGRESS_MSG: f"The following entities are in progress to {step_label}: {in_progress_entities}",
            TIMEOUT_REACHED_MSG: f"Action reached timeout in {step_label} waiting for results for the following "
            f"entities: {in_progress_entities}",
        }
    )


def validate_empty_devices(step_handler, items_to_process, devices, entity_identifier):
    if not devices:
        for item in items_to_process:
            if entity_identifier == step_handler.extract_entities_from_item(item):
                add_custom_data(step_handler, MISSING_DEVICES, entity_identifier)
        raise Exception(f"No devices found for entity {entity_identifier}. Skipping.")


def validate_multiple_devices(
    step_handler, items_to_process, devices, entity_identifier
):
    if len(devices) > 1:
        for item in items_to_process:
            if entity_identifier == step_handler.extract_entities_from_item(item):
                add_custom_data(step_handler, MULTIPLE_DEVICES, entity_identifier)
                step_handler.logger.info(
                    f"Multiple matches found for entity {entity_identifier}, "
                    f"taking agent with the most recent last_contact_time."
                )


def is_entity_from_duplicated(step_handler, entity, entities_internal_ip_map):
    for entity_identifier, internal_ip in entities_internal_ip_map.items():
        if entity == internal_ip:
            step_handler.logger.info(
                f"Entity {entity} is referring to the same device as "
                f"{entity_identifier}. Skipping."
            )
            return entity_identifier
    return False


def add_custom_data(step_handler, key, value):
    data = step_handler.get_custom_variable(key) or []
    data.extend(value) if isinstance(value, list) else data.append(value)
    step_handler.add_custom_variable(key, data)


def group_entities_by_filename(step_handler, state):
    grouped_entities = {}
    if state == FAILED_ENTITY_STATE:
        items = step_handler.failed_on_step()
    else:
        items = step_handler.get_entities_by_state(state=state)
    for host_or_ip, filename in [
        step_handler.extract_entities_from_item(item, -1) for item in items
    ]:
        grouped_entities[filename] = grouped_entities.get(filename, [])
        grouped_entities[filename].append(host_or_ip)
    return grouped_entities


def format_output_message(step_handler, output_message_format, state):
    return "\n".join(
        [
            output_message_format.format(
                **{"filename": filename, "entities": ", ".join(entity_identifiers)}
            )
            for filename, entity_identifiers in group_entities_by_filename(
                step_handler, state
            ).items()
            if entity_identifiers
        ]
    )


def device_custom_output_messages(step_handler):
    message = ""
    if step_handler.get_custom_variable(MULTIPLE_DEVICES):
        message = (
            f"Multiple matches were found in {VENDOR_NAME}, taking agent with the most recent last_contact_time "
            f"the following entities: {', '.join(list(set(step_handler.get_custom_variable(MULTIPLE_DEVICES))))}\n"
        )

    if step_handler.get_custom_variable(DUPLICATED_DEVICES):
        message += (
            "Provided IP and Hostname entities reference the same CB agent, taking Hostname entity for the "
            "following Hostname:IP pairs: {}\n".format(
                ", ".join(
                    [
                        f"{item[0]} - {item[1]}"
                        for item in step_handler.get_custom_variable(DUPLICATED_DEVICES)
                    ]
                )
            )
        )

    return message
