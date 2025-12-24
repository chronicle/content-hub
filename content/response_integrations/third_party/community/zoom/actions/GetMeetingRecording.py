from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.parameters import Parameters
from ..core.ZoomManager import ZoomManager

INTEGRATION_NAME = "Zoom"
SCRIPT_NAME = "Get Meeting Recording"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    # Extracting the integration params
    siemplify.LOGGER.info("------------------ Main Started -------------------")

    conf = siemplify.get_configuration(INTEGRATION_NAME)
    parameters = Parameters.from_conf(conf)

    try:
        # Extracting the action params
        meeting_id = siemplify.extract_action_param("Meeting ID")

        # Creating a ZoomManager object instance
        zoom_manager = ZoomManager(**parameters.as_dict(), logger=siemplify.LOGGER)

        json_result = {}

        meeting_recording_details = zoom_manager.get_meeting_recording(meeting_id)

        meeting_recording_url = meeting_recording_details.get("share_url")

        json_result["meetingRecordingDetails"] = meeting_recording_details
        output_message = "The meeting recording was fetched"
        result_value = meeting_recording_url

        # Adding the image URL link
        title = "Recording meeting URL"
        link = meeting_recording_url
        siemplify.result.add_link(title, link)

        # Adding json result to the action
        siemplify.result.add_result_json(json_result)

        status = EXECUTION_STATE_COMPLETED

    except Exception as e:
        result_value = None
        output_message = f"Couldn't get the meeting recording: {e}"
        status = EXECUTION_STATE_FAILED

    finally:
        siemplify.end(output_message, result_value, status)

        if status is EXECUTION_STATE_FAILED:
            siemplify.LOGGER.error("Error trying to create a meeting")
            siemplify.LOGGER.exception(output_message)
            raise


if __name__ == "__main__":
    main()
