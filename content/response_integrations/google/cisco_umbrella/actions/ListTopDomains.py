from __future__ import annotations
from dataclasses import asdict
from itertools import islice

from cisco_umbrella.core.CiscoUmbrellaStaticResourcesManager import (
    CiscoUmbrellaStaticResourcesManager,
    StaticAssets,
)
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_action_param
from cisco_umbrella.core.exceptions import ValidationError
from cisco_umbrella.core.utils import validate_range


INTEGRATION_NAME = "CiscoUmbrella"
SCRIPT_NAME = f"{INTEGRATION_NAME} - List Top Domains"
SUCCESS_MESSAGE = "Successfully returned top domains from Cisco Umbrella."
MAX_ITEMS_LIMIT = 100000


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")
    result_value = True
    json_results = []
    status = EXECUTION_STATE_COMPLETED
    output_message = SUCCESS_MESSAGE

    max_domains_to_return = extract_action_param(
        siemplify,
        param_name="Max Domains To Return",
        is_mandatory=False,
        print_value=True,
    )

    try:
        try:
            max_domains_to_return = validate_range(
                max_domains_to_return, 0, MAX_ITEMS_LIMIT
            )
        except ValidationError as e:
            raise ValidationError(f"Max Domains To Return: {e}") from e
        manager = CiscoUmbrellaStaticResourcesManager()
        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        top_domains = manager.get_asset(StaticAssets.TOP_1M_CSV_ZIP)
        json_results.extend(islice(map(asdict, top_domains), max_domains_to_return))
        siemplify.result.add_result_json(json_results)

    except Exception as e:  # pylint: disable=broad-exception-caught
        output_message = f"Error executing action '{SCRIPT_NAME}'. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
