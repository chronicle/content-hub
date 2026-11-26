from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param

from ..core.action_utils import create_manager, parse_account_input, user_entity_accounts
from ..core.constants import INTEGRATION_DISPLAY_NAME, INTEGRATION_IDENTIFIER
from ..core.portnox_manager import PortnoxAuthError, PortnoxError

SCRIPT_NAME = "Move Account To Group"


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_IDENTIFIER} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    moved: list[str] = []
    failed: list[str] = []

    try:
        group_name = extract_action_param(siemplify, param_name="Group Name", is_mandatory=True, print_value=True)
        account_id_param = extract_action_param(siemplify, param_name="Account ID", print_value=True)

        manager = create_manager(siemplify)

        # The Account ID parameter wins. Fall back to User entities in the alert.
        targets = parse_account_input(account_id_param)
        if not targets:
            targets = user_entity_accounts(siemplify.target_entities)

        for account_id in targets:
            try:
                manager.move_account_to_group(account_id, group_name)
                moved.append(account_id)
            except PortnoxAuthError:
                raise
            except PortnoxError as move_error:
                siemplify.LOGGER.error(f"Failed to move {account_id} to group {group_name}: {move_error}")
                failed.append(account_id)

        messages = []
        if moved:
            messages.append(
                f"Successfully moved accounts to group '{group_name}' on the following entities using "
                f"{INTEGRATION_DISPLAY_NAME}: {', '.join(moved)}"
            )
        if failed:
            messages.append(
                f"Action wasn't able to move accounts to group '{group_name}' on the following entities using "
                f"{INTEGRATION_DISPLAY_NAME}: {', '.join(failed)}. Note that accounts synchronized from LDAP "
                "cannot be moved through the API."
            )
        if not targets:
            messages.append("No accounts to move. Provide the Account ID parameter or run the action on User entities.")

        status = EXECUTION_STATE_COMPLETED
        result_value = bool(moved)
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
