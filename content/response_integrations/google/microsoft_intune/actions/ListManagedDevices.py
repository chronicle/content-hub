from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon import construct_csv, extract_action_param, extract_configuration_param

from microsoft_intune.core.constants import (
    AZURE_AD_ENDPOINT_DEFAULT_VALUE,
    FILTER_KEY_DEFAULT_VALUE,
    FILTER_LOGIC_DEFAULT_VALUE,
    INTEGRATION_NAME,
    LIST_DEVICE_TABLE_NAME,
    LIST_MANAGED_DEVICES_SCRIPT_NAME,
    MAX_RECORDS_TO_RETURN_DEFAULT_VALUE,
    MICROSOFT_GRAPH_ENDPOINT_DEFAULT_VALUE,
)
from microsoft_intune.core.exceptions import InvalidMaxRecordsValueError, WrongFilterKeyError
from microsoft_intune.core.MicrosoftIntuneManager import MicrosoftIntuneManager


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_MANAGED_DEVICES_SCRIPT_NAME
    siemplify.LOGGER.info("--------------- Main - Param Init ---------------")
    azure_ad_endpoint = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Azure AD endpoint",
        is_mandatory=True,
        print_value=True,
        default_value=AZURE_AD_ENDPOINT_DEFAULT_VALUE,
    )

    microsoft_graph_endpoint = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Microsoft Graph Endpoint",
        is_mandatory=True,
        print_value=True,
        default_value=MICROSOFT_GRAPH_ENDPOINT_DEFAULT_VALUE,
    )

    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
        print_value=True,
    )

    client_secret_value = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret Value",
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )

    azure_ad_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Azure Active Directory ID",
        is_mandatory=True,
        print_value=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
        default_value=True,
    )

    # Action parameters
    filter_key = extract_action_param(
        siemplify,
        param_name="Filter Key",
        default_value=FILTER_KEY_DEFAULT_VALUE,
        print_value=True,
    )

    filter_logic = extract_action_param(
        siemplify,
        param_name="Filter Logic",
        default_value=FILTER_LOGIC_DEFAULT_VALUE,
        print_value=True,
    )

    filter_value = extract_action_param(
        siemplify, param_name="Filter Value", print_value=True
    )

    try:
        max_records_to_return = extract_action_param(
            siemplify,
            param_name="Max Records To Return",
            input_type=int,
            default_value=MAX_RECORDS_TO_RETURN_DEFAULT_VALUE,
            print_value=True,
        )
    except Exception as e:
        siemplify.LOGGER.error(e)
        siemplify.LOGGER.error(
            'Failed to use "Max Records To Return" value. Using default of 50.'
        )
        max_records_to_return = MAX_RECORDS_TO_RETURN_DEFAULT_VALUE

    siemplify.LOGGER.info("---------------- Main - Started ----------------")
    output_message = ""
    result = True
    status = EXECUTION_STATE_COMPLETED
    json_result = []

    try:
        if max_records_to_return is not None and not 1 <= max_records_to_return <= 100:
            raise InvalidMaxRecordsValueError

        if filter_key == "Select One" and (
            filter_logic == "Equal" or filter_logic == "Contains"
        ):
            raise WrongFilterKeyError(
                "Reason: you need to select a field " 'from the "Filter Key" parameter.'
            )

        siemplify.LOGGER.info("Initializing manager")
        manager = MicrosoftIntuneManager(
            azure_ad_endpoint=azure_ad_endpoint,
            microsoft_graph_endpoint=microsoft_graph_endpoint,
            client_id=client_id,
            client_secret_value=client_secret_value,
            azure_ad_id=azure_ad_id,
            verify_ssl=verify_ssl,
            logger=siemplify.LOGGER,
        )

        siemplify.LOGGER.info("Fetching all devices using filters")
        action_result = manager.list_managed_devices(
            filter_key=filter_key,
            filter_logic=filter_logic,
            filter_value=filter_value,
            max_records_to_return=max_records_to_return,
        )
        devices = action_result.devices

        if len(devices) > 0:
            siemplify.result.add_data_table(
                LIST_DEVICE_TABLE_NAME,
                construct_csv([device.to_csv() for device in devices]),
            )
            output_message += (
                "\nSuccessfully found managed device(s) "
                "for the provided criteria in the Microsoft Intune instance"
            )

            for device in devices:
                json_result.append(device.to_json())

            siemplify.result.add_result_json(json_result)

            if not filter_value:
                output_message += (
                    "\nThe filter was not applied, "
                    "because parameter “Filter Value” has an empty value"
                )

        else:
            output_message += (
                "\nNo managed devices were found for "
                "the provided criteria in the Microsoft Intune instance"
            )
            result = False

    except WrongFilterKeyError as err:
        siemplify.LOGGER.error(err)
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action {LIST_MANAGED_DEVICES_SCRIPT_NAME}. "
            f"Reason: {err}"
        )

    except InvalidMaxRecordsValueError:
        result = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Error executing action {LIST_MANAGED_DEVICES_SCRIPT_NAME}. "
            "Reason: Invalid value was provided for "
            f'"Max Records to Return": {max_records_to_return}. '
            "Positive number in range from 1 to 100 should be provided."
        )
        siemplify.LOGGER.error(output_message)

    except Exception as e:
        output_message = (
            f"Error executing action  {LIST_MANAGED_DEVICES_SCRIPT_NAME}. "
            f"Reason: {e}"
        )
        result = False
        status = EXECUTION_STATE_FAILED

        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("---------------- Main - Finished ----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
