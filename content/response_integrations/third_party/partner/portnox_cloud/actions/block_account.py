from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param

from ..core.action_utils import create_manager, parse_account_input, user_entity_accounts
from ..core.constants import DEFAULT_BLOCK_REASON, INTEGRATION_DISPLAY_NAME, INTEGRATION_IDENTIFIER
from ..core.portnox_manager import PortnoxAuthError, PortnoxError

SCRIPT_NAME = "Block Account"
SOURCE_PARAMETER = "Account ID parameter"
SOURCE_ENTITIES = "User entities in the alert"


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_IDENTIFIER} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    account_id_param = extract_action_param(siemplify, param_name="Account ID", print_value=True)
    reason = extract_action_param(
        siemplify,
        param_name="Reason",
        default_value=DEFAULT_BLOCK_REASON,
        print_value=True,
    )

    blocked: list[str] = []
    failed: list[str] = []

    try:
        manager = create_manager(siemplify)

        # The Account ID parameter wins. Fall back to User entities in the alert.
        targets = parse_account_input(account_id_param)
        source = SOURCE_PARAMETER
        if not targets:
            targets = user_entity_accounts(siemplify.target_entities)
            source = SOURCE_ENTITIES
        siemplify.LOGGER.info(f"Resolved {len(targets)} account(s) from {source}: {targets}")

        for account_id in targets:
            try:
                manager.block_account(account_id, reason)
                blocked.append(account_id)
            except PortnoxAuthError:
                raise
            except PortnoxError as block_error:
                siemplify.LOGGER.error(f"Failed to block {account_id}: {block_error}")
                failed.append(account_id)

        blocked_lower = {account.lower() for account in blocked}
        blocked_entities = [
            e
            for e in siemplify.target_entities
            if e.entity_type == EntityTypes.USER and e.identifier.lower() in blocked_lower
        ]
        for entity in blocked_entities:
            entity.is_suspicious = True
        if blocked_entities:
            siemplify.update_entities(blocked_entities)

        siemplify.result.add_result_json({
            "blocked": blocked,
            "failed": failed,
            "reason": reason,
            "resolved_from": source,
        })

        messages = []
        if blocked:
            messages.append(
                f"Successfully blocked accounts on the following entities using {INTEGRATION_DISPLAY_NAME}: "
                f"{', '.join(blocked)}"
            )
        if failed:
            messages.append(
                f"Action wasn't able to block accounts on the following entities using {INTEGRATION_DISPLAY_NAME}: "
                f"{', '.join(failed)}"
            )
        if not targets:
            messages.append(
                "No accounts to block. Provide the Account ID parameter or run the action on User entities."
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
