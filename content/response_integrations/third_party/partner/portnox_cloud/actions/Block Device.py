from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from ..core.PortnoxManager import PortnoxManager, PortnoxAuthError

INTEGRATION_NAME = "PortnoxCloud"
SCRIPT_NAME = "Block Device"

SUPPORTED_ENTITIES = [EntityTypes.MACADDRESS, EntityTypes.HOSTNAME, EntityTypes.ADDRESS]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "{0} - {1}".format(INTEGRATION_NAME, SCRIPT_NAME)
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    api_root = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name="API Root",
        default_value="https://clear.portnox.com:8081/CloudPortalBackEnd/")
    api_token = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name="API Token", is_mandatory=False)
    username = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name="username", is_mandatory=False)
    password = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name="password", is_mandatory=False)
    verify_ssl = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name="Verify SSL",
        input_type=bool, default_value=True)

    reason = siemplify.extract_action_param(
        param_name="Reason", is_mandatory=False, print_value=True,
        default_value="Blocked by Google SecOps SOAR")
    device_id_param = siemplify.extract_action_param(
        param_name="Device ID", is_mandatory=False, print_value=True)
    max_pages = siemplify.extract_action_param(
        param_name="Max Pages To Scan", input_type=int, default_value=10,
        is_mandatory=False, print_value=True)

    blocked, not_found, errors = [], [], []

    try:
        manager = PortnoxManager(
            api_root=api_root, api_token=api_token, username=username,
            password=password, verify_ssl=verify_ssl, logger=siemplify.LOGGER)

        # Path 1: an explicit device GUID was supplied by the playbook.
        if device_id_param:
            manager.block_device(device_id_param, reason)
            blocked.append(device_id_param)

        # Path 2: resolve entities in the case to device GUIDs, then block.
        else:
            scope = [e for e in siemplify.target_entities
                     if e.entity_type in SUPPORTED_ENTITIES]
            for entity in scope:
                try:
                    if entity.entity_type == EntityTypes.MACADDRESS:
                        devices = manager.find_devices_by_mac(
                            entity.identifier, max_pages=max_pages)
                    else:
                        devices = manager.find_devices_by_text(
                            entity.identifier, max_pages=max_pages)

                    if not devices:
                        not_found.append(entity.identifier)
                        continue

                    for device in devices:
                        device_id = device.get("DeviceId")
                        if not device_id:
                            continue
                        manager.block_device(device_id, reason)
                        blocked.append("{0} ({1})".format(entity.identifier, device_id))
                        entity.is_suspicious = True

                except Exception as entity_error:
                    siemplify.LOGGER.error("Block failed for {0}: {1}".format(
                        entity.identifier, entity_error))
                    errors.append("{0}: {1}".format(entity.identifier, entity_error))

            siemplify.update_entities(
                [e for e in scope if e.identifier not in not_found])

        status = EXECUTION_STATE_COMPLETED
        result_value = str(bool(blocked))
        parts = []
        if blocked:
            parts.append("Blocked in Portnox Cloud: {0}".format(", ".join(blocked)))
        if not_found:
            parts.append("No matching Portnox device: {0}".format(", ".join(not_found)))
        if errors:
            parts.append("Errors: {0}".format("; ".join(errors)))
        output_message = "\n".join(parts) or "Nothing to block."

    except PortnoxAuthError as error:
        siemplify.LOGGER.error(str(error))
        status = EXECUTION_STATE_FAILED
        result_value = "False"
        output_message = "Authentication to Portnox Cloud failed. {0}".format(error)

    except Exception as error:
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = "False"
        output_message = "Block Device failed. Error: {0}".format(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
