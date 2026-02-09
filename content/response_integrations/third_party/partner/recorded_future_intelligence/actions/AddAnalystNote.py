############################## TERMS OF USE ################################### # noqa: E266
# The following code is provided for demonstration purposes only, and should  #
# not be used without independent verification. Recorded Future makes no      #
# representations or warranties, express, implied, statutory, or otherwise,   #
# regarding this code, and provides it strictly "as-is".                      #
# Recorded Future shall not be liable for, and you assume all risk of         #
# using the foregoing.                                                        #
###############################################################################

from __future__ import annotations

import json
import sys
from typing import NoReturn

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, resume_stdout
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.constants import ADD_ANALYST_NOTE_SCRIPT_NAME, PROVIDER_NAME, TOPIC_MAP
from ..core.exceptions import RecordedFutureUnauthorizedError
from ..core.RecordedFutureManager import RecordedFutureManager

SUITABLE_ENTITY_TYPES = [
    EntityTypes.HOSTNAME,
    EntityTypes.CVE,
    EntityTypes.FILEHASH,
    EntityTypes.ADDRESS,
    EntityTypes.URL,
]


@output_handler
def main():
    siemplify = SiemplifyAction()

    def end_script() -> NoReturn:
        output_object = siemplify._build_output_object()
        resume_stdout()
        sys.stdout.write(json.dumps(output_object))
        sys.exit()

    siemplify.end_script = end_script

    siemplify.script_name = ADD_ANALYST_NOTE_SCRIPT_NAME

    api_url = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="ApiUrl",
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="ApiKey",
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    note_title = extract_action_param(
        siemplify,
        param_name="Note Title",
        is_mandatory=True,
    )
    note_text = extract_action_param(
        siemplify,
        param_name="Note Text",
        is_mandatory=True,
    )
    topic = extract_action_param(
        siemplify,
        param_name="Topic",
        default_value=TOPIC_MAP["None"],
    )

    entities = "\n".join([entity.identifier for entity in siemplify.target_entities])
    note_text = note_text + f"\n\nEntities collected from case: {entities}"
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    success = True
    output_message = "Note uploaded successfully"
    status = EXECUTION_STATE_COMPLETED
    note_id = ""

    try:
        manager = RecordedFutureManager(
            api_url=api_url,
            api_key=api_key,
            verify_ssl=verify_ssl,
        )

        note_id = manager.get_analyst_notes(
            title=note_title,
            text=note_text,
            topic=TOPIC_MAP[topic],
        ).document_id

    except Exception as err:
        output_message = f"Error executing action {ADD_ANALYST_NOTE_SCRIPT_NAME}. Reason: {err}"
        if isinstance(err, RecordedFutureUnauthorizedError):
            output_message = "Unauthorized - please check your API token and try again. {}"
        success = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  succeded: {success}\n  note_id: {note_id}",
    )
    siemplify.end(output_message, note_id, status)


if __name__ == "__main__":
    main()
