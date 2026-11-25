from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from ..core.PortnoxManager import PortnoxManager, PortnoxAuthError

INTEGRATION_NAME = "PortnoxCloud"
SCRIPT_NAME = "Move Account To Group"


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
        provider_name=INTEGRATION_NAME, param_name="Username", is_mandatory=False)
    password = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name="Password", is_mandatory=False)
    verify_ssl = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name="Verify SSL",
        input_type=bool, default_value=True)

    group_name = siemplify.extract_action_param(
        param_name="Group Name", is_mandatory=True, print_value=True)
    account_id_param = siemplify.extract_action_param(
        param_name="Account ID", is_mandatory=False, print_value=True)

    moved, failed = [], []

    try:
        manager = PortnoxManager(
            api_root=api_root, api_token=api_token, username=username,
            password=password, verify_ssl=verify_ssl, logger=siemplify.LOGGER)

        targets = []
        if account_id_param:
            targets = [account_id_param]
        else:
            targets = [e.identifier for e in siemplify.target_entities
                       if e.entity_type == EntityTypes.USER]

        for account_id in targets:
            try:
                manager.move_account_to_group(account_id, group_name)
                moved.append(account_id)
            except Exception as move_error:
                siemplify.LOGGER.error("Move failed for {0}: {1}".format(
                    account_id, move_error))
                failed.append("{0}: {1}".format(account_id, move_error))

        status = EXECUTION_STATE_COMPLETED
        result_value = str(bool(moved))
        parts = []
        if moved:
            parts.append("Moved to group '{0}': {1}".format(group_name, ", ".join(moved)))
        if failed:
            parts.append("Failed: {0}".format("; ".join(failed)))
        if not targets:
            parts.append("No User entities in scope and no Account ID supplied. "
                         "Note that LDAP-sourced accounts cannot be moved via API.")
        output_message = "\n".join(parts)

    except PortnoxAuthError as error:
        siemplify.LOGGER.error(str(error))
        status = EXECUTION_STATE_FAILED
        result_value = "False"
        output_message = "Authentication to Portnox Cloud failed. {0}".format(error)

    except Exception as error:
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = "False"
        output_message = "Move Account To Group failed. Error: {0}".format(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
