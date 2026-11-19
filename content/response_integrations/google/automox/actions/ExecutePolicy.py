from __future__ import annotations
from itertools import chain

from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_action_param, extract_configuration_param

from automox.core.AutomoxManager import AutomoxManager
from automox.core.exceptions import AutomoxAPIError
from automox.core.constants import (
    INTEGRATION_NAME,
    EXECUTE_POLICY_SCRIPT_NAME,
    SUPPORTED_ENTITIES,
    ENTITY_MAPPER,
)
from automox.core.AutomoxUtils import get_entity_original_identifier


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = EXECUTE_POLICY_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        remove_whitespaces=False,
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

    remediation_scope = extract_action_param(
        siemplify, param_name="Remediation Scope", is_mandatory=True, print_value=True
    )
    policy_name = extract_action_param(
        siemplify, param_name="Policy Name", is_mandatory=True, print_value=True
    )

    output_message = ""
    result_json = {}

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = AutomoxManager(
            api_root=api_root, api_key=api_key, verify_ssl=verify_ssl
        )

        policies = manager.get_policies(
            filter_key="name", filter_logic="Equal", filter_value=policy_name
        )
        if not policies:
            raise ValueError(
                f"policy “{policy_name}” wasn’t found in Automox. Please check the spelling."
            )

        policy = policies[0]

        # Execute policy on all devices
        if remediation_scope == "All Devices":
            manager.execute_policy(policy_id=policy.id, action="remediateAll")
            result_value = True
            status = EXECUTION_STATE_COMPLETED
            output_message = f"Successfully executed policy {policy_name} in Automox."
            siemplify.LOGGER.info(
                f"Successfully executed policy {policy_name} in Automox on All Devices."
            )
            siemplify.result.add_result_json({"status": "done"})

        # Executing policies on specific entities
        elif remediation_scope == "Only Entities":
            # Map entities to devices based on Automox outputs
            siemplify.LOGGER.info(f"Fetching devices from Automox")
            entity_devices_mapping = {}
            failed_entities = []
            for entity in siemplify.target_entities:
                if entity.entity_type not in SUPPORTED_ENTITIES:
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} is of unsupported type. Skipping."
                    )
                    continue

                entity_devices = manager.get_devices(
                    filter_value=get_entity_original_identifier(entity),
                    filter_field=ENTITY_MAPPER[entity.entity_type],
                )
                if not entity_devices:
                    failed_entities.append(entity.identifier)
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} wasn’t found in Automox. Skipping."
                    )
                    continue

                for device in entity_devices:
                    entity_devices_mapping[device.id] = (
                        entity_devices_mapping.get(device.id, []) + [entity.identifier]
                        if entity.identifier
                        not in entity_devices_mapping.get(device.id, [])
                        else entity_devices_mapping[device.id]
                    )

            # Executing policies one by one and tracking if we have any exceptions along the way
            # to map successful and failed tries
            siemplify.LOGGER.info(
                f"Executing policy “{policy_name}” on {len(entity_devices_mapping)} devices"
            )
            successful_devices = []
            failed_devices = []
            for device_id in entity_devices_mapping:
                try:
                    manager.execute_policy(
                        policy_id=policy.id,
                        action="remediateServer",
                        server_id=device_id,
                    )
                    successful_devices.append(device_id)
                except AutomoxAPIError as e:
                    siemplify.LOGGER.error(
                        f"Failed to execute policy {policy_name} on device {device_id}. Error: {e}"
                    )
                    failed_devices.append(device_id)

            # Trying to form the json results based on the results of the execution
            successful_entities = list(
                chain.from_iterable(
                    [
                        entity_devices_mapping[device_id]
                        for device_id in successful_devices
                    ]
                )
            )
            result_json.update(
                {
                    entity_identifier: {"status": "done"}
                    for entity_identifier in successful_entities
                }
            )

            failed_entities.extend(
                chain.from_iterable(
                    [entity_devices_mapping[device_id] for device_id in failed_devices]
                )
            )
            result_json.update(
                {
                    entity_identifier: {"status": "failure"}
                    for entity_identifier in failed_entities
                }
            )

            # Deciding which output message to use based on the results of the execution
            if successful_entities:
                log_message = (
                    f"Successfully executed policy {policy_name} on the following "
                    f"entities in Automox: {', '.join(successful_entities)}.\n"
                )
                output_message += log_message
                result_value = True
                status = EXECUTION_STATE_COMPLETED
                siemplify.LOGGER.info(log_message)

                if failed_entities:
                    log_message += (
                        f"Action wasn’t able to execute policy {policy_name} on the following "
                        f"entities in Automox: {', '.join(failed_entities)}.\n"
                    )
                    output_message += log_message
                    siemplify.LOGGER.info(log_message)
            else:
                log_message = (
                    f"No entities were found. Policy {policy_name} wasn’t executed."
                )
                output_message += log_message
                result_value = False
                status = EXECUTION_STATE_COMPLETED
                siemplify.LOGGER.info(log_message)

            if result_json:
                siemplify.result.add_result_json(
                    convert_dict_to_json_result_dict(result_json)
                )
        else:
            raise ValueError(f"Remediation Scope {remediation_scope} is not supported.")

    except Exception as e:
        output_message = (
            f"Error executing action “{EXECUTE_POLICY_SCRIPT_NAME}”. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}"
        f"\n  result_value: {result_value}"
        f"\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
