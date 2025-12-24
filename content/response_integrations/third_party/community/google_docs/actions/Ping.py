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

    google_doc_manager = GoogleDocsManager(credentials_json)
    google_doc_manager.test_connectivity()

    siemplify.end("Connected successfully", True)


if __name__ == "__main__":
    main()
