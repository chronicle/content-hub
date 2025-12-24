from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.parameters import Parameters
from ..core.ZoomManager import ZoomManager

INTEGRATION_NAME = "Zoom"
SCRIPT_NAME = "Create Meeting"


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
        meeting_topic = siemplify.extract_action_param("Meeting Topic")
        meeting_type = siemplify.extract_action_param("Meeting Type")
        meeting_start_time = siemplify.extract_action_param("Meeting Start Time")
        meeting_duration = siemplify.extract_action_param("Meeting Duration")
        meeting_time_zone = siemplify.extract_action_param("Time Zone")
        meeting_recording_type = siemplify.extract_action_param("Auto Recording Type")
        host_email_address = siemplify.extract_action_param("Host Email Address")

        zoom_manager = ZoomManager(**parameters.as_dict(), logger=siemplify.LOGGER)

        created_meeting_details = zoom_manager.create_meeting(
            meeting_topic,
            meeting_type,
            meeting_start_time,
            meeting_duration,
            meeting_time_zone,
            meeting_recording_type,
            host_email_address,
        )

        if created_meeting_details:
            output_message = "The meeting was created successfully"
            result_value = True
            status = EXECUTION_STATE_COMPLETED

            siemplify.result.add_link(
                title="Meeting URL link",
                link=created_meeting_details.get("join_url"),
            )

        else:
            output_message = "The meeting wasn't created"
            result_value = False
            status = EXECUTION_STATE_FAILED

        siemplify.result.add_result_json(created_meeting_details)

        siemplify.LOGGER.info(
            "Script execution completed: \n"
            f"    Output message: {output_message} \n"
            f"    Result value: {result_value} \n",
        )

    except Exception as e:
        result_value = False
        output_message = f"Error trying to create a meeting: {e}"
        status = EXECUTION_STATE_FAILED

    finally:
        siemplify.end(output_message, result_value, status)
        if status is EXECUTION_STATE_FAILED:
            siemplify.LOGGER.error("Error trying to create a meeting")
            siemplify.LOGGER.exception(output_message)
            raise


if __name__ == "__main__":
    main()
