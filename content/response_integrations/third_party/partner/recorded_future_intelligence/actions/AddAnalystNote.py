############################## TERMS OF USE ################################### # noqa: E266
# The following code is provided for demonstration purposes only, and should  #
# not be used without independent verification. Recorded Future makes no      #
# representations or warranties, express, implied, statutory, or otherwise,   #
# regarding this code, and provides it strictly "as-is".                      #
# Recorded Future shall not be liable for, and you assume all risk of         #
# using the foregoing.                                                        #
###############################################################################

from __future__ import annotations

from psengine.analyst_notes import AnalystNoteMgr, AnalystNotePublishError
from psengine.config import Config
from pydantic import ValidationError
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.constants import PROVIDER_NAME, TOPIC_MAP
from ..core.version import __version__ as version


@output_handler
def main():
    siemplify = SiemplifyAction()

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

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    is_success = True
    output_message = ""
    status = EXECUTION_STATE_COMPLETED

    entities = "\n".join([entity.identifier for entity in siemplify.target_entities])
    note_text = note_text + f"\n\nEntities collected from case: {entities}"

    try:
        siemplify.LOGGER.info("Initializing psengine configuration")
        Config.init(
            client_verify_ssl=verify_ssl,
            rf_token=api_key,
            app_id=f"ps-google-soar/{version}",
        )
        siemplify.LOGGER.info("Initializing psengine AnalystNoteMgr")
        note_mgr = AnalystNoteMgr()
        siemplify.LOGGER.info("Publishing Analyst Note")
        analyst_note_resp = note_mgr.publish(title=note_title, text=note_text, topic=topic)
        data = analyst_note_resp.json()
        siemplify.result.add_result_json(data)
        output_message += (
            f"Successfully published Analyst Note {analyst_note_resp.note_id} in Recorded Future."
        )

    except ValueError as err:
        output_message = f"Analyst Note Manager ValueError: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except ValidationError as err:
        output_message = f"Error with Analyst Note Manager publish parameters: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except AnalystNotePublishError as err:
        output_message = f"Error publishing Analyst Note: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except Exception as err:
        output_message = f"Error executing Add Analyst Note action: {err}"
        is_success = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {is_success}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, is_success, status)


if __name__ == "__main__":
    main()
