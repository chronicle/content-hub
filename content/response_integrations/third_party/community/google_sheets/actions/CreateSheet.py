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
    sheet_name = siemplify.extract_action_param(
        param_name="Sheet Name",
        is_mandatory=True,
    )
    emails_to_share = siemplify.extract_action_param(param_name="Share with emails")

    try:
        client = GoogleSheetFactory(credentials_json).create_client()
        sheet = client.create(sheet_name)

        if emails_to_share:
            emails = emails_to_share.split(";")
            for email in emails:
                sheet.share(email, perm_type="user", role="writer")
    except Exception as err:
        status = EXECUTION_STATE_FAILED
        message = str(err)
        sheet_id = -1
    else:
        status = EXECUTION_STATE_COMPLETED
        message = "The Sheet was created successfully"
        sheet_id = sheet.id

    siemplify.end(message, sheet_id, status)


if __name__ == "__main__":
    main()
