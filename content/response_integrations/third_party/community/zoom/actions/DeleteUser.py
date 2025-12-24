from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.parameters import Parameters
from ..core.ZoomManager import NotFoundError, ZoomManager

INTEGRATION_NAME = "Zoom"
SCRIPT_NAME = "Delete User"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    # Extracting the integration params
    siemplify.LOGGER.info("------------------ Main Started -------------------")

    conf = siemplify.get_configuration(INTEGRATION_NAME)
    parameters = Parameters.from_conf(conf)

    # Extracting the action params

    user_email = siemplify.extract_action_param("Deleted User Email")

    transfer_recording = siemplify.extract_action_param("Transfer Recordings")

    transfer_webinar = siemplify.extract_action_param("Transfer Webinar")

    transfer_meeting = siemplify.extract_action_param("Transfer Meeting")

    transfer_email = siemplify.extract_action_param("Transfer Email")

    json_result = {}

    try:
        # Creating a ZoomManager object instance
        zoom_manager = ZoomManager(**parameters.as_dict(), logger=siemplify.LOGGER)

        # If transfer is not required or there is nothing to transfer, don't even try it
        if not (
            transfer_recording == "true" and zoom_manager.list_recordings(user_email)
        ):
            transfer_recording = "false"
        if not (transfer_webinar == "true" and zoom_manager.list_webinars(user_email)):
            transfer_webinar = "false"
        if not (transfer_meeting == "true" and zoom_manager.list_meetings(user_email)):
            transfer_meeting = "false"

        zoom_manager.delete_user(
            user_email,
            transfer_recording,
            transfer_webinar,
            transfer_meeting,
            transfer_email,
        )

        output_message = "The account was deleted successfully"
        json_result["isDeleted"] = result_value = True
        status = EXECUTION_STATE_COMPLETED

    except NotFoundError:
        output_message = "The account was not deleted: user doesn't exist"
        json_result["isDeleted"] = result_value = False
        status = EXECUTION_STATE_FAILED

    except Exception as e:
        output_message = f"Unknown error: {e}"
        json_result["isDeleted"] = result_value = False
        status = EXECUTION_STATE_FAILED

    finally:
        # Adding json result to the action
        siemplify.result.add_result_json(json_result)
        siemplify.end(output_message, result_value, status)

        if status is EXECUTION_STATE_FAILED:
            siemplify.LOGGER.error("Error trying to delete a user")
            siemplify.LOGGER.exception(output_message)
            raise


if __name__ == "__main__":
    main()
