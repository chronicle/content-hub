from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import PROVIDER_NAME, CREATE_IP_LIST_ASSET_SCRIPT_NAME
from ..core.TenableManager import TenableSecurityCenterManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_IP_LIST_ASSET_SCRIPT_NAME
    status = EXECUTION_STATE_COMPLETED
    result_value = False

    try:
        siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

        server_address = extract_configuration_param(
            siemplify,
            provider_name=PROVIDER_NAME,
            param_name="Server Address",
            is_mandatory=True,
            print_value=True,
        )
        username = extract_configuration_param(
            siemplify,
            provider_name=PROVIDER_NAME,
            param_name="Username",
            is_mandatory=False,
            print_value=True,
        )
        password = extract_configuration_param(
            siemplify,
            provider_name=PROVIDER_NAME,
            param_name="Password",
            is_mandatory=False,
        )
        access_key = extract_configuration_param(
            siemplify,
            provider_name=PROVIDER_NAME,
            param_name="Access Key",
            is_mandatory=False,
            remove_whitespaces=False,
        )
        secret_key = extract_configuration_param(
            siemplify,
            provider_name=PROVIDER_NAME,
            param_name="Secret Key",
            is_mandatory=False,
            remove_whitespaces=False,
        )
        use_ssl = extract_configuration_param(
            siemplify,
            provider_name=PROVIDER_NAME,
            param_name="Use SSL",
            is_mandatory=True,
            input_type=bool,
            print_value=True,
        )

        name = extract_action_param(
            siemplify, param_name="Name", is_mandatory=True, print_value=True
        )
        description = extract_action_param(
            siemplify, param_name="Description", is_mandatory=False, print_value=True
        )
        tag = extract_action_param(
            siemplify, param_name="Tag", is_mandatory=False, print_value=True
        )

        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        scope_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type == EntityTypes.ADDRESS
        ]

        if scope_entities:
            # Create manager instance
            manager = TenableSecurityCenterManager(
                server_address,
                username,
                password,
                access_key,
                secret_key,
                use_ssl,
            )
            ips_csv = ",".join([entity.identifier for entity in scope_entities])
            asset = manager.create_ip_list_asset(
                name=name, description=description, tags=tag, ips=ips_csv
            )
            siemplify.result.add_result_json(asset.to_json())
            output_message = (
                "Successfully created new IP List Asset {} with the following IPs in Tenable.sc:\n "
                "{}".format(
                    name, "\n".join([entity.identifier for entity in scope_entities])
                )
            )
            result_value = True
        else:
            output_message = "At least 1 IP entity should be available in order to create an IP List Asset."

    except Exception as e:
        output_message = f'Error executing action "Create IP List Asset". Reason: {e}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
