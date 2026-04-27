from __future__ import annotations
from ..core import utils

from ..core.GoogleGRRManager import GoogleGRRManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.consts import INTEGRATION_NAME, STOP_A_HUNT
from ..core.exceptions import GoogleGRRNotFoundException, GoogleGRRStatusCodeException


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {STOP_A_HUNT}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )

    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )

    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=False,
        print_value=True,
    )

    hunt_ids = extract_action_param(
        siemplify,
        param_name="Hunt ID",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    not_found_hunts = []
    not_start_pause_hunts = []
    stopped_hunts = []
    json_results = []
    output_message = ""
    result_value = False

    try:
        manager = GoogleGRRManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )

        #  Get list of hunt ids from hunts comma separated value
        hunt_ids = utils.load_csv_to_list(hunt_ids, "Hunt ID")

        siemplify.LOGGER.info("Start stopping hunts")
        for hunt_id in hunt_ids:
            try:
                siemplify.LOGGER.info(f"Stop hunt with id: {hunt_id}")
                hunt = manager.stop_hunt(hunt_id=hunt_id)
                siemplify.LOGGER.info(f"Successfully stopped hunt with id: {hunt_id}")

                stopped_hunts.append(hunt_id)
                json_results.append({"Hunt_ID": hunt_id, "State": hunt.state})

            except GoogleGRRNotFoundException as e:
                not_found_hunts.append(hunt_id)
                siemplify.LOGGER.error(
                    f"Failed to stop hunt with id: {hunt_id}. Error: {e}"
                )
                siemplify.LOGGER.exception(e)

            except GoogleGRRStatusCodeException as e:
                not_start_pause_hunts.append(hunt_id)
                siemplify.LOGGER.error(
                    f"Failed to stop hunt with id: {hunt_id}. Error: {e}"
                )
                siemplify.LOGGER.exception(e)

        if stopped_hunts:
            siemplify.result.add_result_json(json_results)
            output_message += f"Successfully stopped the following hunts: {', '.join(stopped_hunts)}. \n"
            result_value = True

        if not_found_hunts:
            output_message += (
                f"Could not stop the following hunts. {', '.join(not_found_hunts)} could not be"
                f" found in GRR. \n"
            )

        if not_start_pause_hunts:
            output_message += (
                f"Could not stop the following hunts: {', '.join(not_start_pause_hunts)}. Hunt can "
                f"only be stopped from STARTED or PAUSED states. \n"
            )

        status = EXECUTION_STATE_COMPLETED

    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action “Stop a Hunt” for {hunt_ids} hunt. Reason: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
