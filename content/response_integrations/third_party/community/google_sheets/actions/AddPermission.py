from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.google_sheets import GoogleSheetFactory

IDENTIFIER = "Google Sheet"


@output_handler
def main():
    siemplify = SiemplifyAction()

    credentials_json = siemplify.extract_configuration_param(
        IDENTIFIER,
        "Credentials Json",
    )

    sheet_id = siemplify.extract_action_param(param_name="Sheet Id", is_mandatory=True)
    role = siemplify.extract_action_param(param_name="Role", is_mandatory=True)
    emails = siemplify.extract_action_param(param_name="Emails")

    try:
        client = GoogleSheetFactory(credentials_json).create_client()
        client.insert_permission(sheet_id, emails, perm_type="user", role=role.lower())
    except Exception as err:
        status = EXECUTION_STATE_FAILED
        message = str(err)
    else:
        status = EXECUTION_STATE_COMPLETED
        message = "The permission was granted successfully"

    siemplify.end(message, status is EXECUTION_STATE_COMPLETED, status)


if __name__ == "__main__":
    main()
