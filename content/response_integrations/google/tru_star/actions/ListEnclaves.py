from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.TruSTARManager import TruSTARManager
from ..core.consts import (
    INTEGRATION_NAME,
    LIST_ENCLAVES,
    DEFAULT_MAX_ENCLAVES,
    EQUAL_ENCLAVE_FILTER_OPERATOR,
    CONTAINS_ENCLAVE_FILTER_OPERATOR,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {LIST_ENCLAVES}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        is_mandatory=True,
        print_value=True,
    )
    api_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Secret",
        is_mandatory=True,
        print_value=False,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=True,
        is_mandatory=True,
        print_value=True,
    )

    filter_logic = extract_action_param(
        siemplify,
        param_name="Filter Logic",
        default_value=EQUAL_ENCLAVE_FILTER_OPERATOR,
        is_mandatory=False,
        print_value=True,
    )
    filter_value = extract_action_param(
        siemplify, param_name="Filter Value", is_mandatory=False, print_value=True
    )
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    status = EXECUTION_STATE_COMPLETED

    found_enclaves = []

    try:
        max_enclaves_to_return = extract_action_param(
            siemplify,
            param_name="Max Enclaves To Return",
            input_type=int,
            is_mandatory=False,
            print_value=True,
            default_value=DEFAULT_MAX_ENCLAVES,
        )
        if max_enclaves_to_return <= 0:
            siemplify.LOGGER.info(
                f'"Max Enclaves To Return" parameter must be positive. Using default of: {DEFAULT_MAX_ENCLAVES}'
            )
            max_enclaves_to_return = DEFAULT_MAX_ENCLAVES

        manager = TruSTARManager(
            api_root=api_root,
            api_key=api_key,
            api_secret=api_secret,
            verify_ssl=verify_ssl,
        )
        enclaves = manager.list_enclaves()[:max_enclaves_to_return]
        siemplify.LOGGER.info(f"Listed {len(enclaves)} available enclaves")
        if filter_value:
            for enclave in enclaves:
                if filter_logic == EQUAL_ENCLAVE_FILTER_OPERATOR:
                    if filter_value == enclave.name:
                        found_enclaves.append(enclave)
                if filter_logic == CONTAINS_ENCLAVE_FILTER_OPERATOR:
                    if filter_value in enclave.name:
                        found_enclaves.append(enclave)
        else:
            found_enclaves.extend(enclaves)

        if found_enclaves:
            result_value = True
            siemplify.result.add_result_json(
                [enclave.as_json() for enclave in found_enclaves]
            )
            siemplify.result.add_data_table(
                title="Related Reports",
                data_table=construct_csv(
                    [enclave.as_csv() for enclave in found_enclaves]
                ),
            )
            output_message = (
                f"Successfully returned available enclaves in {INTEGRATION_NAME}"
            )
        else:
            output_message = f"No related enclaves were found in {INTEGRATION_NAME}"

    except Exception as error:
        status = EXECUTION_STATE_FAILED
        output_message = f'Error execution action "{LIST_ENCLAVES}". Reason: {error}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
