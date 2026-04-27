from __future__ import annotations
from ..core.FireEyeNXConstants import (
    PROVIDER_NAME,
    ADD_IPS_POLICY_EXCEPTION_SCRIPT_NAME,
    MAPPED_IP_POLICY_EXCEPTION_MODE,
    DEFAULT_IP_POLICY_EXCEPTION_INTERFACE,
    DEFAULT_IP_POLICY_EXCEPTION_MODE,
    DEFAULT_IP_POLICY_EXCEPTION_NAME,
)
from ..core.FireEyeNXManager import FireEyeNXManager
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.UtilsManager import mask_ip_address

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler

SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_IPS_POLICY_EXCEPTION_SCRIPT_NAME
    siemplify.LOGGER.info("=" * 20 + " Main - Params Init " + "=" * 20)

    # Configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )

    username = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=False,
    )

    password = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Password",
        is_mandatory=True,
        print_value=False,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    # Parameters
    victim_ip_subnet = extract_action_param(
        siemplify, param_name="Victim IP Subnet", is_mandatory=True, print_value=True
    )
    interface = extract_action_param(
        siemplify,
        param_name="Interface",
        is_mandatory=True,
        default_value=DEFAULT_IP_POLICY_EXCEPTION_INTERFACE,
        print_value=True,
    )
    policy_mode = extract_action_param(
        siemplify,
        param_name="Mode",
        is_mandatory=True,
        default_value=DEFAULT_IP_POLICY_EXCEPTION_MODE,
        print_value=True,
    )
    policy_name = extract_action_param(
        siemplify,
        param_name="Name",
        is_mandatory=False,
        default_value=DEFAULT_IP_POLICY_EXCEPTION_NAME.format(interface, policy_mode),
        print_value=True,
    )

    siemplify.LOGGER.info("=" * 20 + " Main - Started " + "=" * 20)

    result_value = False
    status = EXECUTION_STATE_COMPLETED
    output_messages = []

    successful_entities = []
    failed_entities = []
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        policy_mode = MAPPED_IP_POLICY_EXCEPTION_MODE.get(policy_mode)

        manager = FireEyeNXManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        siemplify.LOGGER.info(
            f"Found {len(suitable_entities)} entities of type IP Address to process."
        )

        for entity in suitable_entities:
            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
            masked_entity = mask_ip_address(entity.identifier)
            siemplify.LOGGER.info(
                f"Entity {entity.identifier} was masked to {masked_entity}"
            )

            try:
                manager.create_ips_policy_exception(
                    policy_name=policy_name,
                    policy_mode=policy_mode,
                    interface=interface,
                    victim_ip_subnet=victim_ip_subnet,
                    attacker_ip=masked_entity,
                )

                successful_entities.append(entity)
                siemplify.LOGGER.info(
                    f"Successfully created IP Policy exception for entity {entity.identifier}"
                )

            except Exception as error:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"Failed to create IP policy exception for entity: {entity.identifier}"
                )
                siemplify.LOGGER.exception(error)

            siemplify.LOGGER.info(f"Finished processing entity: {entity.identifier}")

        if successful_entities:
            output_messages.append(
                "Successfully added IPS policy exceptions in {} based on the following "
                "entities:\n {}".format(
                    PROVIDER_NAME,
                    "\n ".join(
                        [entity.identifier.strip() for entity in successful_entities]
                    ),
                )
            )
            result_value = True

        if failed_entities:
            output_messages.append(
                "Action wasn't able to add IPS policy exceptions based on the following "
                "entities:\n {}".format(
                    "\n ".join(
                        [entity.identifier.strip() for entity in failed_entities]
                    )
                )
            )

        if not successful_entities and not failed_entities:
            output_messages.append("No IPS policy exception were created.")

        output_message = "\n\n".join(output_messages)

    except Exception as error:
        output_message = (
            f'Error executing action "Add IPS Policy Exception". Reason: {error}'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("=" * 20 + " Main - Finished " + "=" * 20)
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
