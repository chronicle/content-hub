from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

"""
This adapter is suitable for jsons in the following format:
{
    "results": [
        { 
            #log
        },
        .....
    ]
}

and returns a json in the following format: 
{
    "results": [
        { 
            "entityType": "field_from_json",
            "entityIdentifier": "value_from_json"
        },
        .....
    ]
}

This action will return EXECUTION_STATE_COMPLETED only when a requested field was found.
"""


@output_handler
def main():
    siemplify = SiemplifyAction()

    search_fields = siemplify.extract_action_param("fields_to_search")
    raw_json = siemplify.extract_action_param("raw_json")
    output = {"results": []}
    status = EXECUTION_STATE_FAILED  # default value. Will considered success only if found values
    is_success = False

    try:
        fields = [f.strip() for f in search_fields.split(",")]
        json_obj = json.loads(raw_json)
        siemplify.LOGGER.info("Retrieved fields to search and json")

        if (
            fields is not None
            and len(fields) > 0
            and json_obj is not None
            and len(json_obj) > 0
        ):
            for result in json_obj["results"]:
                for field in fields:
                    siemplify.LOGGER.info(f"Searching field: {field}")
                    if field in result:
                        result_parse = {
                            "entityType": field,
                            "entityIdentifier": result[field],
                        }
                        output["results"].append(result_parse)
                    else:
                        siemplify.LOGGER.info(
                            f"Couldn't find field {field} in given json",
                        )

        siemplify.LOGGER.info(
            f"Found {len(output['results'])} out of given {len(fields)} fields",
        )
        siemplify.LOGGER.info(f"{output}")

        if len(output["results"]) > 0:
            output_json = json.dumps(output)
            siemplify.result.add_result_json(output_json)
            status = EXECUTION_STATE_COMPLETED
            is_success = True

    except Exception as e:
        siemplify.LOGGER.error(f"Error occurred while searching fields in json: {e}")

    output_message = get_output_by_status(status)
    siemplify.end(output_message, is_success, status)


def get_output_by_status(status):
    if status == EXECUTION_STATE_COMPLETED:
        return "Json adapter script finished successfully with results"
    return "Json adapter script could not filter json"


if __name__ == "__main__":
    main()
