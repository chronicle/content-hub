from __future__ import annotations

import json

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

    document_id = siemplify.extract_action_param(
        param_name="Document Id",
        is_mandatory=True,
    )
    json_str = siemplify.extract_action_param(param_name="Json", is_mandatory=True)

    json_object = json.loads(json_str)
    items = json_object["items"]
    requests = []

    for item in items:
        start_index = item["start_index"]
        end_index = item["end_index"]

        item_to_delete = {
            "deleteContentRange": {
                "range": {"startIndex": start_index, "endIndex": end_index},
            },
        }
        requests.append(item_to_delete)

    google_doc_manager = GoogleDocsManager(credentials_json)
    res = google_doc_manager.execute_request(document_id, requests)

    siemplify.result.add_result_json(res)

    siemplify.end("Content was successfully removed", document_id)


if __name__ == "__main__":
    main()
