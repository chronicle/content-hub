from __future__ import annotations
import sys

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.SiemplifyUtils import output_handler
from ..core.constants import INTEGRATION_NAME, DISMISS_THREAT_SCRIPT_NAME
from ..core.McAfeeMvisionEDRManager import McAfeeMvisionEDRManager
from ..core.McAfeeMvisionEDRExceptions import (
    McAfeeMvisionEDRException,
    CaseNotFoundException,
    TaskFailedException,
    UnknownTaskStatusException,
)
from soar_sdk.SiemplifyAction import SiemplifyAction


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = DISMISS_THREAT_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Integration Parameters
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )

    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )

    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=False,
        input_type=str,
        print_value=False,
    )

    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        input_type=str,
    )

    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        input_type=str,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )

    threat_id = extract_action_param(
        siemplify,
        param_name="Threat ID",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        client = McAfeeMvisionEDRManager(
            api_root=api_root,
            username=username,
            password=password,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
        )

        if is_first_run:
            siemplify.LOGGER.info(
                "First run of the action, creating threat dismission task"
            )
            task = client.create_dismiss_threat_task(threat_id)
            siemplify.LOGGER.info(
                f"Threat dismission task was created with ID {task.id}"
            )
        else:
            task_id = extract_action_param(
                siemplify,
                param_name="additional_data",
                is_mandatory=True,
                input_type=int,
                print_value=True,
            )
            siemplify.LOGGER.info(f"Extracting task id {task_id} from the previous run")
            task = client.get_task_status(task_id)

        if task.is_failed:
            raise TaskFailedException(f"Task with ID {task.id} failed")

        elif task.is_completed:
            output_message = f"Successfully dismissed threat with ID {threat_id}"
            is_success = "true"
            status = EXECUTION_STATE_COMPLETED

        elif task.is_in_progress:
            output_message = (
                f"Dismission task {task.id} with threat ID {threat_id} in progress..."
            )
            is_success = task.id
            status = EXECUTION_STATE_INPROGRESS

        else:
            raise UnknownTaskStatusException(
                f"Unknown status {task.status} for threat dismission with id {threat_id}"
            )

        siemplify.LOGGER.info(output_message)

    except CaseNotFoundException as e:
        output_message = str(e)
        is_success = "false"
        status = EXECUTION_STATE_COMPLETED
        siemplify.LOGGER.info(output_message)
    except (TaskFailedException, UnknownTaskStatusException) as e:
        output_message = f"Failed to dismiss threat with id {threat_id}"
        is_success = "false"
        status = EXECUTION_STATE_COMPLETED
        siemplify.LOGGER.info(output_message)
    except (Exception, McAfeeMvisionEDRException) as e:
        output_message = f'Error executing action "Dismiss Threat". Reason: {e}'
        is_success = "false"
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, is_success, status)


if __name__ == "__main__":
    first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(first_run)
