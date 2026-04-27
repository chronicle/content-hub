from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.MISPManager import MISPManager
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    construct_csv,
    flat_dict_to_csv,
)
from ..core.constants import INTEGRATION_NAME, GET_EVENT_DETAILS_SCRIPT_NAME


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_EVENT_DETAILS_SCRIPT_NAME
    status = EXECUTION_STATE_COMPLETED

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

    event_ids_string = extract_action_param(
        siemplify, param_name="Event ID", is_mandatory=True, print_value=True
    )
    return_attributes_info = extract_action_param(
        siemplify,
        param_name="Return Attributes Info",
        input_type=bool,
        default_value=True,
        print_value=True,
    )
    event_ids = [
        event_id.strip() for event_id in event_ids_string.split(",") if event_id.strip()
    ]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_json = {}
    output_message = ""
    result_value = True
    succeeded_ids = []
    failed_ids = []

    try:
        misp_manager = MISPManager(api_root, api_token, use_ssl, ca_certificate)

        for event_id in event_ids:
            try:
                siemplify.LOGGER.info(f"Fetching event {event_id} details.")
                event = misp_manager.get_event_by_id(event_id)
                siemplify.LOGGER.info(f"Found details for event {event_id}.")
                result_json[event_id] = event.raw_data
                siemplify.result.add_data_table(
                    f"Event {event_id} Details", flat_dict_to_csv(event.to_csv())
                )
                if return_attributes_info and event.attributes:
                    siemplify.result.add_data_table(
                        f"Event {event_id} Attributes Details",
                        construct_csv(
                            [attribute.to_csv() for attribute in event.attributes]
                        ),
                    )

                succeeded_ids.append(event_id)

            except Exception as e:
                siemplify.LOGGER.error(f"An error occurred on event {event_id}")
                siemplify.LOGGER.exception(e)
                failed_ids.append(event_id)

        if result_json:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(result_json)
            )

        if succeeded_ids:
            output_message += "Successfully retrieved information for the following events:\n   {}".format(
                "\n   ".join(succeeded_ids)
            )

        else:
            output_message += "No event details were found."
            result_value = False

        if failed_ids:
            output_message += "\n\nFailed to retrieved information for the following events:\n   {}".format(
                "\n   ".join(failed_ids)
            )

    except Exception as e:
        output_message = (
            f'Error executing action "{GET_EVENT_DETAILS_SCRIPT_NAME}". Reason: {e}'
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
