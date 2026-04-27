from __future__ import annotations
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from ..core.AWSGuardDutyManager import AWSGuardDutyManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import INTEGRATION_NAME
from ..core.datamodels import FILE_FORMATS


SCRIPT_NAME = "Create a Trusted IP list"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    aws_access_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AWS Access Key ID",
        is_mandatory=True,
    )

    aws_secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AWS Secret Key",
        is_mandatory=True,
    )

    aws_default_region = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AWS Default Region",
        is_mandatory=True,
    )

    detector_id = extract_action_param(
        siemplify, param_name="Detector ID", is_mandatory=True, print_value=True
    )
    name = extract_action_param(
        siemplify, param_name="Name", is_mandatory=True, print_value=True
    )
    file_format = extract_action_param(
        siemplify, param_name="File Format", is_mandatory=True, print_value=True
    )
    file_location = extract_action_param(
        siemplify, param_name="File Location", is_mandatory=True, print_value=True
    )
    activate = extract_action_param(
        siemplify,
        param_name="Activate",
        is_mandatory=True,
        print_value=True,
        input_type=bool,
    )
    aws_region = extract_action_param(
        siemplify,
        param_name="AWS Region",
        is_mandatory=False,
        print_value=True,
        default_value=aws_default_region,
    )

    file_format = FILE_FORMATS[file_format]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    json_results = {}

    try:
        siemplify.LOGGER.info("Connecting to AWS GuardDuty Service")
        manager = AWSGuardDutyManager(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_default_region=aws_region,
        )
        manager.test_connectivity()  # this validates the credentials
        siemplify.LOGGER.info("Successfully connected to AWS GuardDuty service")

        siemplify.LOGGER.info(f"Creating IP list {name}.")
        ip_set_id = manager.create_ip_set(
            detector_id=detector_id,
            name=name,
            file_format=file_format,
            file_location=file_location,
            activate=activate,
        )
        siemplify.LOGGER.info(f"Successfully created IP list {ip_set_id}.")
        json_results["TrustedIPID"] = ip_set_id

        status = EXECUTION_STATE_COMPLETED
        output_message = (
            f"Successfully created new Trusted IP List '{name}' in AWS GuardDuty."
        )
        result_value = "true"

    except Exception as error:  # action failed
        siemplify.LOGGER.error(
            f"Error executing action '{SCRIPT_NAME}'. Reason: {error}"
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Error executing action '{SCRIPT_NAME}'. Reason: {error}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.result.add_result_json(json_results)
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
