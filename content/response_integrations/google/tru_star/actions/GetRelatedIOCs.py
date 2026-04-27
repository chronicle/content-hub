from __future__ import annotations
from collections import defaultdict

from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.TruSTARManager import TruSTARManager
from ..core.consts import (
    INTEGRATION_NAME,
    GET_RELATED_IOCS,
    DEFAULT_MAX_RELATED_IOCS,
    MAX_RELATED_IOCS,
    MIN_RELATED_IOCS,
    LIST_ENCLAVES,
)
from ..core.exceptions import TruSTARMissingEnclaveException
from ..core.utils import load_csv_to_list


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {GET_RELATED_IOCS}"
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

    enclave_filter = extract_action_param(
        siemplify, param_name="Enclave Filter", is_mandatory=False, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    status = EXECUTION_STATE_COMPLETED

    failed_enclaves = []
    found_enclaves_ids = []
    json_results = defaultdict(list)

    try:
        max_iocs_to_return = extract_action_param(
            siemplify,
            param_name="Max IOCs To Return",
            input_type=int,
            is_mandatory=False,
            print_value=True,
            default_value=DEFAULT_MAX_RELATED_IOCS,
        )

        if (max_iocs_to_return > MAX_RELATED_IOCS) or (
            max_iocs_to_return < MIN_RELATED_IOCS
        ):
            siemplify.LOGGER.info(
                f'"Max IOCs To Return" parameter not in range of {MIN_RELATED_IOCS} to {MAX_RELATED_IOCS}. Using default of: {DEFAULT_MAX_RELATED_IOCS}'
            )
            max_iocs_to_return = DEFAULT_MAX_RELATED_IOCS

        enclave_filter_list = (
            load_csv_to_list(enclave_filter, "Enclave Filter") if enclave_filter else []
        )
        manager = TruSTARManager(
            api_root=api_root,
            api_key=api_key,
            api_secret=api_secret,
            verify_ssl=verify_ssl,
        )

        if siemplify.target_entities:
            enclaves = manager.list_enclaves()
            siemplify.LOGGER.info(f"Listed {len(enclaves)} available enclaves")
            enclaves_names_to_ids = {enclave.name: enclave.id for enclave in enclaves}

            for enclave in enclave_filter_list:
                if enclave not in enclaves_names_to_ids:
                    failed_enclaves.append(enclave)
                else:
                    found_enclaves_ids.append(enclaves_names_to_ids.get(enclave, ""))

            if failed_enclaves:
                raise TruSTARMissingEnclaveException(
                    'Error execution action "{}". Reason: the following enclaves were not found:\n  {}\n\nPlease check the spelling or '
                    'use the action "{}" to find the valid enclaves.'
                    "".format(
                        GET_RELATED_IOCS, "\n  ".join(failed_enclaves), LIST_ENCLAVES
                    )
                )
            if found_enclaves_ids:
                siemplify.LOGGER.info(
                    f"Searching related IOCs for enclave ids of: {', '.join(found_enclaves_ids)}"
                )
            else:
                siemplify.LOGGER.info(
                    "Searching related IOCs for all available enclaves"
                )
            related_iocs = manager.get_related_iocs(
                indicators=[entity.identifier for entity in siemplify.target_entities],
                enclave_ids=found_enclaves_ids,
                limit=max_iocs_to_return,
            )[:max_iocs_to_return]
            siemplify.LOGGER.info(f"Found {len(related_iocs)} related IOCs")
        else:
            siemplify.LOGGER.info(f"No siemplify entities were provided for enrichment")
            related_iocs = []

        if related_iocs:
            for ioc in related_iocs:
                json_results[ioc.indicator_type].append(ioc.value)
            try:
                siemplify.result.add_result_json(
                    {k: v for k, v in json_results.items()}
                )
                siemplify.result.add_data_table(
                    title="Statistics",
                    data_table=construct_csv(
                        [
                            {"Type": indicator_type, "Count": len(indicator_values)}
                            for indicator_type, indicator_values in json_results.items()
                        ]
                    ),
                )
            except Exception as error:
                siemplify.LOGGER.error(f"Failed to add json results and csv table")
                siemplify.LOGGER.exception(error)
            result_value = True
            output_message = f"Successfully returned related IOCs for the provided entities in {INTEGRATION_NAME}"
        else:
            output_message = f"No related IOCs were found for the provided entities in {INTEGRATION_NAME}"

    except Exception as error:
        status = EXECUTION_STATE_FAILED
        output_message = f'Error execution action "{GET_RELATED_IOCS}". Reason: {error}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
