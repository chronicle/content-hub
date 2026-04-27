from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.MISPManager import MISPManager
from TIPCommon import extract_configuration_param, extract_action_param
from os import path
from ..core.utils import string_to_multi_value, adjust_categories
from ..core.exceptions import (
    MISPNotAcceptableNumberOrStringError,
    MISPInvalidFileError,
    MISPManagerEventIdNotFoundError,
)
from ..core.constants import INTEGRATION_NAME, UPLOAD_FILE_SCRIPT_NAME, DISTRIBUTION, COMMUNITY


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = UPLOAD_FILE_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Root"
    )
    api_token = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Key"
    )
    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Use SSL",
        default_value=False,
        input_type=bool,
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File - parsed into Base64 String",
    )
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    event_id = extract_action_param(
        siemplify, param_name="Event ID", is_mandatory=True, print_value=True
    )
    file_paths = list(
        set(
            string_to_multi_value(
                extract_action_param(
                    siemplify,
                    param_name="File Path",
                    print_value=True,
                    is_mandatory=True,
                )
            )
        )
    )
    category = adjust_categories(
        extract_action_param(
            siemplify,
            param_name="Category",
            print_value=True,
            default_value="External analysis",
        )
    )
    distribution = extract_action_param(
        siemplify,
        param_name="Distribution",
        print_value=True,
        default_value=str(DISTRIBUTION[COMMUNITY]),
    )
    to_ids = extract_action_param(
        siemplify,
        param_name="For Intrusion Detection System",
        print_value=True,
        input_type=bool,
        default_value=False,
    )
    comment = extract_action_param(siemplify, param_name="Comment", print_value=True)

    id_type = "ID" if event_id.isdigit() else "UUID"
    result_value = False
    status = EXECUTION_STATE_COMPLETED

    try:
        if distribution.lower() not in map(
            str, tuple(DISTRIBUTION.keys()) + tuple(DISTRIBUTION.values())
        ):
            raise MISPNotAcceptableNumberOrStringError(
                "Distribution",
                acceptable_strings=DISTRIBUTION.keys(),
                acceptable_numbers=DISTRIBUTION.values(),
            )
        distribution = int(
            DISTRIBUTION[distribution.lower()]
            if not distribution.isdigit()
            else distribution
        )

        invalid_file_paths = [
            file_path for file_path in file_paths if not path.isfile(file_path)
        ]

        if invalid_file_paths:
            raise MISPInvalidFileError(
                "the following files were not accessible:\n   {}".format(
                    "\n   ".join(invalid_file_paths)
                )
            )

        manager = MISPManager(api_root, api_token, use_ssl, ca_certificate)

        event_details = manager.get_event_by_id_or_raise(event_id)

        failed_upload_paths = []
        events = []

        for file_path in file_paths:
            try:
                events.append(
                    manager.upload_file(
                        file_path=file_path,
                        event_id=event_details.id,
                        distribution=distribution,
                        to_ids=to_ids,
                        category=category,
                        comment=comment,
                    )
                )
            except Exception as e:
                if isinstance(e, MISPManagerEventIdNotFoundError):
                    raise
                failed_upload_paths.append((file_path, str(e)))
                siemplify.LOGGER.exception(e)

        if events:
            event_details = manager.get_event_by_id(event_id)
            siemplify.result.add_result_json(event_details.to_json())
            result_value = event_details.id
            output_message = f"Successfully uploaded the provided files to the event {event_id} in {INTEGRATION_NAME}"
        else:
            output_message = f"Action wasn’t able to upload files to the event {event_id} in {INTEGRATION_NAME}"

    except Exception as e:
        output_message = f"Error executing action '{UPLOAD_FILE_SCRIPT_NAME}'. Reason: "
        output_message += (
            f"Event with {id_type} {event_id} was not found in {INTEGRATION_NAME}"
            if isinstance(e, MISPManagerEventIdNotFoundError)
            else str(e)
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
