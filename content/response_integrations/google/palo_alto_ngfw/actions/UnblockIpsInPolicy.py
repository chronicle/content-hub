from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon import extract_action_param, extract_configuration_param

from ..core.constants import INTEGRATION_NAME, UNBLOCK_IPS_IN_POLICY_SCRIPT_NAME
from ..core.exceptions import NGFWException
from ..core.NGFWManager import NGFWManager


SUPPORTED_ENTITY_TYPES = [EntityTypes.ADDRESS]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UNBLOCK_IPS_IN_POLICY_SCRIPT_NAME
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        print_value=False,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        print_value=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )
    deviceName = extract_action_param(
        siemplify, param_name="Device Name", print_value=True, is_mandatory=True
    )
    vsysName = extract_action_param(
        siemplify, param_name="Vsys Name", print_value=True, is_mandatory=True
    )
    policy_name = extract_action_param(
        siemplify, param_name="Policy Name", print_value=True, is_mandatory=True
    )
    target = extract_action_param(
        siemplify, param_name="Target", print_value=True, is_mandatory=True
    )

    suitable_entity_identifiers = [
        entity.identifier
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]
    successful_entities, not_existing_entities = [], []
    json_results = {"success": [], "didn't_exist_initially": []}
    result_value = True
    status = EXECUTION_STATE_COMPLETED

    try:
        if not target != "source" and not target != "destination":
            raise NGFWException("Target must be source or destination!")

        if suitable_entity_identifiers:
            api = NGFWManager(
                api_root,
                username,
                password,
                siemplify.run_folder,
                verify_ssl=verify_ssl,
            )
            existing_ips = (
                api.FindRuleBlockedIps(deviceName, vsysName, policy_name, target) or []
            )

            for entity_identifier in suitable_entity_identifiers:
                if entity_identifier not in existing_ips:
                    not_existing_entities.append(entity_identifier)
                else:
                    api.EditBlockedIps(
                        deviceName=deviceName,
                        vsysName=vsysName,
                        policyName=policy_name,
                        target=target,
                        IpsToRemove=[entity_identifier],
                    )
                    successful_entities.append(entity_identifier)

            if successful_entities:
                output_message = "Successfully unblocked %s \n" % (
                    ",".join(successful_entities)
                )
            else:
                output_message = "No IP addresses were unblocked \n"
                result_value = False

            if not_existing_entities:
                result_value = True
                output_message += (
                    "The following IP addresses were not blocked in Palo Alto NGFW: "
                    "{}\n".format(", ".join(not_existing_entities))
                )

            json_results["success"] = successful_entities
            json_results["didn't_exist_initially"] = not_existing_entities

            siemplify.result.add_result_json(json_results)

        else:
            output_message = "No suitable entities found in the scope."
            result_value = False

    except Exception as e:
        output_message = f'Error executing action "Unblock ips in policy". Reason: {e}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
