from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from ..core.PortnoxManager import PortnoxManager, PortnoxAuthError

INTEGRATION_NAME = "PortnoxCloud"
SCRIPT_NAME = "Block Account"


def parse_account_input(raw):
    """Turn whatever a playbook placeholder produced into a list of account names.

    Placeholders are not guaranteed to deliver a bare string. A YARA-L outcome
    variable built with array_distinct() arrives as a JSON-ish list, e.g.

        ["user@corp.com"]          -> ["user@corp.com"]
        ['a@corp.com','b@corp.com'] -> ["a@corp.com", "b@corp.com"]
        user@corp.com, other@corp.com -> ["user@corp.com", "other@corp.com"]
        user@corp.com              -> ["user@corp.com"]

    Rather than failing on the bracketed form, normalise it here.
    """
    if raw is None:
        return []
    text = str(raw).strip()
    if not text:
        return []

    # Strip one layer of list brackets if present.
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]

    accounts = []
    for chunk in text.split(","):
        value = chunk.strip().strip('"').strip("'").strip()
        if value and value.lower() not in ("none", "null"):
            accounts.append(value)
    return accounts


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

    account_id_param = siemplify.extract_action_param(
        param_name="Account ID", is_mandatory=False, print_value=True)
    reason = siemplify.extract_action_param(
        param_name="Reason", is_mandatory=False, print_value=True,
        default_value="Blocked by Google SecOps SOAR")

    blocked, failed = [], []

    try:
        manager = PortnoxManager(
            api_root=api_root, api_token=api_token, username=username,
            password=password, verify_ssl=verify_ssl, logger=siemplify.LOGGER)

        # The Account ID parameter wins. Fall back to User entities in the alert.
        targets = parse_account_input(account_id_param)
        source = "Account ID parameter"
        if not targets:
            targets = [e.identifier for e in siemplify.target_entities
                       if e.entity_type == EntityTypes.USER]
            source = "User entities in the alert"

        siemplify.LOGGER.info("Resolved {0} account(s) from {1}: {2}".format(
            len(targets), source, targets))

        for account_id in targets:
            try:
                manager.block_account(account_id, reason)
                blocked.append(account_id)
                siemplify.LOGGER.info("Blocked {0}".format(account_id))
            except Exception as block_error:
                siemplify.LOGGER.error("Block failed for {0}: {1}".format(
                    account_id, block_error))
                failed.append("{0}: {1}".format(account_id, block_error))

        for entity in siemplify.target_entities:
            if entity.entity_type == EntityTypes.USER and entity.identifier in blocked:
                entity.is_suspicious = True
        siemplify.update_entities(
            [e for e in siemplify.target_entities
             if e.entity_type == EntityTypes.USER and e.identifier in blocked])

        siemplify.result.add_result_json({
            "blocked": blocked, "failed": failed,
            "reason": reason, "resolved_from": source})

        status = EXECUTION_STATE_COMPLETED
        result_value = str(bool(blocked))
        parts = []
        if blocked:
            parts.append("Blocked in Portnox Cloud: {0}".format(", ".join(blocked)))
        if failed:
            parts.append("Failed: {0}".format("; ".join(failed)))
        if not targets:
            parts.append(
                "No account to block. The Account ID parameter was empty and the alert "
                "contains no User entities. Supply Account ID via a placeholder, or map "
                "the account field to a User entity in the ontology.")
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
        output_message = "Block Account failed. Error: {0}".format(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
