from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.GoogleDocsManager import GoogleDocsManager

IDENTIFIER = "Google Docs"


@output_handler
def main():
    siemplify = SiemplifyAction()

    credentials_json = siemplify.extract_configuration_param(
        IDENTIFIER,
        "Credentials Json",
    )

    title = siemplify.extract_action_param(param_name="Title", is_mandatory=True)
    role = siemplify.extract_action_param(param_name="Role", is_mandatory=True)
    user_emails_to_add = siemplify.extract_action_param(
        param_name="Emails",
        is_mandatory=True,
    )

    google_doc_manager = GoogleDocsManager(credentials_json)
    res = google_doc_manager.create_document(title, role, user_emails_to_add)

    siemplify.result.add_result_json(res)

    siemplify.end("Document created successfully", res["id"])


if __name__ == "__main__":
    main()
