from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param

from ..core.action_utils import DEVICE_ENTITY_TYPES, create_manager, find_devices_for_entity
from ..core.constants import (
    DEFAULT_BLOCK_REASON,
    DEFAULT_MAX_PAGES,
    INTEGRATION_DISPLAY_NAME,
    INTEGRATION_IDENTIFIER,
)
from ..core.portnox_manager import PortnoxAuthError, PortnoxError

SCRIPT_NAME = "Block Device"


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_IDENTIFIER} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    reason = extract_action_param(
        siemplify,
        param_name="Reason",
        default_value=DEFAULT_BLOCK_REASON,
        print_value=True,
    )
    device_id_param = extract_action_param(siemplify, param_name="Device ID", print_value=True)

    blocked: list[str] = []
    failed: list[str] = []
    ambiguous: list[str] = []

    try:
        max_pages = extract_action_param(
            siemplify,
            param_name="Max Pages To Scan",
            input_type=int,
            default_value=DEFAULT_MAX_PAGES,
            print_value=True,
        )
        if max_pages < 1:
            raise ValueError("Max Pages To Scan must be a positive number.")

        manager = create_manager(siemplify)

        if device_id_param:
            # Path 1: the playbook supplied a device GUID.
            try:
                manager.block_device(device_id_param, reason)
                blocked.append(device_id_param)
            except PortnoxAuthError:
                raise
            except PortnoxError as block_error:
                siemplify.LOGGER.error(f"Failed to block device {device_id_param}: {block_error}")
                failed.append(device_id_param)
        else:
            # Path 2: resolve MAC address, IP address and hostname entities to device GUIDs.
            suspicious_entities = []
            for entity in (e for e in siemplify.target_entities if e.entity_type in DEVICE_ENTITY_TYPES):
                try:
                    devices = [d for d in find_devices_for_entity(manager, entity, max_pages) if d.get("DeviceId")]
                    if not devices:
                        siemplify.LOGGER.info(f"No Portnox Cloud device matches {entity.identifier}")
                        failed.append(entity.identifier)
                        continue
                    # Only a MAC address identifies a device exactly; never block several
                    # devices because an IP address or hostname matched more than one.
                    if len(devices) > 1 and entity.entity_type != EntityTypes.MACADDRESS:
                        siemplify.LOGGER.info(f"{len(devices)} devices match {entity.identifier}; not blocking any")
                        ambiguous.append(entity.identifier)
                        continue
                    for device in devices:
                        manager.block_device(device["DeviceId"], reason)
                    blocked.append(entity.identifier)
                    entity.is_suspicious = True
                    suspicious_entities.append(entity)
                except PortnoxAuthError:
                    raise
                except PortnoxError as entity_error:
                    siemplify.LOGGER.error(f"Failed to block device for {entity.identifier}: {entity_error}")
                    failed.append(entity.identifier)

            if suspicious_entities:
                siemplify.update_entities(suspicious_entities)

        messages = []
        if blocked:
            messages.append(
                f"Successfully blocked devices on the following entities using {INTEGRATION_DISPLAY_NAME}: "
                f"{', '.join(blocked)}"
            )
        if failed:
            messages.append(
                f"Action wasn't able to block devices on the following entities using {INTEGRATION_DISPLAY_NAME}: "
                f"{', '.join(failed)}"
            )
        if ambiguous:
            messages.append(
                "More than one device matched the following entities, so none of them were blocked. "
                f"Use a MAC address or the Device ID parameter instead: {', '.join(ambiguous)}"
            )
        if not messages:
            messages.append(
                "No devices to block. Provide the Device ID parameter or run the action on MAC address, "
                "IP address or hostname entities."
            )

        status = EXECUTION_STATE_COMPLETED
        result_value = bool(blocked)
        output_message = "\n".join(messages)

    except Exception as error:
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = f'Error executing action "{SCRIPT_NAME}". Reason: {error}'

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
